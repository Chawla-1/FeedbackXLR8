import os
import sys
import time
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.pii_redactor import PIIShield
from pipeline.sentiment import SentimentEngine
from pipeline.sentiment_v3 import SentimentV3Engine
from pipeline.theming_v3 import ThemingV3Engine

test_review = "Great password manager, BUT the app crashes after opening vault on Android 15. Call me at +1-555-839-2001 or email alex@test.com."

print("=" * 65)
print("BENCHMARKING LATENCY PER REVIEW (RUNNING ON CURRENT CPU)")
print("=" * 65)

# 1. PII Redaction
pii = PIIShield()
# Warmup
pii.redact_text(test_review)
t0 = time.perf_counter()
for _ in range(100):
    redacted, audits = pii.redact_text(test_review)
t_pii = (time.perf_counter() - t0) / 100 * 1000

# 2. Sentiment v2 (Baseline fast)
sent_v2 = SentimentEngine(mode="rating_assisted")
t0 = time.perf_counter()
for _ in range(100):
    res_v2 = sent_v2.analyze_text(redacted, rating=3)
t_sent_v2 = (time.perf_counter() - t0) / 100 * 1000

# 3. Sentiment v3 (Clause Splitter + Offline ML)
sent_v3_fast = SentimentV3Engine(use_transformer=False)
t0 = time.perf_counter()
for _ in range(100):
    res_v3_fast = sent_v3_fast.analyze(redacted, rating=3)
t_sent_v3_fast = (time.perf_counter() - t0) / 100 * 1000

# 4. Dense Embeddings (all-MiniLM-L6-v2)
print("Loading all-MiniLM-L6-v2 embeddings model...")
themer = ThemingV3Engine()
themer.embed_texts([redacted]) # Warmup

t0 = time.perf_counter()
for _ in range(30):
    emb = themer.embed_texts([redacted])
t_emb_single = (time.perf_counter() - t0) / 30 * 1000

# 5. Batched Embedding (10 reviews)
batch_10 = [test_review] * 10
t0 = time.perf_counter()
for _ in range(10):
    emb_batch = themer.embed_texts(batch_10)
t_emb_batched = (time.perf_counter() - t0) / 10 / 10 * 1000

# 6. Founder Engine Priority & Ticket Generation
from pipeline.founder_engine import calculate_theme_priority_metrics, generate_ticket_markdown
sample_theme = {"title": "App Stability & Launch Crashes", "volume": 1, "avg_rating": 3.0}
import pandas as pd
df_sample = pd.DataFrame([{"review_id": "REV-1", "rating": 3, "theme_title": "App Stability & Launch Crashes", "review_text": redacted}])
t0 = time.perf_counter()
for _ in range(100):
    m = calculate_theme_priority_metrics(df_sample, [sample_theme])
    ticket = generate_ticket_markdown(m[0])
t_founder = (time.perf_counter() - t0) / 100 * 1000

print(f"\n1. PII Masking & Redaction:       {t_pii:6.3f} ms")
print(f"2. Sentiment Analysis (v2 fast):       {t_sent_v2:6.3f} ms")
print(f"3. Sentiment Analysis (v3 split+ML):   {t_sent_v3_fast:6.3f} ms")
print(f"4. Dense Semantic Embeddings (single): {t_emb_single:6.3f} ms")
print(f"   Dense Embeddings (batched/review):  {t_emb_batched:6.3f} ms")
print(f"5. Priority Score & Ticket Generation: {t_founder:6.3f} ms")

total_v2 = t_pii + t_sent_v2 + t_founder
total_v3_single = t_pii + t_sent_v3_fast + t_emb_single + t_founder
total_v3_batched = t_pii + t_sent_v3_fast + t_emb_batched + t_founder

print("-" * 65)
print(f"TOTAL TIME (v2 Standard Pipeline):     {total_v2:6.3f} ms  (~{1000/total_v2:,.0f} reviews/sec)")
print(f"TOTAL TIME (v3 Semantic Pipeline):     {total_v3_single:6.3f} ms  (~{1000/total_v3_single:,.0f} reviews/sec)")
print(f"TOTAL TIME (v3 Batched Pipeline):      {total_v3_batched:6.3f} ms  (~{1000/total_v3_batched:,.0f} reviews/sec)")
print("=" * 65)
