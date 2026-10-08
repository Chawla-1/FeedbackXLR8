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
    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english", use_transformer: bool = True):
        """
        Initialize Sentiment v3 Engine with DistilBERT for faster inference.
        
        Args:
            model_name: Transformer model to use (default: DistilBERT SST-2)
            use_transformer: Enable transformer inference (True for production)
        
        Performance:
            - DistilBERT: 40% smaller, 60% faster than BERT, 97% accuracy retention
            - Model size: ~268MB (vs 1.4GB for large models)
            - Speed: ~10-15 reviews/sec (vs 2 reviews/sec with RoBERTa-base)
        """
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
                # DistilBERT: 60% faster than BERT, 97% accuracy
                self.hf_pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.model_name,
                    device=-1,  # CPU inference
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
        
        Special case: "nothing but X" is NOT split (idiomatic phrase meaning "only X").
        """
        text = str(text).strip()
        
        # FIX: "nothing but" is an idiomatic phrase, not a contrast
        if "nothing but" in text.lower():
            return [{"clause": text, "marker": ""}]
        
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
        
        # FIX #1: Detect conditional/hypothetical statements (mixed sentiment)
        conditional_patterns = ["would be", "could be", "if only", "if it wasn't", "if it weren't", 
                               "except for", "aside from", "apart from", "without the", "without ads",
                               "would have been", "could have been"]
        has_conditional = any(pattern in t_lower for pattern in conditional_patterns)
        
        # FIX #2: Detect "nothing but X" = strong negative
        nothing_but = "nothing but" in t_lower
        
        # FIX #3: Expanded keyword lists
        pos_words = ["great", "love", "best", "awesome", "good", "useful", "easy", "perfect", "amazing", "smooth", "helpful", "decent", "secure", "nice", "excellent", "wonderful", "fantastic",
                     "5 stars", "4 stars", "five stars", "four stars"]  # Add rating mentions
        neg_words = ["crash", "crashes", "freeze", "freezes", "bug", "broken", "slow", "terribly", "terrible", "lag", "drain", "worst", "hate", "fails", "fail", "error", "sluggish", "unusable",
                     "charged me twice", "force close", "force closes", "keeps closing", "nothing but",
                     "1 star", "2 stars", "one star", "two stars"]  # Add bad rating mentions
        
        # FIX #4: Detect neutral indicators
        neutral_indicators = ["okay", "ok", "meh", "nothing special", "average", "decent"]
        has_neutral = any(ind in t_lower for ind in neutral_indicators)
        
        has_pos = any(w in t_lower for w in pos_words)
        has_neg = any(w in t_lower for w in neg_words)

        # FIX #5: Conditional + mixed sentiment = mixed
        if has_conditional and (has_pos or has_neg):
            return "mixed", 0.90
        
        # FIX #6: "Nothing but X" = strong negative
        if nothing_but:
            return "negative", 0.95

        # Try HuggingFace pipeline first
        if self.hf_pipeline is not None:
            try:
                out = self.hf_pipeline(t_clean[:512])[0]
                best = max(out, key=lambda x: x["score"])
                raw_label = best["label"].lower()
                conf = float(best["score"])

                if "pos" in raw_label or raw_label in ["5 stars", "4 stars"]:
                    pred_sentiment = "positive"
                elif "neg" in raw_label or raw_label in ["1 star", "2 stars"]:
                    pred_sentiment = "negative"
                else:
                    pred_sentiment = "neutral"
                
                # FIX #7: Override transformer if strong domain cues conflict
                if has_neg and not has_pos and pred_sentiment != "negative":
                    return "negative", 0.90
                elif has_pos and not has_neg and pred_sentiment != "positive":
                    return "positive", 0.90
                elif has_neutral and not (has_pos or has_neg):
                    return "neutral", 0.85
                    
                return pred_sentiment, conf
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
                elif has_neutral and not (has_pos or has_neg):
                    return "neutral", 0.85

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
        elif has_neutral:
            return "neutral", 0.80
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
        text_lower = text.lower()
        
        # FIX #11: "Nothing but X" with 1-star = definite negative
        nothing_but = "nothing but" in text_lower
        if rating is not None and rating == 1 and nothing_but:
            final_sent = "negative"
            conf = 0.95
        
        # FIX #10: Negations with high rating = positive (not mixed/negative)
        # Check if text has negations + high rating BEFORE is_mixed check
        has_negation = any(neg in text_lower for neg in ["no crash", "no bug", "no lag", "no freeze", "doesn't crash", "doesnt crash", "no issues", "no problems", "no force close", "doesn't have bug", "doesnt have bug", "not laggy", "not slow", "not buggy"])
        
        if rating is not None and rating >= 4 and has_negation and final_sent in ["mixed", "negative"]:
            final_sent = "positive"
            conf = 0.90
        
        # NOW set is_mixed based on final_sent (AFTER potential overrides above)
        is_mixed = (final_sent == "mixed")
        
        if rating is not None and not is_mixed:
            r = int(rating)
            
            # FIX #8: 3-star + neutral words = neutral (not negative/positive)
            has_neutral_words = any(w in text_lower for w in ["okay", "ok", "meh", "nothing special", "average"])
            if r == 3 and has_neutral_words and conf < 0.85:
                final_sent = "neutral"
                conf = 0.80
            
            # FIX #9: 1-star reviews should NEVER be positive/mixed unless truly contradictory
            elif r == 1 and final_sent != "negative":
                # Only keep non-negative if extremely high confidence positive (sarcasm detection)
                if conf < 0.95:
                    final_sent = "negative"
                    conf = 0.90
            
            # Ambiguous/neutral or low-confidence tiebreak
            elif conf < 0.70 or final_sent == "neutral":
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
