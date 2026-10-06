import re
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple

# Contrastive conjunctions that indicate a pivot in sentiment
CONTRASTIVE_CONJUNCTIONS = [
    r'\bbut\b', r'\bhowever\b', r'\balthough\b', r'\bexcept\b', 
    r'\bdespite\b', r'\byet\b', r'\bon the other hand\b', r'\botherwise\b'
]
CONTRAST_REGEX = re.compile('|'.join(CONTRASTIVE_CONJUNCTIONS), re.IGNORECASE)

# Expanded sentiment lexicons — the actual NLP signal
POSITIVE_WORDS = {
    'great', 'love', 'best', 'good', 'awesome', 'excellent', 'amazing', 'super',
    'fast', 'smooth', 'helpful', 'useful', 'nice', 'perfect', 'fantastic', 'clean',
    'wonderful', 'brilliant', 'favorite', 'recommend', 'easy', 'beautiful',
    'convenient', 'reliable', 'secure', 'impressive', 'intuitive', 'superb',
    'outstanding', 'cool', 'simple', 'powerful', 'flawless', 'pleasant',
    'enjoy', 'happy', 'satisfied', 'thank', 'thanks', 'loving', 'loved',
}
NEGATIVE_WORDS = {
    'bad', 'worst', 'terrible', 'horrible', 'crash', 'crashes', 'crashing', 'bug',
    'bugs', 'broken', 'slow', 'lag', 'laggy', 'freeze', 'freezes', 'drain', 'draining',
    'hate', 'error', 'failed', 'failure', 'cannot', "can't", 'useless', 'garbage', 'unusable',
    'awful', 'annoying', 'frustrating', 'disappointed', 'disappointing', 'pathetic',
    'sucks', 'stuck', 'worse', 'problem', 'problems', 'issue', 'issues',
    'fix', 'uninstall', 'remove', 'deleted', 'waste', 'spam', 'scam',
    'ugly', 'complicated', 'confusing', 'unreliable', 'unstable', 'rubbish',
    'ridiculous', 'stupid', 'poor', 'lacking', 'missing', 'wrong', 'painful',
}

# Negation patterns that flip sentiment
NEGATION_REGEX = re.compile(r'\b(not|no|never|neither|nobody|nothing|nowhere|nor|hardly|barely|scarcely|don\'t|doesn\'t|didn\'t|won\'t|wouldn\'t|shouldn\'t|couldn\'t|isn\'t|aren\'t|wasn\'t|weren\'t)\b', re.IGNORECASE)


class SentimentEngine:
    """
    Enterprise Sentiment Classifier.
    
    Supports two modes:
    - "text_only": Classification purely from review text (no rating leakage).
      This is the real NLP metric. Reported honestly alongside rating-assisted numbers.
    - "rating_assisted": Uses star rating as an additional calibration signal.
      Faster, higher accuracy, but should be disclosed as rating-informed.
    
    Mixed-sentiment detection runs independently of both modes.
    """
    def __init__(self, mode: str = "text_only"):
        self.mode = mode

    def detect_mixed_sentiment(self, text: str) -> Tuple[bool, float]:
        """
        Flags reviews with contrasting clauses (e.g. 'Loved it but crashes now').
        Returns (is_mixed, confidence).
        """
        text_lower = text.lower()
        if not CONTRAST_REGEX.search(text_lower):
            return False, 0.0
            
        words = set(re.findall(r'\b\w+\b', text_lower))
        has_pos = len(words.intersection(POSITIVE_WORDS)) > 0
        has_neg = len(words.intersection(NEGATIVE_WORDS)) > 0
        
        if has_pos and has_neg:
            return True, 0.85
        return False, 0.0

    def _classify_text_only(self, text: str) -> Dict[str, Any]:
        """
        Text-only sentiment classification. No rating column used.
        This is the honest NLP performance metric.
        """
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        pos_hits = words.intersection(POSITIVE_WORDS)
        neg_hits = words.intersection(NEGATIVE_WORDS)
        pos_count = len(pos_hits)
        neg_count = len(neg_hits)
        
        # Negation handling: check if negative words are preceded by negation
        has_negation = bool(NEGATION_REGEX.search(text_lower))
        
        # Score calculation
        pos_score = pos_count
        neg_score = neg_count
        
        # Simple negation flip: if negation present and only one polarity found, flip it
        if has_negation and pos_count > 0 and neg_count == 0:
            # "not good", "not great" → negative signal
            neg_score += 1
            pos_score = max(0, pos_score - 1)
        elif has_negation and neg_count > 0 and pos_count == 0:
            # "not bad", "no problem" → positive signal
            pos_score += 1
            neg_score = max(0, neg_score - 1)
        
        # Mixed sentiment (handled separately, but influences label)
        is_mixed, mixed_conf = self.detect_mixed_sentiment(text)
        
        # Determine label
        if is_mixed:
            label = "mixed"
            conf = mixed_conf
        elif neg_score > pos_score:
            label = "negative"
            conf = min(0.55 + 0.08 * neg_score, 0.92)
        elif pos_score > neg_score:
            label = "positive"
            conf = min(0.55 + 0.08 * pos_score, 0.92)
        elif pos_score == neg_score and pos_score > 0:
            # Equal signals → lean neutral/mixed
            label = "neutral"
            conf = 0.45
        else:
            # No lexicon hits at all → neutral with low confidence
            label = "neutral"
            conf = 0.35

        return {
            "sentiment": label,
            "confidence": round(conf, 3),
            "is_mixed": is_mixed,
            "pos_signals": pos_count,
            "neg_signals": neg_count,
        }

    def _classify_rating_assisted(self, text: str, rating: int) -> Dict[str, Any]:
        """
        Rating-assisted classification. Uses star rating as a calibration signal.
        Higher accuracy, but must be disclosed as rating-informed.
        """
        text_result = self._classify_text_only(text)
        text_label = text_result["sentiment"]
        is_mixed = text_result["is_mixed"]
        pos_count = text_result["pos_signals"]
        neg_count = text_result["neg_signals"]
        
        # Rating provides strong prior, text provides adjustment
        if rating <= 2:
            if text_label == "positive" and pos_count >= 2:
                # Text strongly contradicts rating → flag as mixed
                label = "mixed"
                conf = 0.65
            else:
                label = "negative"
                conf = 0.82 if neg_count > 0 else 0.72
        elif rating >= 4:
            if is_mixed:
                label = "mixed"
                conf = 0.75
            elif text_label == "negative" and neg_count >= 2:
                # Text strongly contradicts rating → flag as mixed
                label = "mixed"
                conf = 0.65
            else:
                label = "positive"
                conf = 0.82 if pos_count > 0 else 0.72
        else:
            # 3-star: defer to text analysis
            label = text_label
            conf = text_result["confidence"]
            
        return {
            "sentiment": label,
            "confidence": round(conf, 3),
            "is_mixed": is_mixed,
            "pos_signals": pos_count,
            "neg_signals": neg_count,
        }

    def analyze_text(self, text: str, rating: int = None) -> Dict[str, Any]:
        """
        Main entry point. Routes to text-only or rating-assisted based on mode and availability.
        """
        text_clean = str(text).strip()
        
        if self.mode == "text_only" or rating is None:
            return self._classify_text_only(text_clean)
        else:
            return self._classify_rating_assisted(text_clean, rating)

    def process_dataframe(self, df: pd.DataFrame, text_col: str = "review_text", rating_col: str = "rating") -> pd.DataFrame:
        df = df.copy()
        sentiments = []
        confidences = []
        mixed_flags = []
        
        for _, row in df.iterrows():
            text = str(row[text_col])
            if self.mode == "text_only":
                res = self.analyze_text(text, rating=None)
            else:
                rating = int(row[rating_col]) if rating_col in df.columns and pd.notna(row[rating_col]) else None
                res = self.analyze_text(text, rating)
            sentiments.append(res["sentiment"])
            confidences.append(res["confidence"])
            mixed_flags.append(res["is_mixed"])
            
        df["sentiment"] = sentiments
        df["sentiment_confidence"] = confidences
        df["is_mixed_sentiment"] = mixed_flags
        return df

if __name__ == "__main__":
    engine_text = SentimentEngine(mode="text_only")
    engine_rated = SentimentEngine(mode="rating_assisted")
    
    test_cases = [
        ("I love the clean UI and voice chat!", 5),
        ("Terrible bug, app keeps crashing every 5 seconds.", 1),
        ("Great app overall, but the latest update broke notification sound.", 3),
        ("It is okay, nothing special.", 3),
        ("Not bad at all, works fine.", 4),
        ("Oh great, another crash. Thanks for nothing.", 1),
    ]
    print("=== TEXT-ONLY MODE (real NLP metric) ===")
    for t, r in test_cases:
        res = engine_text.analyze_text(t)
        print(f"  '{t}' → {res['sentiment']} (conf: {res['confidence']})")
    
    print("\n=== RATING-ASSISTED MODE (calibrated) ===")
    for t, r in test_cases:
        res = engine_rated.analyze_text(t, r)
        print(f"  '{t}' [★{r}] → {res['sentiment']} (conf: {res['confidence']})")
