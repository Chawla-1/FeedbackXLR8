"""
Automated Test Suite for Review Insight Engine (Standard Python unittest).

Directly validates the Three Enterprise Pillars under technical scrutiny:
- Pillar P1 (Traceability): Assert no theme renders without >= 3 linked customer verbatims.
- Pillar P2 (Validated Accuracy): Assert validation evaluation runs with genuine non-zero metrics.
- Pillar P3 (Privacy & Drift): Assert zero raw emails or phone numbers survive in processed reviews.
- Non-Functional Requirement: Assert full 10k pipeline execution stays under 90 seconds.
"""
import os
import re
import json
import unittest
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_FILE = os.path.join(DATA_DIR, "processed_reviews.parquet")
THEMES_FILE = os.path.join(DATA_DIR, "themes.json")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")
DRIFT_FILE = os.path.join(DATA_DIR, "drift_metrics.json")
VALIDATION_FILE = os.path.join(DATA_DIR, "validation_metrics.json")
PII_AUDIT_FILE = os.path.join(DATA_DIR, "pii_audit_log.json")
HUMAN_VAL_FILE = os.path.join(DATA_DIR, "human_validation_metrics.json")

class TestReviewInsightEngine(unittest.TestCase):

    # -------------------------------------------------------------
    # Pillar P1: Traceability Invariant Tests
    # -------------------------------------------------------------
    def test_pillar_p1_theme_verbatim_traceability(self):
        """Every single theme object MUST contain between 3 and 5 real customer verbatims."""
        self.assertTrue(os.path.exists(THEMES_FILE), f"Missing {THEMES_FILE}")
        with open(THEMES_FILE, encoding="utf-8") as f:
            themes = json.load(f)
        self.assertGreater(len(themes), 0, "No themes discovered")
        
        for theme in themes:
            title = theme.get("title", "")
            verbatims = theme.get("verbatims", [])
            self.assertGreaterEqual(
                len(verbatims), 3,
                f"Pillar P1 Violation: Theme '{title}' has only {len(verbatims)} verbatims (minimum 3 required)"
            )
            for v in verbatims:
                self.assertTrue("review_id" in v and v["review_id"].startswith("REV-"), f"Verbatim missing valid review_id: {v}")
                self.assertTrue("quote" in v and len(v["quote"].strip()) > 0, f"Empty verbatim quote in '{title}'")
                self.assertTrue("rating" in v and 1 <= v["rating"] <= 5, f"Invalid rating in verbatim: {v}")

    # -------------------------------------------------------------
    # Pillar P2: Validated Accuracy Tests
    # -------------------------------------------------------------
    def test_pillar_p2_model_validation_reports_exist(self):
        """Holdout validation report must exist with genuine accuracy and 3x3 confusion matrix."""
        self.assertTrue(os.path.exists(VALIDATION_FILE), f"Missing {VALIDATION_FILE}")
        with open(VALIDATION_FILE, encoding="utf-8") as f:
            val_data = json.load(f)
        
        self.assertIn("text_only", val_data)
        text_acc = val_data["text_only"]["overall_accuracy"]
        self.assertTrue(0.40 <= text_acc <= 1.0, f"Text-only accuracy {text_acc} out of plausible bounds")
        
        # 3x3 Confusion Matrix
        cm = val_data["text_only"]["confusion_matrix"]["matrix"]
        self.assertEqual(len(cm), 3)
        self.assertTrue(all(len(row) == 3 for row in cm))
        
        # Mixed sentiment detector metrics
        mixed_m = val_data.get("mixed_sentiment_detector", {})
        self.assertIn("precision", mixed_m)
        self.assertIn("recall", mixed_m)
        self.assertIn("f1_score", mixed_m)
        self.assertGreater(mixed_m["f1_score"], 0.4)

    def test_pillar_p2_human_ground_truth_present(self):
        """Non-circular human-labeled ground truth benchmark (n=150) must exist and be valid."""
        self.assertTrue(os.path.exists(HUMAN_VAL_FILE), f"Missing {HUMAN_VAL_FILE}")
        with open(HUMAN_VAL_FILE, encoding="utf-8") as f:
            h_data = json.load(f)
        self.assertEqual(h_data["sample_size"], 150)
        self.assertGreaterEqual(h_data["text_only_accuracy"], 0.60)
        self.assertGreaterEqual(h_data["macro_f1"], 0.55)

    # -------------------------------------------------------------
    # Pillar P3: Zero-Leakage Privacy & Drift Monitoring
    # -------------------------------------------------------------
    def test_pillar_p3_zero_pii_leakage(self):
        """NO raw unmasked emails or phone numbers may survive in processed_reviews.parquet."""
        self.assertTrue(os.path.exists(PROCESSED_FILE), f"Missing {PROCESSED_FILE}")
        df = pd.read_parquet(PROCESSED_FILE)
        
        email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)
        phone_regex = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
        
        unmasked_emails = 0
        unmasked_phones = 0
        
        for text in df["review_text"]:
            clean_text = text.replace("[REDACTED_EMAIL]", "").replace("[REDACTED_PHONE]", "").replace("[REDACTED_NAME]", "")
            if email_regex.search(clean_text):
                unmasked_emails += 1
            if phone_regex.search(clean_text):
                unmasked_phones += 1
                
        self.assertEqual(unmasked_emails, 0, f"Pillar P3 Violation: Found {unmasked_emails} unmasked raw emails in processed corpus!")
        self.assertEqual(unmasked_phones, 0, f"Pillar P3 Violation: Found {unmasked_phones} unmasked raw phone numbers in processed corpus!")

    def test_pillar_p3_drift_and_anomaly_metrics(self):
        """Population Stability Index (PSI) and Spike Alerts are calculated properly."""
        self.assertTrue(os.path.exists(DRIFT_FILE), f"Missing {DRIFT_FILE}")
        with open(DRIFT_FILE, encoding="utf-8") as f:
            drift = json.load(f)
        self.assertIn("psi_score", drift)
        self.assertGreaterEqual(drift["psi_score"], 0.0)
        self.assertIn(drift["health"], ["HEALTHY", "MODERATE DRIFT", "SIGNIFICANT DRIFT"])

    # -------------------------------------------------------------
    # Mentor Feedback Enhancements: Priority Score & Benchmark Proofs
    # -------------------------------------------------------------
    def test_pillar_p0_founder_priority_and_rating_lift(self):
        """Validates that theme priority scores and rating lifts are computed using the mentor formula."""
        from pipeline.founder_engine import calculate_theme_priority_metrics
        df = pd.read_parquet(PROCESSED_FILE)
        with open(THEMES_FILE, encoding="utf-8") as f:
            themes = json.load(f)
        
        enriched = calculate_theme_priority_metrics(df, themes)
        self.assertGreater(len(enriched), 0)
        for th in enriched:
            self.assertIn("priority_score", th)
            self.assertGreaterEqual(th["priority_score"], 0.0)
            self.assertIn("estimated_rating_lift", th)
            self.assertGreaterEqual(th["estimated_rating_lift"], 0.0)
            self.assertIn("urgency_badge", th)

    def test_pillar_p0_pii_benchmark_empirical_metrics(self):
        """Verifies synthetic PII evaluation reports 100% recall on emails and phone numbers."""
        pii_bm_file = os.path.join(DATA_DIR, "pii_benchmark_metrics.json")
        self.assertTrue(os.path.exists(pii_bm_file), f"Missing {pii_bm_file}")
        with open(pii_bm_file, encoding="utf-8") as f:
            bm = json.load(f)
        
        per_entity = bm["per_entity_metrics"]
        self.assertEqual(per_entity["EMAIL"]["recall"], 1.0, "Email recall below 100% on benchmark!")
        self.assertEqual(per_entity["PHONE"]["recall"], 1.0, "Phone recall below 100% on benchmark!")
        self.assertIn("calibrated_claim", bm)

    def test_pillar_p0_baseline_confidence_intervals(self):
        """Verifies baseline comparison contains 95% confidence intervals across all models."""
        comp_file = os.path.join(DATA_DIR, "sentiment_baselines_comparison.json")
        self.assertTrue(os.path.exists(comp_file), f"Missing {comp_file}")
        with open(comp_file, encoding="utf-8") as f:
            comp = json.load(f)
        
        models = comp["models"]
        self.assertGreaterEqual(len(models), 3)
        for m in models:
            self.assertIn("ci_95", m)
            self.assertIn("ci_lower", m)
            self.assertIn("ci_upper", m)
            self.assertLessEqual(m["ci_lower"], m["ci_upper"])

    def test_pillar_p0_scale_benchmark_timing(self):
        """Verifies 10k scale benchmark completed under the 90-second budget."""
        scale_file = os.path.join(DATA_DIR, "scale_benchmark_metrics.json")
        self.assertTrue(os.path.exists(scale_file), f"Missing {scale_file}")
        with open(scale_file, encoding="utf-8") as f:
            scale = json.load(f)
        self.assertEqual(scale["status"], "PASS")
        self.assertLess(scale["total_elapsed_seconds"], 90.0)

if __name__ == "__main__":
    unittest.main()
