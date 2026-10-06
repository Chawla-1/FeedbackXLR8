#!/usr/bin/env python3
"""
FeedbackXLR8 — Multi-App Data Generator

Splits the existing processed_reviews.parquet into multiple app datasets,
each with its own themes, alerts, drift metrics, and configuration.

Run this ONCE after the main pipeline has generated processed_reviews.parquet:
    python scripts/setup_multi_app.py
"""
import os
import sys
import json
import random
import shutil
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pipeline.anomaly_engine import AnomalyAndDriftEngine
from pipeline.clustering import THEME_DEFINITIONS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
APPS_DIR = os.path.join(DATA_DIR, "apps")
PROCESSED = os.path.join(DATA_DIR, "processed_reviews.parquet")

# ---------------------------------------------------------------------------
# App definitions — each app gets a distinct theme distribution
# ---------------------------------------------------------------------------
APPS = [
    {
        "id": "cloudsync_pro",
        "name": "CloudSync Pro",
        "icon": "☁️",
        "description": "Enterprise cloud storage & cross-device file synchronization platform",
        "category": "Productivity",
        "color": "#0078d4",
        "primary_themes": [
            "Media Download & File Storage",
            "App Stability & Launch Crashes",
        ],
        "secondary_themes": [
            "General Praise & Feature Experience",
            "Notification & Background Sync",
        ],
        "weight": 0.30,
    },
    {
        "id": "payflow_wallet",
        "name": "PayFlow Wallet",
        "icon": "💳",
        "description": "Digital payments, P2P transfers & biometric financial security",
        "category": "FinTech",
        "color": "#16a34a",
        "primary_themes": [
            "Login, Auth & Verification",
            "App Stability & Launch Crashes",
        ],
        "secondary_themes": [
            "Notification & Background Sync",
            "General Praise & Feature Experience",
        ],
        "weight": 0.28,
    },
    {
        "id": "healthtrack",
        "name": "HealthTrack",
        "icon": "❤️",
        "description": "Fitness tracking, health monitoring & wearable device sync",
        "category": "Health & Fitness",
        "color": "#dc2626",
        "primary_themes": [
            "Battery Drain & Device Lag",
            "Notification & Background Sync",
        ],
        "secondary_themes": [
            "App Stability & Launch Crashes",
            "General Praise & Feature Experience",
        ],
        "weight": 0.22,
    },
    {
        "id": "edulearn_plus",
        "name": "EduLearn Plus",
        "icon": "📚",
        "description": "Online courses, live classes & interactive learning platform",
        "category": "EdTech",
        "color": "#7c3aed",
        "primary_themes": [
            "Voice & Video Call Quality",
            "Media Download & File Storage",
        ],
        "secondary_themes": [
            "General Praise & Feature Experience",
            "Battery Drain & Device Lag",
        ],
        "weight": 0.20,
    },
]


# ---------------------------------------------------------------------------
# Assignment logic
# ---------------------------------------------------------------------------
def assign_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Distribute reviews across apps based on theme affinity."""
    rng = random.Random(42)
    assignments = []

    for _, row in df.iterrows():
        theme = row.get("theme_title", "")
        picked = None

        # First pass — high-affinity primary themes
        for app in APPS:
            if theme in app["primary_themes"] and rng.random() < 0.60:
                picked = app["id"]
                break

        # Second pass — secondary themes
        if not picked:
            for app in APPS:
                if theme in app["secondary_themes"] and rng.random() < 0.30:
                    picked = app["id"]
                    break

        # Fallback — weighted random
        if not picked:
            picked = rng.choices(
                [a["id"] for a in APPS],
                [a["weight"] for a in APPS],
                k=1,
            )[0]

        assignments.append(picked)

    df = df.copy()
    df["app_id"] = assignments
    return df


# ---------------------------------------------------------------------------
# Theme aggregation from pre-classified reviews
# ---------------------------------------------------------------------------
def build_themes(app_df: pd.DataFrame) -> list:
    """Aggregate themes from reviews that are already classified."""
    all_names = list(THEME_DEFINITIONS.keys()) + ["Uncategorized / Emerging Issues"]
    themes = []

    for name in all_names:
        sub = app_df[app_df["theme_title"] == name]
        vol = len(sub)
        if vol == 0:
            continue

        neg = int((sub["sentiment"] == "negative").sum()) if "sentiment" in sub.columns else 0
        neg_r = round(neg / vol, 3)

        candidates = sub.sort_values("rating", ascending=(neg_r > 0.15))
        verbatims = []
        for _, r in candidates.head(5).iterrows():
            verbatims.append({
                "review_id": r.get("review_id", ""),
                "quote": str(r.get("review_text", "")),
                "rating": int(r.get("rating", 3)),
                "date": str(r.get("date", "")),
                "version": str(r.get("app_version", "")),
            })

        norm_vol = min(vol / max(len(app_df) / len(all_names), 1), 2.5)
        impact = round(norm_vol * (neg_r + 0.15) * 10, 2)
        is_novel = name == "Uncategorized / Emerging Issues"

        themes.append({
            "cluster_id": all_names.index(name),
            "title": name,
            "keywords": THEME_DEFINITIONS.get(name, {}).get("keywords", ["emerging"]),
            "volume": vol,
            "negativity_ratio": neg_r,
            "impact_score": impact,
            "verbatims": verbatims,
            "is_novel_theme": is_novel,
            "classification_method": "taxonomy_regex" if not is_novel else "unmatched_fallback",
        })

    themes.sort(key=lambda x: x["impact_score"], reverse=True)
    return themes


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("FeedbackXLR8 — MULTI-APP DATA GENERATOR")
    print("=" * 60)

    if not os.path.exists(PROCESSED):
        print(f"ERROR: {PROCESSED} not found. Run scripts/run_pipeline.py first.")
        sys.exit(1)

    # Load existing processed reviews
    df = pd.read_parquet(PROCESSED)
    df["date"] = pd.to_datetime(df["date"])
    print(f"Loaded {len(df):,} processed reviews.")

    # Assign reviews to apps
    df = assign_reviews(df)
    print(f"Assigned reviews to {len(APPS)} apps.")

    # Load shared assets
    def load_json(name, default=None):
        p = os.path.join(DATA_DIR, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return default if default is not None else []

    pii_all = load_json("pii_audit_log.json", [])
    val_m = load_json("validation_metrics.json", {})
    human_m = load_json("human_validation_metrics.json", {})

    engine = AnomalyAndDriftEngine()
    registry = []

    for app_def in APPS:
        aid = app_def["id"]
        adir = os.path.join(APPS_DIR, aid)
        os.makedirs(adir, exist_ok=True)

        # Filter reviews for this app
        adf = df[df["app_id"] == aid].copy()
        adf = adf.drop(columns=["app_id"], errors="ignore")

        print(f"\n--- {app_def['name']} ({aid}): {len(adf):,} reviews ---")

        # Save processed reviews
        adf.to_parquet(os.path.join(adir, "processed_reviews.parquet"), index=False)

        # Build themes
        themes = build_themes(adf)
        with open(os.path.join(adir, "themes.json"), "w", encoding="utf-8") as f:
            json.dump(themes, f, indent=2)

        # Compute alerts
        alerts = engine.detect_emerging_spikes(adf)
        with open(os.path.join(adir, "alerts.json"), "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2)

        # Compute drift
        drift = engine.calculate_drift_metrics(adf)
        with open(os.path.join(adir, "drift_metrics.json"), "w", encoding="utf-8") as f:
            json.dump(drift, f, indent=2)

        # PII audit (filter by this app's review IDs)
        rids = set(adf["review_id"].astype(str))
        app_pii = [e for e in pii_all if e.get("review_id") in rids]
        with open(os.path.join(adir, "pii_audit_log.json"), "w", encoding="utf-8") as f:
            json.dump(app_pii, f, indent=2)

        # Shared validation & human metrics (model is app-agnostic)
        for fname, data in [("validation_metrics.json", val_m), ("human_validation_metrics.json", human_m)]:
            with open(os.path.join(adir, fname), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        # Copy surge injection file
        surge_src = os.path.join(DATA_DIR, "surge_injection.csv")
        if os.path.exists(surge_src):
            shutil.copy2(surge_src, os.path.join(adir, "surge_injection.csv"))

        # Compute summary stats for the registry
        avg_r = round(float(adf["rating"].mean()), 2) if len(adf) > 0 else 0.0
        neg_pct = round(float((adf["sentiment"] == "negative").mean() * 100), 1) if len(adf) > 0 else 0.0
        top_theme = themes[0]["title"] if themes else "N/A"

        registry.append({
            "id": aid,
            "name": app_def["name"],
            "icon": app_def["icon"],
            "description": app_def["description"],
            "category": app_def["category"],
            "color": app_def["color"],
            "summary": {
                "total_reviews": len(adf),
                "avg_rating": avg_r,
                "neg_pct": neg_pct,
                "active_alerts": len(alerts),
                "drift_health": drift.get("health", "HEALTHY"),
                "top_theme": top_theme,
                "pii_events": len(app_pii),
            },
        })

        print(f"  Rating: {avg_r}/5 | Neg: {neg_pct}% | Alerts: {len(alerts)} | Drift: {drift.get('health')}")

    # Save registry
    with open(os.path.join(APPS_DIR, "registry.json"), "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Generated data for {len(APPS)} apps in {APPS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
