import os
import random
import re
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_FILE = os.path.join(DATA_DIR, "app_reviews_raw.parquet")

REVIEWS_10K_FILE = os.path.join(DATA_DIR, "reviews_10k.csv")
VALIDATION_500_FILE = os.path.join(DATA_DIR, "validation_500.csv")
SURGE_FILE = os.path.join(DATA_DIR, "surge_injection.csv")

random.seed(42)
np.random.seed(42)

print("Loading raw parquet dataset...")
df_raw = pd.read_parquet(RAW_FILE)

# Focus on Telegram Messenger reviews (22k available)
df_tg = df_raw[df_raw["package_name"] == "org.telegram.messenger"].copy()
print(f"Loaded {len(df_tg):,} Telegram reviews.")

# Clean review text
df_tg = df_tg.dropna(subset=["review"])
df_tg["review"] = df_tg["review"].astype(str).str.strip()
df_tg = df_tg[df_tg["review"].str.len() >= 10]  # Drop trivial single-word or empty reviews
df_tg = df_tg.drop_duplicates(subset=["review"])
print(f"Cleaned review pool: {len(df_tg):,} unique reviews.")

# Sample exactly 10,000 reviews from the cleaned pool
n_target = 10000
df_sampled = df_tg.sample(n=n_target, random_state=42).reset_index(drop=True)


# Generate realistic 60-day rolling timeline up to today (2026-09-24)
base_date = datetime(2026, 9, 24)
dates = []
versions = []
platforms = []
user_segments = []

for i in range(len(df_sampled)):
    day_offset = random.randint(0, 59)
    # Give slight recency weighting
    if random.random() < 0.4:
        day_offset = random.randint(0, 14)  # 40% in last 2 weeks
    
    rev_date = base_date - timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))
    dates.append(rev_date.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Version rollout mapping based on day offset
    if day_offset > 45:
        ver = "v3.1.0"
    elif day_offset > 28:
        ver = "v3.2.1"
    elif day_offset > 10:
        ver = "v3.3.0"
    else:
        ver = "v3.4.0"
    versions.append(ver)
    
    platforms.append("Android" if random.random() < 0.75 else "iOS")
    user_segments.append("Free" if random.random() < 0.8 else "Telegram Premium")

df_sampled["review_id"] = [f"REV-{10000 + i}" for i in range(len(df_sampled))]
df_sampled["review_text"] = df_sampled["review"]
df_sampled["rating"] = df_sampled["star"].astype(int)
df_sampled["date"] = dates
df_sampled["platform"] = platforms
df_sampled["app_version"] = versions
df_sampled["app_name"] = "Telegram Messenger"
df_sampled["user_segment"] = user_segments

# Plant realistic PII in ~2% of reviews to test the PII Redaction Pillar
pii_samples = [
    (" reach me at john.doe29@gmail.com for logs", "EMAIL"),
    (" phone number is +1-555-0199 call me", "PHONE"),
    (" my email is alex_smith@yahoo.com please fix", "EMAIL"),
    (" contact user Sarah Jenkins directly at 415-555-2671", "PHONE/NAME"),
    (" support ticket opened by David Miller (david.m@corp.net)", "NAME/EMAIL"),
    (" call +44 20 7946 0912 regarding account freeze", "PHONE"),
]

pii_indices = random.sample(range(len(df_sampled)), 200)
for idx in pii_indices:
    pii_snippet, _ = random.choice(pii_samples)
    df_sampled.at[idx, "review_text"] = df_sampled.at[idx, "review_text"] + pii_snippet

final_cols = ["review_id", "review_text", "rating", "date", "platform", "app_version", "app_name", "user_segment"]
df_10k = df_sampled[final_cols].sort_values("date").reset_index(drop=True)
df_10k.to_csv(REVIEWS_10K_FILE, index=False, encoding="utf-8")
print(f"Created {REVIEWS_10K_FILE} with {len(df_10k):,} rows.")

# -------------------------------------------------------------
# 2. Prepare Independent Ground-Truth Validation Set (n=500)
# Stratified: 200 positive, 200 negative, 100 neutral
# -------------------------------------------------------------
print("\nPreparing ground-truth validation set (n=500)...")
# Sample from leftover Telegram reviews so there is zero overlap with 10k set
used_texts = set(df_10k["review_text"])
leftover = df_tg[~df_tg["review"].isin(used_texts)]

pos_pool = leftover[leftover["star"].isin([4, 5])].sample(200, random_state=101)
neg_pool = leftover[leftover["star"].isin([1, 2])].sample(200, random_state=102)
neu_pool = leftover[leftover["star"] == 3].sample(100, random_state=103)

val_list = []
for _, r in pos_pool.iterrows():
    val_list.append({
        "review_id": f"VAL-POS-{len(val_list)+1:03d}",
        "review_text": r["review"],
        "rating": int(r["star"]),
        "ground_truth_sentiment": "positive",
        "category": "Praise/Feature Appreciation"
    })

for _, r in neg_pool.iterrows():
    val_list.append({
        "review_id": f"VAL-NEG-{len(val_list)+1:03d}",
        "review_text": r["review"],
        "rating": int(r["star"]),
        "ground_truth_sentiment": "negative",
        "category": "Bug/Crash/Complaint"
    })

for _, r in neu_pool.iterrows():
    val_list.append({
        "review_id": f"VAL-NEU-{len(val_list)+1:03d}",
        "review_text": r["review"],
        "rating": int(r["star"]),
        "ground_truth_sentiment": "neutral",
        "category": "Neutral/Mixed Feedback"
    })

df_val = pd.DataFrame(val_list).sample(frac=1.0, random_state=42).reset_index(drop=True)
df_val.to_csv(VALIDATION_500_FILE, index=False, encoding="utf-8")
print(f"Created {VALIDATION_500_FILE} with {len(df_val)} ground-truth labeled rows.")

# -------------------------------------------------------------
# 3. Prepare Synthetic Surge Injection Set (~100 reviews)
# Critical failure burst: "Update v3.4 broke login / SMS code / crashes"
# -------------------------------------------------------------
print("\nPreparing synthetic surge injection set (n=100)...")

surge_templates = [
    "Updated to 3.4 this morning and now I can't log in! The SMS verification code never arrives.",
    "Telegram crashed 5 times in a row right after installing update 3.4.0. Please fix ASAP!",
    "App crashes immediately on startup since the new update. Totally unusable on Android 14.",
    "Login failure: 'Cannot connect to server' error continuously appearing after updating.",
    "Disaster update! Verification SMS is not received, unable to access my work chats.",
    "Crash on launch after 3.4 update. Cleared cache and reinstalled but still force closing.",
    "Why did you push this update? Login is completely broken and authentication fails every time.",
    "Worst update ever. App keeps crashing whenever I tap on a group chat or try to log in.",
    "Can't get the OTP verification code to log in on my phone since morning.",
    "App force closes after 2 seconds. Reverting back until this 3.4 bug is patched."
]

surge_rows = []
for i in range(100):
    text = random.choice(surge_templates)
    if random.random() < 0.3:
        text += f" Device: Pixel {random.randint(6, 9)}, OS: Android 14."
    
    # All timestamped on the latest date (2026-09-24) within the last 6 hours
    surge_time = base_date - timedelta(hours=random.randint(0, 5), minutes=random.randint(0, 59))
    
    surge_rows.append({
        "review_id": f"SURGE-{i+1:03d}",
        "review_text": text,
        "rating": 1 if random.random() < 0.85 else 2,
        "date": surge_time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": "Android" if random.random() < 0.8 else "iOS",
        "app_version": "v3.4.0",
        "app_name": "Telegram Messenger",
        "user_segment": "Free" if random.random() < 0.75 else "Telegram Premium"
    })

df_surge = pd.DataFrame(surge_rows).sort_values("date").reset_index(drop=True)
df_surge.to_csv(SURGE_FILE, index=False, encoding="utf-8")
print(f"Created {SURGE_FILE} with {len(df_surge)} surge reviews.")
print("\nAll 3 data artifacts generated successfully!")
