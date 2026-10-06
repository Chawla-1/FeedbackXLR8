import os
import requests
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
RAW_FILE = os.path.join(DATA_DIR, "app_reviews_raw.parquet")

URL = "https://huggingface.co/api/datasets/sealuzh/app_reviews/parquet/default/train/0.parquet"

print(f"Downloading from {URL}...")
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(URL, headers=headers, stream=True)
resp.raise_for_status()

with open(RAW_FILE, "wb") as f:
    total_bytes = 0
    for chunk in resp.iter_content(chunk_size=1024 * 1024):
        if chunk:
            f.write(chunk)
            total_bytes += len(chunk)
            print(f"Downloaded {total_bytes / (1024*1024):.2f} MB...", flush=True)

print(f"Saved raw dataset to {RAW_FILE} ({os.path.getsize(RAW_FILE)} bytes).")

df = pd.read_parquet(RAW_FILE)
print("\nDataset Info:")
print(f"Total Rows: {len(df):,}")
print("Columns:", df.columns.tolist())
print("\nFirst 3 rows:")
print(df.head(3))
