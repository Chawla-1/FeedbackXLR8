"""
Hand-Labeling Tool for Independent Ground Truth (Pillar P2).

This script:
1. Samples 150 reviews from the main corpus
2. STRIPS the star rating so the labeler cannot see it
3. Presents each review for manual sentiment classification
4. Saves results to data/human_labels_150.csv

This is the single highest-value thing we can do for credibility:
one real, non-circular accuracy number from independent human labels.
"""
import os
import sys
import random
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SOURCE_FILE = os.path.join(DATA_DIR, "reviews_10k.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "human_labels_150.csv")

N_SAMPLES = 150

def create_labeling_batch():
    df = pd.read_csv(SOURCE_FILE, encoding="utf-8")
    
    # Stratified sample: pull from all rating buckets so we don't just get easy cases
    samples = []
    for star in [1, 2, 3, 4, 5]:
        pool = df[df["rating"] == star]
        n = min(30, len(pool))  # 30 per star bucket = 150 total
        samples.append(pool.sample(n=n, random_state=42 + star))
    
    df_sample = pd.concat(samples).sample(frac=1.0, random_state=99).reset_index(drop=True)
    
    # Output: review text ONLY. No rating visible to the labeler.
    labeling_df = pd.DataFrame({
        "label_id": [f"HL-{i+1:03d}" for i in range(len(df_sample))],
        "review_text": df_sample["review_text"].values,
        "human_sentiment": "",  # To be filled: positive / negative / neutral / mixed
        "labeler_confidence": "",  # high / medium / low
        "notes": "",  # Optional: "sarcastic", "ambiguous", etc.
        # Hidden columns — DO NOT show to the labeler during labeling
        "_hidden_rating": df_sample["rating"].values,
        "_hidden_review_id": df_sample["review_id"].values,
    })
    
    labeling_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"Created labeling batch: {OUTPUT_FILE}")
    print(f"  {len(labeling_df)} reviews sampled (30 per star bucket, shuffled)")
    print(f"  Star ratings are in hidden columns — DO NOT look at them while labeling!")
    print(f"\nInstructions:")
    print(f"  1. Open {OUTPUT_FILE} in Excel or Google Sheets")
    print(f"  2. HIDE columns '_hidden_rating' and '_hidden_review_id'")
    print(f"  3. Read each review_text and fill 'human_sentiment' with:")
    print(f"     positive / negative / neutral / mixed")
    print(f"  4. Fill 'labeler_confidence' with: high / medium / low")
    print(f"  5. Add notes for interesting cases (sarcasm, ambiguous, etc.)")
    print(f"  6. Save and run: python scripts/validate_human_labels.py")


def run_interactive_labeling():
    """Interactive terminal labeling — faster than spreadsheet for small batches."""
    if os.path.exists(OUTPUT_FILE):
        df = pd.read_csv(OUTPUT_FILE, encoding="utf-8")
        already_labeled = df["human_sentiment"].notna() & (df["human_sentiment"] != "")
        remaining = df[~already_labeled]
        print(f"Resuming: {already_labeled.sum()} already labeled, {len(remaining)} remaining.\n")
    else:
        create_labeling_batch()
        df = pd.read_csv(OUTPUT_FILE, encoding="utf-8")
        remaining = df
    
    labeled_count = 0
    for idx, row in remaining.iterrows():
        print(f"\n{'='*60}")
        print(f"[{row['label_id']}] ({idx+1}/{len(df)})")
        print(f"{'='*60}")
        print(f"\n  \"{row['review_text']}\"\n")
        
        while True:
            choice = input("  Sentiment [p]ositive / [n]egative / [u]neutral / [m]ixed / [s]kip / [q]uit: ").strip().lower()
            if choice in ('p', 'n', 'u', 'm', 's', 'q'):
                break
            print("  Invalid. Enter p/n/u/m/s/q.")
        
        if choice == 'q':
            print(f"\nSaved {labeled_count} new labels. Quit.")
            break
        
        if choice == 's':
            continue
        
        label_map = {'p': 'positive', 'n': 'negative', 'u': 'neutral', 'm': 'mixed'}
        df.at[idx, "human_sentiment"] = label_map[choice]
        
        conf = input("  Confidence [h]igh / [m]edium / [l]ow: ").strip().lower()
        conf_map = {'h': 'high', 'm': 'medium', 'l': 'low'}
        df.at[idx, "labeler_confidence"] = conf_map.get(conf, 'medium')
        
        labeled_count += 1
        
        if labeled_count % 10 == 0:
            df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
            total_done = (df["human_sentiment"].notna() & (df["human_sentiment"] != "")).sum()
            print(f"\n  [Auto-saved. {total_done} total labeled so far.]")
    
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    total_done = (df["human_sentiment"].notna() & (df["human_sentiment"] != "")).sum()
    print(f"\nFinal save: {total_done} reviews labeled in {OUTPUT_FILE}")


if __name__ == "__main__":
    if "--interactive" in sys.argv:
        run_interactive_labeling()
    else:
        create_labeling_batch()
