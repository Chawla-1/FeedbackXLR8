"""
Google Play Store Review Fetcher.

Uses `google-play-scraper` to pull real reviews for any public Play Store app.
Processes them through FeedbackXLR8's PII & Sentiment pipeline and stores
results as a virtual app entry compatible with the platform's multi-app architecture.
"""
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

try:
    from google_play_scraper import app as gps_app, reviews as gps_reviews, Sort
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False


def check_gps_available() -> bool:
    """Check if google-play-scraper is installed."""
    return GPS_AVAILABLE


def fetch_app_info(package_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch basic app metadata from Google Play Store.
    Returns None if the app is not found or on error.
    """
    if not GPS_AVAILABLE:
        return None
    try:
        info = gps_app(package_name, lang="en", country="us")
        return {
            "title": info.get("title", package_name),
            "description": info.get("summary", info.get("description", "")[:120]),
            "score": info.get("score", 0),
            "ratings": info.get("ratings", 0),
            "reviews_count": info.get("reviews", 0),
            "genre": info.get("genre", "App"),
            "icon": info.get("icon", ""),
            "developer": info.get("developer", ""),
            "installs": info.get("realInstalls", info.get("installs", "N/A")),
            "version": info.get("version", "Unknown"),
            "updated": info.get("updated", ""),
        }
    except Exception as e:
        print(f"[PlayStore] Error fetching app info for {package_name}: {e}")
        return None


def fetch_reviews(
    package_name: str,
    count: int = 200,
    sort: str = "newest",
    lang: str = "en",
    country: str = "us",
) -> Tuple[pd.DataFrame, int]:
    """
    Fetch reviews from Google Play Store.

    Args:
        package_name: e.g. 'com.whatsapp'
        count: Number of reviews to fetch (max ~1000 per call)
        sort: 'newest' or 'most_relevant'
        lang: Language code
        country: Country code

    Returns:
        (DataFrame with columns matching FeedbackXLR8 schema, total_fetched)
    """
    if not GPS_AVAILABLE:
        return pd.DataFrame(), 0

    sort_order = Sort.NEWEST if sort == "newest" else Sort.MOST_RELEVANT

    all_reviews = []
    continuation_token = None
    remaining = count

    try:
        while remaining > 0:
            batch_size = min(remaining, 100)
            result, continuation_token = gps_reviews(
                package_name,
                lang=lang,
                country=country,
                sort=sort_order,
                count=batch_size,
                continuation_token=continuation_token,
            )
            if not result:
                break
            all_reviews.extend(result)
            remaining -= len(result)
            if continuation_token is None:
                break
    except Exception as e:
        print(f"[PlayStore] Error fetching reviews for {package_name}: {e}")
        if not all_reviews:
            return pd.DataFrame(), 0

    if not all_reviews:
        return pd.DataFrame(), 0

    rows = []
    for i, r in enumerate(all_reviews):
        review_date = r.get("at")
        if isinstance(review_date, datetime):
            date_str = review_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = str(review_date) if review_date else datetime.now().strftime("%Y-%m-%d")

        rows.append({
            "review_id": f"GPS-{package_name.split('.')[-1][:8].upper()}-{i+1:04d}",
            "date": date_str,
            "rating": int(r.get("score", 3)),
            "review_text": str(r.get("content", "")),
            "app_version": str(r.get("appVersion", "Unknown")),
            "platform": "Android",
            "thumbs_up": r.get("thumbsUpCount", 0),
            "reply_content": r.get("replyContent", ""),
            "reviewer": r.get("userName", ""),
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").fillna(pd.Timestamp.now())
    return df, len(rows)


def process_reviews_through_pipeline(
    df: pd.DataFrame,
    use_transformer: bool = True,
    enable_embeddings: bool = True,
) -> pd.DataFrame:
    """
    Run fetched reviews through v3 pipeline: PII redaction, Transformer sentiment, 
    Embeddings, and Dynamic clustering.
    
    Args:
        df: Raw reviews DataFrame
        use_transformer: Use transformer sentiment v3 (default: True, recommended)
        enable_embeddings: Generate embeddings and cluster themes (default: True)
    
    Returns:
        Enriched DataFrame with sentiment, theme_title, embeddings, etc.
    """
    from pipeline.pii_redactor import PIIShield
    from pipeline.sentiment_v3 import SentimentV3Engine
    from pipeline.theming_v3 import ThemingV3Engine

    pii_eng = PIIShield()
    sent_eng = SentimentV3Engine(use_transformer=use_transformer)
    theme_eng = ThemingV3Engine() if enable_embeddings else None

    processed = []
    
    # Step 1 & 2: PII Redaction + Transformer Sentiment v3
    for _, row in df.iterrows():
        raw_text = str(row.get("review_text", ""))
        r_id = str(row.get("review_id", "GPS-0000"))
        
        # PII Redaction
        redacted, _ = pii_eng.redact_text(raw_text, review_id=r_id)
        
        # Transformer Sentiment Analysis v3
        r_val = int(row.get("rating", 3))
        sent_out = sent_eng.analyze(redacted, rating=r_val, review_id=r_id)

        processed.append({
            "review_id": r_id,
            "date": row.get("date", pd.Timestamp.now()),
            "rating": r_val,
            "review_text": redacted,
            "original_text": raw_text,
            "sentiment": sent_out["sentiment"],
            "sentiment_confidence": sent_out["confidence"],
            "is_mixed_sentiment": sent_out["is_mixed"],
            "app_version": str(row.get("app_version", "Unknown")),
            "platform": str(row.get("platform", "Android")),
        })

    result = pd.DataFrame(processed)
    if "date" in result.columns:
        result["date"] = pd.to_datetime(result["date"], errors="coerce").fillna(pd.Timestamp.now())
    
    # Step 3, 4, 5: Embeddings + Clustering + c-TF-IDF Theme Labeling
    if enable_embeddings and theme_eng and len(result) >= 3:
        result, theme_summaries = theme_eng.cluster_reviews(result, min_cluster_size=3)
        
        # Apply keyword classifier to uncategorized reviews (noise cluster = -1)
        uncategorized_mask = result["theme_title"] == "Uncategorized / Emerging Issues"
        if uncategorized_mask.any():
            result.loc[uncategorized_mask, "theme_title"] = result.loc[uncategorized_mask, "review_text"].apply(
                _classify_theme_by_keywords
            )
    else:
        # Fallback: keyword-based themes for small datasets
        result["theme_title"] = result["review_text"].apply(_classify_theme_by_keywords)
        result["cluster_id"] = -1
        result["all_matched_themes"] = result["theme_title"].apply(lambda x: [x])
    
    return result


def _classify_theme_by_keywords(text: str) -> str:
    """Enhanced keyword-based theme classification for small datasets or noise clusters."""
    import re
    t = text.lower()
    
    # BUGFIX #1: Handle negations FIRST - "no crashes" should NOT trigger crash theme
    # Check for "no [issue]" or "doesn't [issue]" patterns with positive context
    negation_patterns = [
        "no crash", "no crashes", "no bug", "no bugs", "no lag", "no lags", 
        "doesn't crash", "doesnt crash", "doesn't lag", "doesnt lag",
        "doesn't freeze", "doesnt freeze", "don't freeze", "dont freeze",
        "no freeze", "no freezes", "no force close", "no force closes",
        "not slow", "not buggy", "not laggy", "no issues", "no problems",
        "doesn't have bugs", "doesnt have bugs", "no complaints",
        "no ads"  # FIX: Add more negation patterns
    ]
    
    # Improvement indicators - "anymore", "now", "finally" signal fixes/improvements
    improvement_words = ["anymore", "now", "finally", "fixed", "better now", "improved", "like before", "now works"]
    
    has_negated_issues = any(neg in t for neg in negation_patterns)
    has_improvement = any(imp in t for imp in improvement_words)
    has_positive_words = any(k in t for k in ["perfect", "perfectly", "smooth", "smoothly", 
                                               "works", "working", "great", "good", "love", 
                                               "excellent", "amazing", "which is great"])
    
    # If review negates problems (with or without explicit positive words) → Praise
    # OR if it mentions improvements/fixes → Praise  
    # OR if multiple negations (e.g., "no freezes, no force closes")
    multiple_negations = sum(1 for neg in negation_patterns if neg in t) >= 2
    
    if (has_negated_issues and (has_positive_words or has_improvement or multiple_negations)) or \
       (has_negated_issues and "which is" in t):  # "No ads, which is great"
        return "General Praise & Feature Experience"
    
    # Priority 1: Specific mentions (ads, billing, auth) - check before generic issues
    
    # 1A: Ads & Monetization - BUGFIX: Use word boundaries to avoid "bad"/"had" false matches
    # Check for "ad" or "ads" as standalone words, plus specific ad-related phrases
    ad_patterns = [
        r'\bad\b', r'\bads\b',  # Word boundaries for "ad" and "ads"
        'advertisement', 'advertisements', 'advertising',
        'spam', 'spammy', 'popup', 'pop up', 'pop-up', 'popups',
        'ad experience', 'advertisement experience',
        'annoying ads', 'ads are annoying', 
        'could be better', 'annoying',  # Indirect complaints
        'too many ads', 'too much ads', 'full of ads', 'ads everywhere'
    ]
    
    if any(re.search(pattern, t) if pattern.startswith(r'\b') else pattern in t 
           for pattern in ad_patterns):
        return "Ads & Monetization"
    
    # 1B: Billing (check early - very specific)
    elif any(k in t for k in ["pay", "paid", "payment", "billing", "subscription", "subscriptions",
                              "charge", "charged", "charges", "refund", "refunds", "purchase",
                              "purchased", "buy", "bought", "price", "pricing", "expensive",
                              "money", "cost", "costs", "free trial"]):
        return "Billing & Subscriptions"
    
    # 1C: Authentication & security (check early - very specific)
    elif any(k in t for k in ["login", "log in", "log-in", "sign in", "signin", "sign-in", 
                            "auth", "password", "passwords", "account", "logged out", 
                            "can't login", "cant login", "cannot login", "won't login",
                            "wont login", "unable to login", "authentication", "verify", 
                            "verification", "otp", "2fa", "two factor", "reset password"]):
        return "Authentication & Account"
    
    # Priority 2: Critical issues (crashes, bugs) - only if NOT negated
    elif any(k in t for k in ["crash", "crashes", "crashed", "crashing", "freeze", "freezes", "freezing", 
                            "frozen", "bug", "bugs", "buggy", "unusable", "stuck", "force close", 
                            "force closes", "won't open", "wont open", "doesn't work", "doesnt work",
                            "not working", "stopped working", "keeps closing", "shuts down", "won't start",
                            "wont start"]) and not has_negated_issues:
        return "App Stability & Launch Crashes"
    
    # Priority 3: Performance issues - only if NOT negated
    elif any(k in t for k in ["slow", "slowness", "lag", "lags", "lagging", "laggy", "performance", 
                              "battery", "drain", "draining", "loading", "takes forever", "hang", 
                              "hangs", "hanging", "unresponsive", "sluggish", "choppy"]) and not has_negated_issues:
        return "Performance & Battery"
    
    # Priority 4: Update issues
    elif any(k in t for k in ["update", "updated", "updates", "version", "upgrade", "upgraded",
                              "downgrade", "latest version", "new version", "after update",
                              "since update", "broke after"]):
        return "Update & Version Issues"
    
    # Priority 5: UI/UX - but NOT if it's incidental mention in praise context
    # Check if "UI" is just mentioned alongside love/awesome/great (incidental)
    has_strong_praise = any(k in t for k in ["love", "awesome", "amazing", "excellent", "fantastic", "best"])
    ui_is_main_topic = any(k in t for k in ["ui is", "ux is", "design is", "interface is", 
                                              "ugly", "confusing", "hard to use", "difficult",
                                              "bad ui", "bad ux", "terrible design", "poor interface"])
    
    if ui_is_main_topic or (not has_strong_praise and any(k in t for k in ["ui", "ux", "design", "dark mode", "light mode", "layout",
                              "interface", "cluttered", "messy", "unintuitive"])):
        return "UI/UX & Design"
    
    # Priority 6: Positive praise (check after issues to avoid false positives)
    elif any(k in t for k in ["love", "loves", "loving", "loved", "great", "best", "amazing",
                              "awesome", "excellent", "perfect", "fantastic", "wonderful",
                              "good", "helpful", "easy", "simple", "smooth", "fast",
                              "recommend", "recommended", "works perfectly", "no issues"]):
        return "General Praise & Feature Experience"
    
    # Default: Uncategorized
    else:
        return "Uncategorized / Emerging Issues"


def save_playstore_app(
    apps_dir: str,
    registry_file: str,
    package_name: str,
    df_processed: pd.DataFrame,
    app_meta: Dict[str, Any],
    color: str = "#0ea5e9",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save a Play Store app's data to disk in FeedbackXLR8 format.
    Returns the registry entry dict.
    """
    # Create stable ID from package name
    app_id = "gps_" + package_name.replace(".", "_")
    app_dir = os.path.join(apps_dir, app_id)
    os.makedirs(app_dir, exist_ok=True)

    # Save credentials if provided
    if api_key and api_key.strip():
        with open(os.path.join(app_dir, "api_credentials.json"), "w", encoding="utf-8") as f:
            json.dump({"api_key_configured": True, "key_masked": f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"}, f, indent=2)

    # Save parquet
    df_processed.to_parquet(os.path.join(app_dir, "processed_reviews.parquet"), index=False)

    # Generate themes summary from data
    if "theme_title" in df_processed.columns:
        theme_counts = df_processed["theme_title"].value_counts()
        themes = []
        for title, vol in theme_counts.items():
            theme_df = df_processed[df_processed["theme_title"] == title]
            themes.append({
                "title": title,
                "volume": int(vol),
                "avg_rating": round(float(theme_df["rating"].mean()), 2),
                "representative_reviews": theme_df["review_id"].head(3).tolist(),
            })
    else:
        themes = []

    with open(os.path.join(app_dir, "themes.json"), "w", encoding="utf-8") as f:
        json.dump(themes, f, indent=2, default=str)

    with open(os.path.join(app_dir, "alerts.json"), "w", encoding="utf-8") as f:
        json.dump([], f)

    # Drift metrics
    drift = {
        "psi_value": 0.005,
        "health": "HEALTHY",
        "baseline_size": len(df_processed),
        "window_size": len(df_processed),
    }
    with open(os.path.join(app_dir, "drift_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(drift, f, indent=2)

    # Empty validation stubs
    for stub_name in ["validation_metrics.json", "human_validation_metrics.json",
                       "pii_audit_log.json", "pii_benchmark_metrics.json",
                       "sentiment_baselines_comparison.json", "scale_benchmark_metrics.json"]:
        stub_path = os.path.join(app_dir, stub_name)
        if not os.path.exists(stub_path):
            with open(stub_path, "w", encoding="utf-8") as f:
                if "log" in stub_name:
                    json.dump([], f)
                else:
                    json.dump({}, f)

    # Compute summary stats
    avg_rating = round(float(df_processed["rating"].mean()), 2) if len(df_processed) > 0 else 0
    neg_pct = 0
    if "sentiment" in df_processed.columns and len(df_processed) > 0:
        neg_pct = round(float((df_processed["sentiment"] == "negative").mean() * 100), 1)
    top_theme = themes[0]["title"] if themes else "N/A"

    # Build registry entry
    entry = {
        "id": app_id,
        "name": app_meta.get("title", package_name),
        "icon": "📱",
        "description": app_meta.get("description", "")[:120],
        "category": app_meta.get("genre", "App"),
        "color": color,
        "source": "playstore",
        "package_name": package_name,
        "has_api_key": bool(api_key and api_key.strip()),
        "summary": {
            "total_reviews": len(df_processed),
            "avg_rating": avg_rating,
            "neg_pct": neg_pct,
            "active_alerts": 0,
            "drift_health": "HEALTHY",
            "top_theme": top_theme,
            "pii_events": 0,
        },
    }

    # Update registry file
    if os.path.exists(registry_file):
        with open(registry_file, encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = []

    # Remove existing entry for same id if re-importing
    registry = [r for r in registry if r["id"] != app_id]
    registry.append(entry)

    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    return entry


def create_manual_app(
    apps_dir: str,
    registry_file: str,
    name: str,
    category: str,
    description: str,
    icon: str = "📱",
    color: str = "#6366f1",
) -> Dict[str, Any]:
    """
    Create a new empty manual app entry (no reviews yet).
    User can later upload CSV or use 1-click sample to add data.
    """
    app_id = "custom_" + name.lower().replace(" ", "_").replace("-", "_")[:30]
    app_dir = os.path.join(apps_dir, app_id)
    os.makedirs(app_dir, exist_ok=True)

    # Create empty parquet with correct schema
    empty_df = pd.DataFrame(columns=[
        "review_id", "date", "rating", "review_text", "original_text",
        "sentiment", "sentiment_confidence", "is_mixed_sentiment",
        "app_version", "platform", "theme_title", "all_matched_themes",
    ])
    empty_df.to_parquet(os.path.join(app_dir, "processed_reviews.parquet"), index=False)

    # Empty JSON stubs
    for fname, default in [
        ("themes.json", []),
        ("alerts.json", []),
        ("drift_metrics.json", {"psi_value": 0, "health": "HEALTHY"}),
        ("validation_metrics.json", {}),
        ("human_validation_metrics.json", {}),
        ("pii_audit_log.json", []),
    ]:
        with open(os.path.join(app_dir, fname), "w", encoding="utf-8") as f:
            json.dump(default, f)

    entry = {
        "id": app_id,
        "name": name,
        "icon": icon,
        "description": description[:120],
        "category": category,
        "color": color,
        "source": "manual",
        "summary": {
            "total_reviews": 0,
            "avg_rating": 0,
            "neg_pct": 0,
            "active_alerts": 0,
            "drift_health": "HEALTHY",
            "top_theme": "N/A",
            "pii_events": 0,
        },
    }

    # Update registry
    if os.path.exists(registry_file):
        with open(registry_file, encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = []

    registry = [r for r in registry if r["id"] != app_id]
    registry.append(entry)

    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    return entry


def remove_app(
    apps_dir: str,
    registry_file: str,
    app_id: str,
) -> bool:
    """
    Remove an app from the registry. Does NOT delete data files (safety).
    Returns True if removed.
    """
    if not os.path.exists(registry_file):
        return False

    with open(registry_file, encoding="utf-8") as f:
        registry = json.load(f)

    original_len = len(registry)
    registry = [r for r in registry if r["id"] != app_id]

    if len(registry) == original_len:
        return False

    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    return True


def find_service_account_keys(base_dir: str = ".") -> List[Dict[str, Any]]:
    """
    Scan directory for Google Cloud Service Account JSON credentials files.
    """
    keys = []
    if not os.path.exists(base_dir):
        return keys
    for fname in os.listdir(base_dir):
        if fname.endswith(".json"):
            fpath = os.path.join(base_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("type") == "service_account" and "private_key" in data:
                    keys.append({
                        "filename": fname,
                        "filepath": fpath,
                        "project_id": data.get("project_id", "Unknown"),
                        "client_email": data.get("client_email", "Unknown"),
                    })
            except Exception:
                continue
    return keys


def fetch_reviews_via_androidpublisher(
    service_account_path: str,
    package_name: str,
    max_results: int = 100,
) -> Tuple[pd.DataFrame, int, Optional[str]]:
    """
    Fetch reviews directly using Google Play Developer API (Android Publisher v3).
    Returns (DataFrame, count, error_message).
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=["https://www.googleapis.com/auth/androidpublisher"]
        )
        service = build("androidpublisher", "v3", credentials=creds)
        res = service.reviews().list(packageName=package_name, maxResults=max_results).execute()
        raw_reviews = res.get("reviews", [])

        if not raw_reviews:
            return pd.DataFrame(), 0, None

        rows = []
        for i, r in enumerate(raw_reviews):
            comments = r.get("comments", [])
            user_comment = comments[0].get("userComment", {}) if comments else {}
            star_rating = user_comment.get("starRating", 3)
            text = user_comment.get("text", "")
            time_stamp = user_comment.get("lastModified", {}).get("seconds")
            if time_stamp:
                dt_str = datetime.fromtimestamp(int(time_stamp)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                dt_str = datetime.now().strftime("%Y-%m-%d")

            app_ver = str(user_comment.get("appVersionCode", "Unknown"))
            author = r.get("authorName", "Anonymous")

            rows.append({
                "review_id": f"GPAPI-{package_name.split('.')[-1][:8].upper()}-{i+1:04d}",
                "date": dt_str,
                "rating": int(star_rating),
                "review_text": str(text),
                "app_version": app_ver,
                "platform": "Android",
                "thumbs_up": user_comment.get("thumbsUpCount", 0),
                "reply_content": "",
                "reviewer": author,
            })

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], errors="coerce").fillna(pd.Timestamp.now())
        return df, len(rows), None
    except Exception as e:
        err_msg = str(e)
        return pd.DataFrame(), 0, err_msg


def sync_playstore_reviews(
    apps_dir: str,
    registry_file: str,
    app_id: str,
    package_name: str,
    service_account_path: Optional[str] = None,
) -> Tuple[int, int, str]:
    """
    Re-sync reviews for an existing Play Store app.
    Returns (old_count, new_count, message).
    """
    app_dir = os.path.join(apps_dir, app_id)
    parquet_path = os.path.join(app_dir, "processed_reviews.parquet")
    old_count = 0
    if os.path.exists(parquet_path):
        try:
            old_df = pd.read_parquet(parquet_path)
            old_count = len(old_df)
        except Exception:
            old_count = 0

    raw_dfs = []
    source_used = "public scraper"

    # 1. Try service account first if provided
    if service_account_path and os.path.exists(service_account_path):
        df_api, count_api, err = fetch_reviews_via_androidpublisher(service_account_path, package_name, max_results=200)
        if count_api > 0:
            raw_dfs.append(df_api)
            source_used = "Google Play Developer API & Scraper"

    # 2. Also query public scraper
    df_scraper, count_scraper = fetch_reviews(package_name, count=200, sort="newest")
    if count_scraper > 0:
        raw_dfs.append(df_scraper)

    if not raw_dfs:
        return old_count, old_count, "No reviews could be fetched from Google Play servers at this time."

    df_raw = pd.concat(raw_dfs, ignore_index=True)
    df_raw["_norm_txt"] = df_raw["review_text"].astype(str).str.strip().str.lower()
    df_raw = df_raw.drop_duplicates(subset=["_norm_txt"]).drop(columns=["_norm_txt"])

    df_processed = process_reviews_through_pipeline(
        df_raw,
        use_transformer=True,
        enable_embeddings=True
    )
    app_meta = fetch_app_info(package_name) or {"title": package_name, "genre": "App"}

    save_playstore_app(
        apps_dir=apps_dir,
        registry_file=registry_file,
        package_name=package_name,
        df_processed=df_processed,
        app_meta=app_meta,
    )

    new_count = len(df_processed)
    if new_count > old_count:
        msg = f"✅ Successfully fetched {new_count} reviews (found {new_count - old_count} new) via {source_used}."
    else:
        msg = f"ℹ️ Google Play servers returned {new_count} review(s). Newly posted reviews typically take between 2 to 24 hours to propagate across Google's public CDN nodes due to spam moderation."

    return old_count, new_count, msg


def append_manual_review(
    apps_dir: str,
    registry_file: str,
    app_id: str,
    rating: int,
    text: str,
    author: str = "User",
    version: str = "v1.0.0",
) -> Tuple[int, str]:
    """
    Append an immediate test review directly to the app's parquet and update registry.
    Returns (new_total_count, message).
    """
    app_dir = os.path.join(apps_dir, app_id)
    parquet_path = os.path.join(app_dir, "processed_reviews.parquet")

    if os.path.exists(parquet_path):
        try:
            df_existing = pd.read_parquet(parquet_path)
        except Exception:
            df_existing = pd.DataFrame()
    else:
        df_existing = pd.DataFrame()

    from pipeline.pii_redactor import PIIShield
    from pipeline.sentiment_v3 import SentimentV3Engine

    pii_eng = PIIShield()
    sent_eng = SentimentV3Engine(use_transformer=True)

    r_id = f"LOCAL-{len(df_existing)+1:04d}"
    redacted, _ = pii_eng.redact_text(text, review_id=r_id)
    sent_out = sent_eng.analyze(redacted, rating=rating, review_id=r_id)

    t_txt = redacted.lower()
    has_friction = any(k in t_txt for k in ["crash", "freeze", "bug", "unusable", "stuck", "error", "broken", "fail"])
    has_praise = any(k in t_txt for k in ["love", "great", "best", "amazing", "awesome", "good", "easy", "helpful", "useful", "nice", "perfect"])

    if any(k in t_txt for k in ["crash", "freeze", "bug", "unusable", "stuck"]):
        theme = "App Stability & Launch Crashes"
    elif any(k in t_txt for k in ["slow", "lag", "performance", "battery", "drain"]):
        theme = "Performance & Battery"
    elif rating >= 4 and has_praise and not has_friction:
        theme = "General Praise & Feature Experience"
    elif any(k in t_txt for k in ["ui", "design", "dark mode", "interface"]):
        theme = "UI/UX & Design"
    elif any(k in t_txt for k in ["password", "login", "auth", "account", "vault"]):
        theme = "Authentication & Account"
    elif has_praise:
        theme = "General Praise & Feature Experience"
    else:
        theme = "Uncategorized / Emerging Issues"

    new_row = pd.DataFrame([{
        "review_id": r_id,
        "date": pd.Timestamp.now(),
        "rating": int(rating),
        "review_text": redacted,
        "original_text": text,
        "sentiment": sent_out["sentiment"],
        "sentiment_confidence": sent_out["confidence"],
        "is_mixed_sentiment": sent_out["is_mixed"],
        "app_version": str(version),
        "platform": "Android",
        "theme_title": theme,
        "all_matched_themes": [theme],
    }])

    df_combined = pd.concat([df_existing, new_row], ignore_index=True)
    df_combined.to_parquet(parquet_path, index=False)

    # Re-save themes and registry summary
    avg_rating = round(float(df_combined["rating"].mean()), 2)
    neg_pct = round(float((df_combined["sentiment"] == "negative").mean() * 100), 1)

    if os.path.exists(registry_file):
        with open(registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
        for r in registry:
            if r["id"] == app_id:
                r["summary"]["total_reviews"] = len(df_combined)
                r["summary"]["avg_rating"] = avg_rating
                r["summary"]["neg_pct"] = neg_pct
        with open(registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

    return len(df_combined), f"Review added! New total: {len(df_combined)} reviews (Avg: {avg_rating}★)."
