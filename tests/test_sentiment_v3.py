import unittest
from pipeline.sentiment_v3 import SentimentV3Engine

class TestSentimentV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = SentimentV3Engine(use_transformer=False)

    def test_mixed_sentiment_clause_splitting(self):
        """Verifies that contrastive conjunctions split clauses into mixed sentiment."""
        res1 = self.engine.analyze("Great UI and clean design, BUT the app crashes after opening.")
        self.assertEqual(res1["sentiment"], "mixed")
        self.assertTrue(res1["is_mixed"])

        res2 = self.engine.analyze("Love the offline vault, however syncing is terribly slow.")
        self.assertEqual(res2["sentiment"], "mixed")

        res3 = self.engine.analyze("Very useful app, although fingerprint unlock fails frequently.")
        self.assertEqual(res3["sentiment"], "mixed")

    def test_hinglish_contrastive_splitting(self):
        """Verifies Hinglish contrast marker 'phir bhi' triggers clause split."""
        res = self.engine.analyze("Good password manager app, phir bhi login screen freezes.")
        self.assertEqual(res["sentiment"], "mixed")

    def test_pure_positive_and_negative(self):
        """Verifies pure positive and negative reviews maintain high confidence."""
        pos = self.engine.analyze("Amazing password manager, perfectly secure and smooth.")
        self.assertEqual(pos["sentiment"], "positive")
        self.assertGreaterEqual(pos["confidence"], 0.70)

        neg = self.engine.analyze("Horrible app, completely broken and crashes on launch.")
        self.assertEqual(neg["sentiment"], "negative")
        self.assertGreaterEqual(neg["confidence"], 0.70)

    def test_rating_assisted_calibration_layer(self):
        """Verifies low confidence ties are calibrated by star rating."""
        # Ambiguous short review with 5 stars
        res_high = self.engine.analyze("ok", rating=5)
        self.assertEqual(res_high["sentiment"], "positive")

        # Ambiguous short review with 1 star
        res_low = self.engine.analyze("ok", rating=1)
        self.assertEqual(res_low["sentiment"], "negative")

if __name__ == "__main__":
    unittest.main()
