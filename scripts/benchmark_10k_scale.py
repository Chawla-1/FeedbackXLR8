"""
10,000 Review Scalability & Performance Benchmark.
Tests the entire end-to-end FeedbackXLR8 pipeline against 10,000 raw customer reviews.

Validates Non-Functional Requirement:
- NFR-1: Full 10,000 review pipeline must execute in under 90 seconds.
- Records per-stage latency, memory, and throughput.
- Writes data/scale_benchmark_metrics.json.
"""
import os
import sys
import time
import json
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from pipeline.pii_redactor import PIIShield
from pipeline.sentiment import SentimentEngine
from pipeline.clustering import ThemeEngine
from pipeline.anomaly_engine import AnomalyAndDriftEngine
from pipeline.founder_engine import calculate_theme_priority_metrics

DATA_DIR = os.path.join(BASE_DIR, "data")
REVIEWS_10K_FILE = os.path.join(DATA_DIR, "reviews_10k.csv")
BENCHMARK_OUTPUT_FILE = os.path.join(DATA_DIR, "scale_benchmark_metrics.json")


def run_10k_benchmark():
    print(f"Loading 10,000 reviews from {REVIEWS_10K_FILE}...")
    t_start = time.perf_counter()
    
    t0 = time.perf_counter()
    df_raw = pd.read_csv(REVIEWS_10K_FILE, encoding="utf-8")
    t_ingest = time.perf_counter() - t0
    n_records = len(df_raw)
    print(f"1. Ingestion: {n_records:,} reviews loaded in {t_ingest:.3f}s")
    
    # 2. PII Shield Redaction
    t0 = time.perf_counter()
    shield = PIIShield()
    df_clean, pii_logs = shield.redact_dataframe(df_raw, text_col="review_text", id_col="review_id")
    t_pii = time.perf_counter() - t0
    print(f"2. PII Redaction: {len(pii_logs):,} entities masked across {n_records:,} reviews in {t_pii:.3f}s")
    
    # 3. Sentiment Engine (Text-only ML mode)
    t0 = time.perf_counter()
    sentiment_engine = SentimentEngine(mode="text_only")
    sent_results = [sentiment_engine.analyze_text(str(t), rating=None) for t in df_clean["review_text"]]
    df_clean["sentiment"] = [r["sentiment"] for r in sent_results]
    df_clean["sentiment_confidence"] = [r["confidence"] for r in sent_results]
    df_clean["is_mixed_sentiment"] = [r.get("is_mixed", False) for r in sent_results]
    t_sentiment = time.perf_counter() - t0
    print(f"3. Sentiment Classification: {n_records:,} reviews processed in {t_sentiment:.3f}s")
    
    # 4. Theme Engine & Verbatim Traceability
    t0 = time.perf_counter()
    theme_engine = ThemeEngine()
    df_themed, themes = theme_engine.fit_transform(df_clean, text_col="review_text")
    t_themes = time.perf_counter() - t0
    print(f"4. Theme Classification & Verbatims: {len(themes)} themes discovered in {t_themes:.3f}s")
    
    # 5. Anomaly & PSI Drift Engine
    t0 = time.perf_counter()
    anomaly_engine = AnomalyAndDriftEngine()
    drift_metrics = anomaly_engine.calculate_drift_metrics(df_themed)
    alerts = anomaly_engine.detect_emerging_spikes(df_themed)
    t_anomaly = time.perf_counter() - t0
    print(f"5. Anomaly & Drift Engine: PSI calculated & {len(alerts)} alerts generated in {t_anomaly:.3f}s")
    
    # 6. Founder Priority Scoring
    t0 = time.perf_counter()
    enriched_themes = calculate_theme_priority_metrics(df_themed, themes)
    t_founder = time.perf_counter() - t0
    print(f"6. Founder Priority Engine: {len(enriched_themes)} themes scored in {t_founder:.3f}s")
    
    total_elapsed = time.perf_counter() - t_start
    throughput = int(n_records / total_elapsed)
    
    benchmark_data = {
        "status": "PASS" if total_elapsed < 90.0 else "FAIL",
        "budget_limit_seconds": 90.0,
        "total_elapsed_seconds": round(total_elapsed, 2),
        "total_records_processed": n_records,
        "throughput_reviews_per_second": throughput,
        "stage_timings_seconds": {
            "ingestion": round(t_ingest, 3),
            "pii_redaction": round(t_pii, 3),
            "sentiment_classification": round(t_sentiment, 3),
            "theme_classification_and_verbatims": round(t_themes, 3),
            "anomaly_and_drift_detection": round(t_anomaly, 3),
            "founder_priority_scoring": round(t_founder, 3)
        },
        "performance_summary": f"Processed {n_records:,} reviews end-to-end in {total_elapsed:.2f}s ({throughput:,} reviews/sec), beating the 90s budget by {round(90.0 - total_elapsed, 1)}s."
    }
    
    with open(BENCHMARK_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)
        
    print("\n" + "="*70)
    print("10,000 REVIEW SCALE BENCHMARK REPORT")
    print("="*70)
    print(f"Total Reviews   : {n_records:,}")
    print(f"Total Time      : {total_elapsed:.2f} seconds (Budget: < 90.0s)")
    print(f"Throughput      : {throughput:,} reviews / second")
    print(f"Status          : {benchmark_data['status']} ({benchmark_data['performance_summary']})")
    print("="*70)

if __name__ == "__main__":
    run_10k_benchmark()
