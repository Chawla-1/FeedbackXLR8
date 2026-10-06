import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta

class AnomalyAndDriftEngine:
    """
    Enterprise Anomaly Spike Detection & Model Drift Monitoring Engine.
    - Killer Feature (FR-6): Theme velocity spike detection vs rolling baseline.
    - Pillar P3 (FR-8): Sentiment drift & new-theme emergence tracking.
    """
    def __init__(self, spike_z_threshold: float = 2.0, velocity_multiplier_threshold: float = 2.5):
        self.spike_z_threshold = spike_z_threshold
        self.velocity_multiplier_threshold = velocity_multiplier_threshold

    def detect_emerging_spikes(self, df: pd.DataFrame, window_hours: int = 24, baseline_days: int = 7) -> List[Dict[str, Any]]:
        """
        Compares last window_hours against the prior baseline_days.
        Calculates Z-score and velocity spike factor.
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        max_date = df["date"].max()
        cutoff_recent = max_date - timedelta(hours=window_hours)
        cutoff_baseline = max_date - timedelta(days=baseline_days)

        recent_df = df[df["date"] >= cutoff_recent]
        baseline_df = df[(df["date"] < cutoff_recent) & (df["date"] >= cutoff_baseline)]

        alerts = []
        if len(recent_df) == 0 or len(baseline_df) == 0:
            return alerts

        baseline_hours = baseline_days * 24
        baseline_rate_multiplier = window_hours / baseline_hours

        # Group by theme
        themes = df["theme_title"].dropna().unique()
        for theme in themes:
            recent_theme = recent_df[recent_df["theme_title"] == theme]
            recent_count = len(recent_theme)
            
            baseline_theme = baseline_df[baseline_df["theme_title"] == theme]
            baseline_count = len(baseline_theme)
            expected_count = baseline_count * baseline_rate_multiplier

            # Velocity ratio
            velocity = round((recent_count + 1) / (expected_count + 1), 2)
            
            # Poisson/Normal approx Z-score
            std_dev = np.sqrt(max(expected_count, 1.0))
            z_score = round((recent_count - expected_count) / std_dev, 2)
            
            neg_ratio = 0.0
            if recent_count > 0 and "sentiment" in recent_theme.columns:
                neg_ratio = round((recent_theme["sentiment"] == "negative").sum() / recent_count, 2)

            # Severity score = z_score * negativity * volume
            severity_score = round(max(z_score, 1.0) * neg_ratio * min(recent_count, 50), 1)

            # Check trigger condition
            if (z_score >= self.spike_z_threshold or velocity >= self.velocity_multiplier_threshold) and neg_ratio >= 0.4 and recent_count >= 5:
                # Grab verbatim quotes for the alert (prioritizing critical 1-2 star complaints)
                alert_candidates = recent_theme.sort_values(by="rating", ascending=True)
                sample_verbatims = []
                for _, r in alert_candidates.head(3).iterrows():
                    sample_verbatims.append({
                        "review_id": r.get("review_id", ""),
                        "quote": str(r.get("review_text", "")),
                        "rating": int(r.get("rating", 1)),
                        "date": str(r.get("date", "")),
                        "version": str(r.get("app_version", ""))
                    })

                alerts.append({
                    "theme": theme,
                    "recent_volume": recent_count,
                    "expected_volume": round(expected_count, 1),
                    "velocity_multiplier": f"{velocity}x",
                    "z_score": z_score,
                    "negativity_ratio": neg_ratio,
                    "severity_score": severity_score,
                    "status": "CRITICAL" if z_score > 3.5 else "HIGH",
                    "sample_verbatims": sample_verbatims
                })

        alerts.sort(key=lambda x: x["severity_score"], reverse=True)
        return alerts

    def calculate_drift_metrics(self, df: pd.DataFrame, window_days: int = 7) -> Dict[str, Any]:
        """
        Measures sentiment distribution drift and novel themes over rolling windows.
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        max_date = df["date"].max()
        cutoff = max_date - timedelta(days=window_days)

        recent = df[df["date"] >= cutoff]
        historical = df[df["date"] < cutoff]

        if len(recent) == 0 or len(historical) == 0:
            return {"status": "INSUFFICIENT_DATA"}

        def get_dist(data):
            counts = data["sentiment"].value_counts(normalize=True)
            return {
                "positive": float(counts.get("positive", 0.0)),
                "negative": float(counts.get("negative", 0.0)),
                "neutral": float(counts.get("neutral", 0.0)) + float(counts.get("mixed", 0.0))
            }

        recent_dist = get_dist(recent)
        historical_dist = get_dist(historical)

        # Population Stability Index (PSI) calculation
        psi = 0.0
        for cat in ["positive", "negative", "neutral"]:
            act = max(recent_dist[cat], 0.001)
            exp = max(historical_dist[cat], 0.001)
            psi += (act - exp) * np.log(act / exp)
        psi = round(psi, 4)

        # Health status
        if psi < 0.1:
            health = "HEALTHY"
            color = "green"
            msg = "Sentiment distribution matches historical baseline within normal variance."
        elif psi < 0.25:
            health = "MODERATE DRIFT"
            color = "yellow"
            msg = "Noticeable distribution shift detected; review changes in user sentiment."
        else:
            health = "SIGNIFICANT DRIFT"
            color = "red"
            msg = "Severe sentiment divergence from baseline; investigate recent release."

        # Novel themes
        hist_themes = set(historical["theme_title"].dropna().unique())
        recent_themes = set(recent["theme_title"].dropna().unique())
        novel_themes = list(recent_themes - hist_themes)

        return {
            "health": health,
            "color": color,
            "psi_score": psi,
            "recent_distribution": recent_dist,
            "historical_distribution": historical_dist,
            "novel_themes": novel_themes,
            "message": msg
        }
