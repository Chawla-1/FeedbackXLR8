"""
Validates sentiment engine against HUMAN-labeled ground truth.
Uses data/human_labels_150.csv (created by create_human_labels.py).

This produces the one number that actually matters:
text-only accuracy against labels that were NOT derived from star ratings.
"""
import os
import sys
import json
import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pipeline.sentiment import SentimentEngine

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HUMAN_LABELS_FILE = os.path.join(DATA_DIR, "human_labels_150.csv")
HUMAN_VALIDATION_FILE = os.path.join(DATA_DIR, "human_validation_metrics.json")


def validate_against_human_labels():
    if not os.path.exists(HUMAN_LABELS_FILE):
        print(f"ERROR: {HUMAN_LABELS_FILE} not found.")
        print(f"Run: python scripts/create_human_labels.py --interactive")
        return None
    
    df = pd.read_csv(HUMAN_LABELS_FILE, encoding="utf-8")
    
    # Filter to only labeled rows
    labeled = df[df["human_sentiment"].notna() & (df["human_sentiment"] != "")]
    if len(labeled) < 20:
        print(f"Only {len(labeled)} reviews labeled. Need at least 20 for meaningful metrics.")
        print(f"Run: python scripts/create_human_labels.py --interactive")
        return None
    
    print(f"Validating against {len(labeled)} human-labeled reviews.\n")
    
    engine = SentimentEngine(mode="text_only")
    classes = ["positive", "neutral", "negative", "mixed"]
    
    y_true = []
    y_pred = []
    disagreements = []
    rating_text_mismatches = []
    
    for _, row in labeled.iterrows():
        text = str(row["review_text"])
        human_label = str(row["human_sentiment"]).lower().strip()
        hidden_rating = int(row.get("_hidden_rating", 3))
        
        res = engine.analyze_text(text, rating=None)
        pred = res["sentiment"]
        
        y_true.append(human_label)
        y_pred.append(pred)
        
        if pred != human_label and len(disagreements) < 20:
            disagreements.append({
                "text": text[:120],
                "human_label": human_label,
                "model_pred": pred,
                "hidden_rating": hidden_rating,
                "confidence": res["confidence"],
            })
        
        # Track cases where human sentiment disagrees with star rating
        rating_sentiment = "positive" if hidden_rating >= 4 else ("negative" if hidden_rating <= 2 else "neutral")
        if human_label != rating_sentiment:
            rating_text_mismatches.append({
                "text": text[:100],
                "human_label": human_label,
                "rating": hidden_rating,
                "rating_implied": rating_sentiment,
            })
    
    # Filter to classes that appear in both y_true and y_pred
    present_classes = sorted(set(y_true) | set(y_pred))
    
    acc = round(accuracy_score(y_true, y_pred), 3)
    report = classification_report(y_true, y_pred, labels=present_classes, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=present_classes)
    
    # How often does the human label agree with the star rating?
    rating_agreement = 1.0 - (len(rating_text_mismatches) / len(labeled)) if len(labeled) > 0 else 0
    
    metrics = {
        "label_source": "Independent human labeling (rating hidden during annotation)",
        "sample_size": len(labeled),
        "text_only_accuracy": acc,
        "macro_f1": round(report.get("macro avg", {}).get("f1-score", 0), 3),
        "confusion_matrix": {
            "labels": present_classes,
            "matrix": cm.tolist(),
        },
        "per_class": {
            cls: {
                "precision": round(report[cls]["precision"], 3),
                "recall": round(report[cls]["recall"], 3),
                "f1_score": round(report[cls]["f1-score"], 3),
                "support": int(report[cls]["support"]),
            }
            for cls in present_classes if cls in report
        },
        "human_vs_rating_agreement": round(rating_agreement, 3),
        "rating_text_mismatch_count": len(rating_text_mismatches),
        "rating_text_mismatch_examples": rating_text_mismatches[:10],
        "model_disagreements": disagreements,
    }
    
    with open(HUMAN_VALIDATION_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    
    print("=" * 60)
    print("HUMAN-LABELED VALIDATION (Non-Circular Ground Truth)")
    print("=" * 60)
    print(f"  Sample size:         {metrics['sample_size']}")
    print(f"  Label source:        {metrics['label_source']}")
    print(f"  TEXT-ONLY Accuracy:  {metrics['text_only_accuracy'] * 100:.1f}%")
    print(f"  Macro F1:            {metrics['macro_f1']}")
    print(f"  Confusion Matrix:    {present_classes}")
    for row_vals in cm.tolist():
        print(f"                       {row_vals}")
    print(f"\n  Human-vs-Rating agreement: {metrics['human_vs_rating_agreement'] * 100:.1f}%")
    print(f"  (This shows how often human sentiment matches star rating)")
    print(f"  Mismatches: {metrics['rating_text_mismatch_count']}")
    print(f"\n  Saved to: {HUMAN_VALIDATION_FILE}")
    
    return metrics


if __name__ == "__main__":
    validate_against_human_labels()
