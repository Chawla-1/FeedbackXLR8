"""
FeedbackXLR8 — Sentiment Engine v3.0 (pipeline/sentiment_v3.py)
Next-generation sentiment classifier combining:
1. Multi-clause contrastive splitting (handles 'Great UI, BUT crashes after 5 minutes')
2. Transformer / calibrated offline ML inference with confidence scoring
3. Rating-assisted calibration layer (Rule 1: preserves fallback safety)
4. Sub-clause aspect polarity extraction
"""
import os
import re
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional

# Contrastive conjunctions (English + Hinglish)
CONTRAST_PATTERN = re.compile(
    r"\b(but|however|though|although|yet|phir bhi|lekin|parantu|nevertheless|nonetheless|except that|still|despite)\b",
    re.IGNORECASE
)

class SentimentV3Engine:
    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest", use_transformer: bool = True):
        self.model_name = model_name
        self.use_transformer = use_transformer
        self.hf_pipeline = None
        self.offline_ml_pipeline = None
        self._cache: Dict[str, Dict[str, Any]] = {}

        # 1. Load offline ML pipeline as reliable zero-latency baseline
        ml_path = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment_model.joblib")
        if os.path.exists(ml_path):
            try:
                self.offline_ml_pipeline = joblib.load(ml_path)
            except Exception:
                self.offline_ml_pipeline = None

        # 2. Try loading HuggingFace Transformer if requested
        if self.use_transformer:
            try:
                from transformers import pipeline
                # Use CPU friendly fast sentiment pipeline
                self.hf_pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.model_name,
                    device=-1, # CPU
                    top_k=None,
                    truncation=True,
                    max_length=512
                )
            except Exception as e:
                # Silently fallback to offline ML without failing
                self.hf_pipeline = None

    def split_clauses(self, text: str) -> List[Dict[str, str]]:
        """
        Splits text on contrastive markers (e.g. 'Great UI, BUT crashes').
        Returns list of {'clause': str, 'marker': str}.
        """
        text = str(text).strip()
        parts = []
        matches = list(CONTRAST_PATTERN.finditer(text))
        if not matches:
            return [{"clause": text, "marker": ""}]

        prev_end = 0
        for m in matches:
            start, end = m.span()
            clause_before = text[prev_end:start].strip(" ,;.-")
            if clause_before:
                parts.append({"clause": clause_before, "marker": ""})
            marker_word = m.group(1).lower()
            prev_end = end
            # Next clause begins after marker

        clause_after = text[prev_end:].strip(" ,;.-")
        if clause_after:
            parts.append({"clause": clause_after, "marker": marker_word})

        return parts if parts else [{"clause": text, "marker": ""}]

    def _score_single_clause(self, text: str) -> Tuple[str, float]:
        """Classifies a single clause without contrast markers."""
        t_clean = text.strip()
        if not t_clean:
            return "neutral", 0.50

        # Strong domain cue check
        t_lower = t_clean.lower()
        pos_words = ["great", "love", "best", "awesome", "good", "useful", "easy", "perfect", "amazing", "smooth", "helpful", "decent", "secure", "nice"]
        neg_words = ["crash", "crashes", "freeze", "freezes", "bug", "broken", "slow", "terribly", "terrible", "lag", "drain", "worst", "hate", "fails", "fail", "error", "sluggish", "unusable"]
        has_pos = any(w in t_lower for w in pos_words)
        has_neg = any(w in t_lower for w in neg_words)

        # Try HuggingFace pipeline first
        if self.hf_pipeline is not None:
            try:
                out = self.hf_pipeline(t_clean[:512])[0]
                best = max(out, key=lambda x: x["score"])
                raw_label = best["label"].lower()
                conf = float(best["score"])

                if "pos" in raw_label or raw_label in ["5 stars", "4 stars"]:
                    return "positive", conf
                elif "neg" in raw_label or raw_label in ["1 star", "2 stars"]:
                    return "negative", conf
                else:
                    return "neutral", conf
            except Exception:
                pass

        # Use offline trained TF-IDF + Logistic Regression
        if self.offline_ml_pipeline is not None:
            try:
                probs = self.offline_ml_pipeline.predict_proba([t_clean])[0]
                classes = list(self.offline_ml_pipeline.classes_)
                best_idx = int(np.argmax(probs))
                best_label = str(classes[best_idx]).lower()
                conf = float(probs[best_idx])

                # Check if strong domain cues contradict weak model prediction
                if has_neg and not has_pos:
                    if best_label != "negative" or conf < 0.75:
                        return "negative", 0.85
                elif has_pos and not has_neg:
                    if best_label != "positive" or conf < 0.75:
                        return "positive", 0.85

                return best_label, conf
            except Exception:
                pass

        # Lexicon fallback (deterministic)
        if has_pos and not has_neg:
            return "positive", 0.85
        elif has_neg and not has_pos:
            return "negative", 0.85
        elif has_pos and has_neg:
            return "mixed", 0.75
        else:
            return "neutral", 0.60

    def analyze(self, text: str, rating: Optional[int] = None, review_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes review text with clause-splitting, sentiment classification,
        confidence scoring, and optional rating calibration.
        """
        cache_key = f"{text}|{rating}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        clauses = self.split_clauses(text)

        # Multi-clause evaluation
        if len(clauses) > 1:
            clause_results = []
            for c_info in clauses:
                c_txt = c_info["clause"]
                if len(c_txt) >= 2:
                    lbl, conf = self._score_single_clause(c_txt)
                    clause_results.append({"clause": c_txt, "sentiment": lbl, "confidence": conf, "marker": c_info["marker"]})

            sentiments = [c["sentiment"] for c in clause_results]
            has_pos = "positive" in sentiments
            has_neg = "negative" in sentiments

            if has_pos and has_neg:
                res = {
                    "sentiment": "mixed",
                    "confidence": round(float(np.mean([c["confidence"] for c in clause_results])), 4),
                    "is_mixed": True,
                    "clauses": clause_results,
                    "engine": "v3_clause_splitter",
                }
                self._cache[cache_key] = res
                return res
            elif has_neg:
                final_sent = "negative"
            elif has_pos:
                final_sent = "positive"
            else:
                final_sent = "neutral"

            conf = round(float(np.mean([c["confidence"] for c in clause_results])), 4)
        else:
            final_sent, conf = self._score_single_clause(text)
            clause_results = [{"clause": text, "sentiment": final_sent, "confidence": conf, "marker": ""}]

        # Rating calibration layer (Item 1.4)
        is_mixed = (final_sent == "mixed")
        if rating is not None and not is_mixed:
            r = int(rating)
            # Ambiguous/neutral or low-confidence tiebreak
            if conf < 0.70 or final_sent == "neutral":
                if r <= 2:
                    final_sent = "negative"
                    conf = max(conf, 0.75)
                elif r >= 4:
                    final_sent = "positive"
                    conf = max(conf, 0.75)
            # Strong conflict tiebreak -> tag mixed
            elif final_sent == "positive" and r <= 2:
                final_sent = "mixed"
                is_mixed = True
            elif final_sent == "negative" and r >= 5:
                final_sent = "mixed"
                is_mixed = True

        res = {
            "sentiment": final_sent,
            "confidence": round(float(conf), 4),
            "is_mixed": is_mixed,
            "clauses": clause_results,
            "engine": "v3_hybrid",
        }
        self._cache[cache_key] = res
        return res
