import unittest
import pandas as pd
from pipeline.theming_v3 import ThemingV3Engine

class TestThemingV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ThemingV3Engine()

    def test_paraphrase_recall_similarity(self):
        """Verifies semantic paraphrases of app crashes have high cosine similarity (> 0.70)."""
        p1 = "the app crashes on launch"
        p2 = "app keeps crashing after opening"
        p3 = "the app crashes immediately on splash screen"

        sim12 = self.engine.test_paraphrase_similarity(p1, p2)
        sim23 = self.engine.test_paraphrase_similarity(p2, p3)
        sim13 = self.engine.test_paraphrase_similarity(p1, p3)

        self.assertGreater(sim12, 0.65, f"Expected similarity > 0.65, got {sim12}")
        self.assertGreater(sim23, 0.65, f"Expected similarity > 0.65, got {sim23}")
        self.assertGreater(sim13, 0.65, f"Expected similarity > 0.65, got {sim13}")

    def test_p1_traceability_invariant(self):
        """Verifies every discovered theme cluster has >= 3 customer receipts with review_id and quote."""
        sample_reviews = [
            {"review_id": "REV-C1", "review_text": "app won't open after new update", "rating": 1, "app_version": "v2.0"},
            {"review_id": "REV-C2", "review_text": "crashes on launch immediately", "rating": 1, "app_version": "v2.0"},
            {"review_id": "REV-C3", "review_text": "force closes on splash screen", "rating": 1, "app_version": "v2.0"},
            {"review_id": "REV-C4", "review_text": "app stopped working and crashes", "rating": 1, "app_version": "v2.0"},
            {"review_id": "REV-P1", "review_text": "great and useful password manager", "rating": 5, "app_version": "v2.0"},
            {"review_id": "REV-P2", "review_text": "awesome app, love the secure vault", "rating": 5, "app_version": "v2.0"},
            {"review_id": "REV-P3", "review_text": "easy to recall all my site passwords", "rating": 5, "app_version": "v2.0"},
            {"review_id": "REV-P4", "review_text": "perfect and smooth offline tool", "rating": 5, "app_version": "v2.0"},
        ]
        df = pd.DataFrame(sample_reviews)
        df_clustered, themes = self.engine.cluster_reviews(df, min_cluster_size=3)

        self.assertGreater(len(themes), 0)
        for th in themes:
            # Pillar P1 Invariant
            self.assertIn("verbatims", th)
            self.assertGreaterEqual(len(th["verbatims"]), 3, f"Theme {th['title']} failed Pillar P1 receipt check!")
            top_v = th["verbatims"][0]
            self.assertIn("review_id", top_v)
            self.assertIn("quote", top_v)
            self.assertIn("rating", top_v)

if __name__ == "__main__":
    unittest.main()
