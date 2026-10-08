"""
FeedbackXLR8 — Unified Benchmark Evaluation Harness (eval.py)
Evaluates any sentiment and theming engine against the sacred benchmark/golden.csv.
Computes accuracy, macro/weighted F1, per-class metrics, confusion matrices, and 95% Wilson CIs.
Usage:
    python eval.py --engine v2 --output benchmark/baseline_v2.json
    python eval.py --engine v3 --output benchmark/sentiment_v3.json
"""
import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculates 95% Wilson Score Confidence Interval."""
    if total == 0:
        return (0.0, 0.0)
    z = 1.96  # 95% confidence
    p = successes / total
    denominator = 1 + z**2 / total
    centre_adjusted_probability = p + z**2 / (2 * total)
    adjusted_std_dev = np.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)
    lower_bound = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    upper_bound = (centre_adjusted_probability + z * adjusted_std_dev) / denominator
    return (round(float(max(0.0, lower_bound)), 4), round(float(min(1.0, upper_bound)), 4))

def evaluate_predictions(y_true: List[str], y_pred: List[str], classes: List[str]) -> Dict[str, Any]:
    """Computes precision, recall, F1, confusion matrix, and Wilson CIs."""
    total = len(y_true)
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = round(correct / max(1, total), 4)
    acc_ci = wilson_score_interval(correct, total)

    # Confusion matrix
    class_to_idx = {c: i for i, c in enumerate(classes)}
    n_c = len(classes)
    cm = [[0 for _ in range(n_c)] for _ in range(n_c)]
    for yt, yp in zip(y_true, y_pred):
        if yt in class_to_idx and yp in class_to_idx:
            cm[class_to_idx[yt]][class_to_idx[yp]] += 1

    per_class = {}
    f1_list = []
    precision_list = []
    recall_list = []

    for idx, c in enumerate(classes):
        tp = cm[idx][idx]
        fp = sum(cm[r][idx] for r in range(n_c)) - tp
        fn = sum(cm[idx][col] for col in range(n_c)) - tp
        support = sum(cm[idx][col] for col in range(n_c))

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_class[c] = {
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "support": int(support),
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
        }
        precision_list.append(prec)
        recall_list.append(rec)
        f1_list.append(f1)

    macro_f1 = round(float(np.mean(f1_list)), 4)
    macro_prec = round(float(np.mean(precision_list)), 4)
    macro_rec = round(float(np.mean(recall_list)), 4)

    return {
        "total_samples": total,
        "correct": correct,
        "accuracy": accuracy,
        "accuracy_95ci": list(acc_ci),
        "macro_f1": macro_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "classes": classes,
        "confusion_matrix": cm,
        "per_class": per_class,
    }

def run_eval(engine_type: str = "v2", benchmark_file: str = "benchmark/golden.csv", output_file: str = "benchmark/baseline_v2.json"):
    if not os.path.exists(benchmark_file):
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_file}")

    df_gold = pd.read_csv(benchmark_file)
    print(f"\n=======================================================")
    print(f"[EVAL] FeedbackXLR8 Evaluation Harness (eval.py)")
    print(f"Target Benchmark: {benchmark_file} ({len(df_gold)} rows)")
    print(f"Engine Type: {engine_type.upper()}")
    print(f"=======================================================\n")

    y_true_sentiment = df_gold["sentiment"].astype(str).str.lower().tolist()
    y_pred_sentiment = []

    y_true_theme = df_gold["theme"].astype(str).str.lower().tolist()
    y_pred_theme = []

    # Engine v2 (Baseline Engine)
    if engine_type == "v2" or engine_type == "v2_rating_assisted":
        from pipeline.sentiment import SentimentEngine
        from pipeline.playstore_fetcher import process_reviews_through_pipeline

        mode = "rating_assisted" if "rating_assisted" in engine_type else "text_only"
        sent_engine = SentimentEngine(mode=mode)

        for _, row in df_gold.iterrows():
            txt = str(row["review_text"])
            r_val = int(row.get("rating", 3))
            res = sent_engine.analyze_text(txt, rating=r_val if mode == "rating_assisted" else None)
            
            # Predict sentiment
            if res.get("is_mixed", False):
                pred_s = "mixed"
            else:
                pred_s = res.get("sentiment", "neutral").lower()
            y_pred_sentiment.append(pred_s)

            # Predict theme via keyword taxonomy
            t_txt = txt.lower()
            if any(k in t_txt for k in ["crash", "freeze", "bug", "unusable", "stuck", "force close"]):
                p_th = "crash"
            elif any(k in t_txt for k in ["login", "auth", "password", "otp", "sign in"]):
                p_th = "auth_otp"
            elif any(k in t_txt for k in ["battery", "drain", "slow", "lag", "performance"]):
                p_th = "performance"
            elif any(k in t_txt for k in ["bill", "payment", "subscription", "charge"]):
                p_th = "billing"
            elif any(k in t_txt for k in ["ui", "design", "dark mode", "layout"]):
                p_th = "ui_ux"
            elif r_val >= 4 and any(k in t_txt for k in ["love", "great", "best", "good", "easy", "helpful"]):
                p_th = "praise"
            else:
                p_th = "other"
            y_pred_theme.append(p_th)

    elif engine_type == "v3":
        # New Transformer / Clause-Splitter Engine
        try:
            from pipeline.sentiment_v3 import SentimentV3Engine
            s3 = SentimentV3Engine()
        except ImportError:
            print("⚠️ pipeline.sentiment_v3 not yet found. Please implement Phase 1 first.")
            return

        for _, row in df_gold.iterrows():
            txt = str(row["review_text"])
            r_val = int(row.get("rating", 3))
            res = s3.analyze(txt, rating=r_val)
            y_pred_sentiment.append(res.get("sentiment", "neutral").lower())

            # Theme assignment
            t_txt = txt.lower()
            if any(k in t_txt for k in ["crash", "freeze", "bug", "unusable", "stuck", "force close"]):
                p_th = "crash"
            elif any(k in t_txt for k in ["login", "auth", "password", "otp", "sign in"]):
                p_th = "auth_otp"
            elif any(k in t_txt for k in ["battery", "drain", "slow", "lag", "performance"]):
                p_th = "performance"
            elif any(k in t_txt for k in ["bill", "payment", "subscription", "charge"]):
                p_th = "billing"
            elif any(k in t_txt for k in ["ui", "design", "dark mode", "layout"]):
                p_th = "ui_ux"
            elif r_val >= 4 and any(k in t_txt for k in ["love", "great", "best", "good", "easy", "helpful"]):
                p_th = "praise"
            else:
                p_th = "other"
            y_pred_theme.append(p_th)
    else:
        raise ValueError(f"Unknown engine type: {engine_type}")

    # Evaluate Sentiment (4 classes: positive, negative, neutral, mixed)
    sentiment_classes = ["negative", "positive", "neutral", "mixed"]
    sent_metrics = evaluate_predictions(y_true_sentiment, y_pred_sentiment, sentiment_classes)

    # Evaluate Theming (7 classes: crash, auth_otp, performance, billing, ui_ux, praise, other)
    theme_classes = ["crash", "auth_otp", "performance", "billing", "ui_ux", "praise", "other"]
    theme_metrics = evaluate_predictions(y_true_theme, y_pred_theme, theme_classes)

    output_data = {
        "engine": engine_type,
        "benchmark_dataset": benchmark_file,
        "evaluation_timestamp": pd.Timestamp.now().isoformat(),
        "sentiment_evaluation": sent_metrics,
        "theme_evaluation": theme_metrics,
    }

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    # Print Summary Table
    print(f"[OK] Evaluation Complete. Results written to: {output_file}\n")
    print(f"--- SENTIMENT PERFORMANCE ({engine_type.upper()}) ---")
    print(f"Accuracy:        {sent_metrics['accuracy']*100:.2f}% (95% CI: [{sent_metrics['accuracy_95ci'][0]*100:.1f}%, {sent_metrics['accuracy_95ci'][1]*100:.1f}%])")
    print(f"Macro F1 Score:  {sent_metrics['macro_f1']:.4f}")
    print(f"Macro Precision: {sent_metrics['macro_precision']:.4f}")
    print(f"Macro Recall:    {sent_metrics['macro_recall']:.4f}\n")

    print(f"{'Class':<12} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
    print("-" * 60)
    for c, stats in sent_metrics["per_class"].items():
        print(f"{c:<12} | {stats['precision']:<10.4f} | {stats['recall']:<10.4f} | {stats['f1_score']:<10.4f} | {stats['support']:<8}")

    print("\n--- CONFUSION MATRIX ---")
    print(f"{'True \\ Pred':<12} | " + " | ".join([f"{c:<8}" for c in sentiment_classes]))
    print("-" * 55)
    for idx, c in enumerate(sentiment_classes):
        row_str = " | ".join([f"{sent_metrics['confusion_matrix'][idx][j]:<8}" for j in range(len(sentiment_classes))])
        print(f"{c:<12} | {row_str}")

    print(f"\n--- THEME PERFORMANCE ({engine_type.upper()}) ---")
    print(f"Theme Accuracy:  {theme_metrics['accuracy']*100:.2f}% | Macro F1: {theme_metrics['macro_f1']:.4f}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FeedbackXLR8 Benchmark Evaluation Harness")
    parser.add_argument("--engine", type=str, default="v2", help="Engine version: v2, v2_rating_assisted, or v3")
    parser.add_argument("--benchmark", type=str, default="benchmark/golden.csv", help="Path to golden benchmark CSV")
    parser.add_argument("--output", type=str, default=None, help="Path to output JSON")
    args = parser.parse_args()

    if args.output is None:
        args.output = "benchmark/sentiment_v3.json" if args.engine == "v3" else "benchmark/baseline_v2.json"

    run_eval(engine_type=args.engine, benchmark_file=args.benchmark, output_file=args.output)
