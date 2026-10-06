import os
import pandas as pd
from typing import Tuple, Dict, Any

REQUIRED_COLUMNS = ["review_id", "review_text", "rating", "date"]

def ingest_and_validate(csv_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Ingests reviews CSV, validates required schema, cleans data, 
    and returns cleaned DataFrame along with a data quality summary report.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Input file not found at {csv_path}")
        
    df = pd.read_csv(csv_path, encoding="utf-8")
    initial_count = len(df)
    
    # Check schema
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in CSV: {missing_cols}")
        
    # Check nulls
    null_texts = df["review_text"].isna().sum()
    df = df.dropna(subset=["review_text"])
    df["review_text"] = df["review_text"].astype(str).str.strip()
    
    # Filter empty / very short strings
    df = df[df["review_text"].str.len() >= 5]
    
    # Deduplicate
    pre_dedup = len(df)
    df = df.drop_duplicates(subset=["review_text"]).reset_index(drop=True)
    duplicates_dropped = pre_dedup - len(df)
    
    # Ensure date format
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    invalid_dates = df["date"].isna().sum()
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    
    # Ensure rating is 1-5 integer
    df["rating"] = df["rating"].fillna(3).clip(1, 5).astype(int)
    
    report = {
        "initial_rows": initial_count,
        "valid_rows": len(df),
        "null_texts_dropped": int(null_texts),
        "duplicates_dropped": int(duplicates_dropped),
        "invalid_dates_dropped": int(invalid_dates),
        "min_date": str(df["date"].min()),
        "max_date": str(df["date"].max()),
        "rating_breakdown": df["rating"].value_counts().to_dict(),
    }
    
    return df, report

if __name__ == "__main__":
    csv_file = os.path.join(os.path.dirname(__file__), "..", "data", "reviews_10k.csv")
    df, report = ingest_and_validate(csv_file)
    print("Ingestion Validation Report:")
    for k, v in report.items():
        print(f"  {k}: {v}")
