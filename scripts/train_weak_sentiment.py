"""
Train an offline TF-IDF + Logistic Regression sentiment classifier using rating-derived weak labels.
Rating Weak Supervision Mapping:
  - 1 or 2 stars -> 'negative'
  - 3 stars      -> 'neutral'
  - 4 or 5 stars -> 'positive'

Saves the lightweight model to data/sentiment_model.joblib for production inference.
"""
import os
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
REVIEWS_FILE = os.path.join(DATA_DIR, "reviews_10k.csv")
MODEL_FILE = os.path.join(DATA_DIR, "sentiment_model.joblib")

def rating_to_weak_label(rating: int) -> str:
    if rating <= 2:
        return "negative"
    elif rating == 3:
        return "neutral"
    else:
        return "positive"

def train_weak_supervision_model():
    print(f"Loading reviews from {REVIEWS_FILE}...")
    df = pd.read_csv(REVIEWS_FILE, encoding="utf-8")
    
    # Filter valid rows
    df = df[df["review_text"].notna() & df["rating"].notna()].copy()
    df["weak_label"] = df["rating"].astype(int).apply(rating_to_weak_label)
    
    print(f"Training dataset size: {len(df)} reviews.")
    print("Class distribution:\n", df["weak_label"].value_counts())
    
    X = df["review_text"].astype(str).tolist()
    y = df["weak_label"].tolist()
    
    print("Building TF-IDF + Logistic Regression pipeline...")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=10000,
            sublinear_tf=True,
            min_df=2,
            strip_accents="unicode",
            lowercase=True
        )),
        ("clf", LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            C=1.2,
            random_state=42,
            solver="lbfgs"
        ))
    ])
    
    print("Fitting model on 10,000 weakly labeled reviews...")
    pipeline.fit(X, y)
    
    y_pred = pipeline.predict(X)
    print("\nTraining Set Performance (against weak labels):")
    print(classification_report(y, y_pred, digits=3))
    
    print(f"Saving trained model to {MODEL_FILE}...")
    joblib.dump(pipeline, MODEL_FILE)
    print("Model training & serialization complete!")
    return pipeline

if __name__ == "__main__":
    train_weak_supervision_model()
