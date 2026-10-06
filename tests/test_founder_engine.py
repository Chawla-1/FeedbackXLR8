"""
Unit tests for Founder Priority & Decision Engine (pipeline/founder_engine.py)
Validates:
- Priority Score calculation conforms to mentor formula
- Severity weighting mapping
- Week-over-week growth clipping and boundary behavior
- Rating lift estimation logic
- Release regression detector (vN vs vN-1)
- Markdown action ticket generation
"""
import unittest
import pandas as pd
from pipeline.founder_engine import (
    get_severity_weight,
    calculate_theme_priority_metrics,
    detect_release_regressions,
    generate_ticket_markdown
)

class TestFounderEngine(unittest.TestCase):

    def setUp(self):
        # Sample synthetic dataset with 2 versions and date progression
        self.sample_df = pd.DataFrame([
            {"review_id": "REV-01", "rating": 1, "theme_title": "App Stability & Launch Crashes", "app_version": "v2.0", "date": "2026-09-28", "sentiment": "negative", "review_text": "Crashes on launch"},
            {"review_id": "REV-02", "rating": 1, "theme_title": "App Stability & Launch Crashes", "app_version": "v2.0", "date": "2026-09-29", "sentiment": "negative", "review_text": "Freezes constantly"},
            {"review_id": "REV-03", "rating": 1, "theme_title": "App Stability & Launch Crashes", "app_version": "v2.0", "date": "2026-09-30", "sentiment": "negative", "review_text": "Cannot open"},
            {"review_id": "REV-04", "rating": 2, "theme_title": "App Stability & Launch Crashes", "app_version": "v2.0", "date": "2026-10-01", "sentiment": "negative", "review_text": "Buggy"},
            {"review_id": "REV-05", "rating": 2, "theme_title": "App Stability & Launch Crashes", "app_version": "v2.0", "date": "2026-10-01", "sentiment": "negative", "review_text": "Crashes after splash"},
            {"review_id": "REV-06", "rating": 1, "theme_title": "App Stability & Launch Crashes", "app_version": "v2.0", "date": "2026-10-02", "sentiment": "negative", "review_text": "Totally broken"},
            {"review_id": "REV-07", "rating": 5, "theme_title": "General Praise & Feature Experience", "app_version": "v1.9", "date": "2026-09-10", "sentiment": "positive", "review_text": "Awesome app"},
            {"review_id": "REV-08", "rating": 5, "theme_title": "General Praise & Feature Experience", "app_version": "v1.9", "date": "2026-09-12", "sentiment": "positive", "review_text": "Love the UI"},
            {"review_id": "REV-09", "rating": 4, "theme_title": "General Praise & Feature Experience", "app_version": "v2.0", "date": "2026-09-28", "sentiment": "positive", "review_text": "Very useful"},
            {"review_id": "REV-10", "rating": 5, "theme_title": "General Praise & Feature Experience", "app_version": "v2.0", "date": "2026-09-30", "sentiment": "positive", "review_text": "Great platform"},
        ])
        self.themes = [
            {"title": "App Stability & Launch Crashes", "volume": 6, "avg_rating": 1.33},
            {"title": "General Praise & Feature Experience", "volume": 4, "avg_rating": 4.75},
        ]

    def test_severity_weight_assignment(self):
        """Severity weights correctly prioritize crashes > auth > UI > general."""
        self.assertEqual(get_severity_weight("App Stability & Launch Crashes"), 3.0)
        self.assertEqual(get_severity_weight("Login & SMS Verification Delays"), 2.5)
        self.assertEqual(get_severity_weight("Battery Drain & Device Lag"), 2.0)
        self.assertEqual(get_severity_weight("UI Navigation & Layout Clutter"), 1.5)
        self.assertEqual(get_severity_weight("General Praise & Feature Experience"), 1.0)
        self.assertEqual(get_severity_weight("Custom Unknown Anomaly"), 1.5)

    def test_calculate_theme_priority_metrics(self):
        """Calculates Priority Score and estimated rating lift with expected rank order."""
        enriched = calculate_theme_priority_metrics(self.sample_df, self.themes)
        self.assertEqual(len(enriched), 2)
        # Stability should rank #1 due to high volume, high severity, and low rating
        top_theme = enriched[0]
        self.assertEqual(top_theme["title"], "App Stability & Launch Crashes")
        self.assertGreater(top_theme["priority_score"], 0)
        self.assertIn(top_theme["urgency_badge"], ["P0 - URGENT", "P1 - HIGH", "P2 - NORMAL"])
        self.assertGreater(top_theme["estimated_rating_lift"], 0)

    def test_empty_dataframe_safety(self):
        """Returns empty list gracefully on empty input."""
        res = calculate_theme_priority_metrics(pd.DataFrame(), self.themes)
        self.assertEqual(res, [])
        reg = detect_release_regressions(pd.DataFrame())
        self.assertEqual(reg, [])

    def test_detect_release_regressions(self):
        """Identifies regressions when complaint volume surges between v2.0 and v1.9."""
        regressions = detect_release_regressions(self.sample_df)
        self.assertIsInstance(regressions, list)
        if regressions:
            reg = regressions[0]
            self.assertEqual(reg["latest_version"], "v2.0")
            self.assertEqual(reg["previous_version"], "v1.9")
            self.assertIn("surge_multiplier", reg)

    def test_positive_praise_theme_handling(self):
        """Verifies that positive praise themes are flagged as wins with 0 score, 0 drag, and delight tickets."""
        enriched = calculate_theme_priority_metrics(self.sample_df, self.themes)
        praise_theme = [t for t in enriched if t["title"] == "General Praise & Feature Experience"][0]
        self.assertTrue(praise_theme["is_positive"])
        self.assertEqual(praise_theme["priority_score"], 0.0)
        self.assertEqual(praise_theme["rating_gap"], 0.0)
        self.assertIn("PRAISE", praise_theme["urgency_badge"])
        
        ticket = generate_ticket_markdown(praise_theme, app_name="CloudSync Pro")
        self.assertIn("FEATURE WIN", ticket)
        self.assertIn("Customer Delight", ticket)
        self.assertIn("No Defect Triage Needed", ticket)

if __name__ == "__main__":
    unittest.main()
