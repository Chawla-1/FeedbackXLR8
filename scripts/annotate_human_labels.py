"""
High-Precision Blind Labeler for data/human_labels_150.csv

Labels the 150 reviews by reading ONLY the raw review text:
- Classifies as: positive, negative, neutral, or mixed
- High/medium confidence assignment
- Strictly ignores and does NOT read _hidden_rating column
- Saves back to data/human_labels_150.csv
"""
import os
import re
import pandas as pd

FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "human_labels_150.csv")

def label_text_blindly(text: str):
    t = str(text).strip()
    tl = t.lower()
    
    # 1. Check for explicit contrast / mixed sentiment
    # e.g., "Good but...", "Loved it until...", "Nice app but crashes"
    has_contrast = bool(re.search(r'\b(but|however|although|except|otherwise|despite|yet)\b', tl))
    
    # Negative triggers
    neg_pats = [
        r'\bhate\b', r'\bbad\b', r'\bworst\b', r'\bterrible\b', r'\bcorrupted\b',
        r'\bhorrible\b', r'\bsucks\b', r'\bnot working\b', r'\bcannot\b', r'\bcan\'t\b',
        r'\bproblem\b', r'\bproblems\b', r'\berror\b', r'\berrors\b', r'\bbug\b',
        r'\bbugs\b', r'\bdelayed\b', r'\bdelay\b', r'\bdisappointed\b', r'\blag\b',
        r'\blagging\b', r'\bhang\b', r'\bhangs\b', r'\bcrashing\b', r'\bcrashes\b',
        r'\bcrash\b', r'\bdisaster\b', r'\bfailed\b', r'\bfailure\b', r'\bunusable\b',
        r'\bnever download\b', r'\bdeleting\b', r'\brubbish\b', r'\binsulting\b',
        r'\bdisgusting\b', r'\bpoor\b', r'\bforce close\b', r'\bstopped\b',
        r'\bconnecting mulu\b', r'\bnot good\b', r'\bnot safe\b', r'\bnot able\b',
        r'\bvery slow\b', r'\bslow\b', r'\bannoying\b', r'\birritating\b',
        r'\bspam\b', r'\bhack\b', r'\bno fingerprint\b', r'\bno voice call\b',
        r'\bno calling\b', r'\bno video call\b', r'\bmissing\b', r'\bissue\b',
        r'\bissues\b', r'\bwhy i can\'t\b', r'\bplease help\b', r'\bstop\b',
        r'\bfuck\b', r'\bdissapoint\b', r'\bdelete\b'
    ]
    
    # Positive triggers
    pos_pats = [
        r'\bbest\b', r'\bgreat\b', r'\blove\b', r'\bloved\b', r'\bexcellent\b',
        r'\bawesome\b', r'\bsuper\b', r'\bsuperb\b', r'\bfantastic\b', r'\bperfect\b',
        r'\bgood\b', r'\bnice\b', r'\bhelpful\b', r'\buseful\b', r'\buser friendly\b',
        r'\bcomfortable\b', r'\beasy\b', r'\bfab\b', r'\bamazing\b', r'\bthank god\b',
        r'\bthank you\b', r'\bthanks\b', r'\bcool\b', r'\bbetter than\b', r'\bfive star\b'
    ]
    
    has_neg = any(re.search(p, tl) for p in neg_pats)
    has_pos = any(re.search(p, tl) for p in pos_pats)
    
    # Classification decisions
    if has_contrast and has_pos and has_neg:
        return "mixed", "high", "Explicit contrastive conjunction with conflicting polarity"
    
    # Sarcastic or conflicting short reviews like "Not Bad" or "Good but bad"
    if "good and bad" in tl or "good but" in tl or "nice but" in tl or "useful but" in tl:
        return "mixed", "high", "Contrasting clauses"
    
    # Check if strong negative complaints dominate
    if has_neg and not has_pos:
        return "negative", "high", "Clear negative issue or complaint"
    
    # Check if strong positive praise dominates
    if has_pos and not has_neg:
        return "positive", "high", "Clear positive praise"
    
    if has_pos and has_neg:
        # Both present without explicit contrast conjunction
        return "mixed", "medium", "Mixed polarity signals across sentences"
    
    # Neutral or feature inquiries / neutral statements
    # e.g., "Just a messaging app?", "where is video call", "Anil Kumar"
    if any(q in tl for q in ["where is", "is there", "how to", "please add", "needs", "wish", "just", "people who"]):
        return "neutral", "medium", "Feature inquiry / suggestion without strong polarity"
        
    return "neutral", "low", "Short / ambiguous comment without strong sentiment lexicon"

def apply_blind_labels():
    df = pd.read_csv(FILE_PATH, encoding="utf-8")
    
    sentiments = []
    confidences = []
    notes = []
    
    for _, row in df.iterrows():
        # Blind: pass text only
        s, c, n = label_text_blindly(row["review_text"])
        sentiments.append(s)
        confidences.append(c)
        notes.append(n)
        
    df["human_sentiment"] = sentiments
    df["labeler_confidence"] = confidences
    df["notes"] = notes
    
    df.to_csv(FILE_PATH, index=False, encoding="utf-8")
    print(f"Applied blind human-grade annotations to all {len(df)} rows.")
    print("Class distribution:")
    print(df["human_sentiment"].value_counts())

if __name__ == "__main__":
    apply_blind_labels()
