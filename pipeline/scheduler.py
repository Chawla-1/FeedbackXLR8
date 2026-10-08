"""
FeedbackXLR8 — Background Review Sync Scheduler
Automatically fetches and processes live Google Play reviews with transformer engine
for maximum accuracy in production environments.

Features:
- Periodic sync every N minutes (configurable)
- Uses transformer sentiment engine (v3) for best accuracy
- Generates embeddings and dynamic theme clustering
- Detects anomalies and triggers alerts in real-time
- Runs in background without blocking UI
"""
import os
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import pandas as pd

from pipeline.playstore_fetcher import (
    sync_playstore_reviews,
    fetch_reviews_via_androidpublisher,
    fetch_reviews,
)
from pipeline.pii_redactor import PIIShield
from pipeline.sentiment_v3 import SentimentV3Engine
from pipeline.theming_v3 import ThemingV3Engine
from pipeline.anomaly_engine import AnomalyAndDriftEngine
from config import GooglePlayConfig, ModelConfig, PerformanceConfig


logger = logging.getLogger("FeedbackXLR8.Scheduler")


class ReviewSyncScheduler:
    """
    Background scheduler for periodic review syncing with transformer processing.
    """
    
    def __init__(
        self,
        apps_dir: str,
        registry_file: str,
        sync_interval_minutes: int = 5,
        use_transformer: bool = True,
        enable_embeddings: bool = True,
        enable_clustering: bool = True,
    ):
        """
        Initialize scheduler.
        
        Args:
            apps_dir: Path to apps data directory
            registry_file: Path to app registry JSON
            sync_interval_minutes: How often to fetch new reviews (default: 5)
            use_transformer: Use transformer sentiment engine (default: True)
            enable_embeddings: Generate embeddings for clustering (default: True)
            enable_clustering: Run dynamic clustering (default: True)
        """
        self.apps_dir = apps_dir
        self.registry_file = registry_file
        self.sync_interval_minutes = sync_interval_minutes
        self.use_transformer = use_transformer
        self.enable_embeddings = enable_embeddings
        self.enable_clustering = enable_clustering
        
        # Engines
        self.pii_engine = PIIShield()
        self.sentiment_engine = SentimentV3Engine(use_transformer=use_transformer)
        self.theme_engine = ThemingV3Engine() if enable_embeddings else None
        self.anomaly_engine = AnomalyAndDriftEngine()
        
        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_sync: Dict[str, datetime] = {}
        self._callbacks: List[Callable] = []
        
        logger.info(f"Initialized ReviewSyncScheduler with {sync_interval_minutes}min interval")
        logger.info(f"Transformer: {use_transformer}, Embeddings: {enable_embeddings}, Clustering: {enable_clustering}")
    
    def register_callback(self, callback: Callable):
        """Register a callback function to be called after each sync."""
        self._callbacks.append(callback)
    
    def _process_reviews_with_transformer(
        self, 
        df_raw: pd.DataFrame,
        app_id: str
    ) -> pd.DataFrame:
        """
        Process reviews with transformer sentiment + embeddings + clustering.
        
        This replaces the basic keyword-based processing with advanced ML pipeline:
        1. PII Redaction
        2. Transformer Sentiment (v3 with clause splitting)
        3. Dense Embeddings (384d MiniLM)
        4. DBSCAN Clustering
        5. c-TF-IDF Theme Labeling
        """
        if len(df_raw) == 0:
            return df_raw
        
        logger.info(f"[{app_id}] Processing {len(df_raw)} reviews with transformer pipeline...")
        start_time = time.time()
        
        processed = []
        
        # Step 1 & 2: PII Redaction + Transformer Sentiment
        for _, row in df_raw.iterrows():
            raw_text = str(row.get("review_text", ""))
            r_id = str(row.get("review_id", f"GPS-{int(time.time())}"))
            
            # PII Redaction
            redacted, _ = self.pii_engine.redact_text(raw_text, review_id=r_id)
            
            # Transformer Sentiment Analysis
            r_val = int(row.get("rating", 3))
            sent_out = self.sentiment_engine.analyze(redacted, rating=r_val, review_id=r_id)
            
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
        
        df_processed = pd.DataFrame(processed)
        
        # Step 3, 4, 5: Embeddings + Clustering + Theme Labeling
        if self.enable_clustering and self.theme_engine and len(df_processed) >= 3:
            logger.info(f"[{app_id}] Generating embeddings and clustering themes...")
            df_processed, theme_summaries = self.theme_engine.cluster_reviews(
                df_processed, 
                min_cluster_size=3
            )
        else:
            # Fallback: keyword-based themes (for small datasets)
            df_processed["theme_title"] = df_processed["review_text"].apply(
                self._classify_theme_by_keywords
            )
            df_processed["cluster_id"] = -1
        
        elapsed = time.time() - start_time
        logger.info(f"[{app_id}] Processed {len(df_processed)} reviews in {elapsed:.2f}s ({len(df_processed)/elapsed:.1f} reviews/sec)")
        
        return df_processed
    
    def _classify_theme_by_keywords(self, text: str) -> str:
        """Fallback keyword-based theme classification for small datasets."""
        t = text.lower()
        
        if any(k in t for k in ["crash", "freeze", "bug", "unusable", "stuck", "force close"]):
            return "App Stability & Launch Crashes"
        elif any(k in t for k in ["slow", "lag", "performance", "battery", "drain"]):
            return "Performance & Battery"
        elif any(k in t for k in ["login", "auth", "password", "account", "sign in"]):
            return "Authentication & Account"
        elif any(k in t for k in ["ad", "ads", "advertisement", "popup"]):
            return "Ads & Monetization"
        elif any(k in t for k in ["pay", "billing", "subscription", "charge", "refund"]):
            return "Billing & Subscriptions"
        elif any(k in t for k in ["ui", "design", "dark mode", "layout", "interface"]):
            return "UI/UX & Design"
        elif any(k in t for k in ["love", "great", "best", "amazing", "awesome", "excellent"]):
            return "General Praise & Feature Experience"
        else:
            return "Uncategorized / Emerging Issues"
    
    def _sync_app(self, app_info: Dict) -> Dict:
        """
        Sync a single app: fetch reviews, process with transformer, detect anomalies.
        
        Returns:
            Dict with sync results (old_count, new_count, message, alerts)
        """
        app_id = app_info.get("id")
        package_name = app_info.get("package_name")
        
        if not app_id or not package_name:
            return {"success": False, "message": "Invalid app info"}
        
        logger.info(f"[{app_id}] Starting sync for {package_name}...")
        
        try:
            # Fetch raw reviews
            raw_dfs = []
            
            # Try Developer API first (if configured)
            if GooglePlayConfig.is_configured():
                df_api, count, err = fetch_reviews_via_androidpublisher(
                    GooglePlayConfig.SERVICE_ACCOUNT_FILE,
                    package_name,
                    max_results=500  # Increased from 200 for better coverage
                )
                if count > 0:
                    raw_dfs.append(df_api)
                    logger.info(f"[{app_id}] Fetched {count} reviews from Developer API")
            
            # Also fetch from public scraper
            df_scraper, count_scraper = fetch_reviews(package_name, count=500, sort="newest")
            if count_scraper > 0:
                raw_dfs.append(df_scraper)
                logger.info(f"[{app_id}] Fetched {count_scraper} reviews from public scraper")
            
            if not raw_dfs:
                return {
                    "success": False,
                    "app_id": app_id,
                    "message": "No reviews fetched"
                }
            
            # Combine and deduplicate
            df_raw = pd.concat(raw_dfs, ignore_index=True)
            df_raw["_norm_txt"] = df_raw["review_text"].astype(str).str.strip().str.lower()
            df_raw = df_raw.drop_duplicates(subset=["_norm_txt"]).drop(columns=["_norm_txt"])
            
            # Load existing reviews
            app_dir = os.path.join(self.apps_dir, app_id)
            parquet_path = os.path.join(app_dir, "processed_reviews.parquet")
            old_count = 0
            
            if os.path.exists(parquet_path):
                try:
                    df_existing = pd.read_parquet(parquet_path)
                    old_count = len(df_existing)
                    
                    # Filter out reviews we already have
                    existing_ids = set(df_existing["review_id"].astype(str))
                    df_raw = df_raw[~df_raw["review_id"].astype(str).isin(existing_ids)]
                    
                    if len(df_raw) == 0:
                        logger.info(f"[{app_id}] No new reviews found")
                        return {
                            "success": True,
                            "app_id": app_id,
                            "old_count": old_count,
                            "new_count": old_count,
                            "added": 0,
                            "message": "No new reviews"
                        }
                except Exception as e:
                    logger.warning(f"[{app_id}] Error loading existing reviews: {e}")
            
            # Process with transformer pipeline
            df_new = self._process_reviews_with_transformer(df_raw, app_id)
            
            # Merge with existing
            if old_count > 0:
                df_all = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df_all = df_new
            
            # Save updated data
            os.makedirs(app_dir, exist_ok=True)
            df_all.to_parquet(parquet_path, index=False)
            
            new_count = len(df_all)
            added_count = len(df_new)
            
            # Detect anomalies on updated dataset
            alerts = []
            if len(df_all) >= 50:  # Need minimum data for anomaly detection
                try:
                    alerts = self.anomaly_engine.detect_emerging_spikes(
                        df_all,
                        window_hours=24,
                        baseline_days=7
                    )
                    if alerts:
                        logger.warning(f"[{app_id}] Detected {len(alerts)} spike alerts!")
                except Exception as e:
                    logger.error(f"[{app_id}] Error detecting anomalies: {e}")
            
            self._last_sync[app_id] = datetime.now()
            
            result = {
                "success": True,
                "app_id": app_id,
                "package_name": package_name,
                "old_count": old_count,
                "new_count": new_count,
                "added": added_count,
                "alerts": alerts,
                "message": f"Added {added_count} new reviews (total: {new_count})"
            }
            
            logger.info(f"[{app_id}] Sync complete: {result['message']}")
            
            # Trigger callbacks
            for callback in self._callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{app_id}] Sync failed: {e}", exc_info=True)
            return {
                "success": False,
                "app_id": app_id,
                "message": f"Error: {str(e)}"
            }
    
    def _sync_all_apps(self):
        """Sync all registered Google Play apps."""
        import json
        
        if not os.path.exists(self.registry_file):
            logger.warning("No app registry found")
            return
        
        with open(self.registry_file, "r", encoding="utf-8") as f:
            apps = json.load(f)
        
        # Filter to only Google Play apps
        gps_apps = [app for app in apps if app.get("source") == "google_play_store"]
        
        if not gps_apps:
            logger.info("No Google Play apps registered for syncing")
            return
        
        logger.info(f"Syncing {len(gps_apps)} Google Play apps...")
        
        for app in gps_apps:
            self._sync_app(app)
    
    def _run_loop(self):
        """Main background sync loop."""
        logger.info(f"Background sync loop started (interval: {self.sync_interval_minutes} minutes)")
        
        while self._running:
            try:
                logger.info("=" * 60)
                logger.info(f"Starting scheduled sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 60)
                
                self._sync_all_apps()
                
                logger.info(f"Sync complete. Next sync in {self.sync_interval_minutes} minutes")
                
                # Sleep in small chunks to allow clean shutdown
                sleep_seconds = self.sync_interval_minutes * 60
                elapsed = 0
                while elapsed < sleep_seconds and self._running:
                    time.sleep(1)
                    elapsed += 1
                    
            except Exception as e:
                logger.error(f"Error in sync loop: {e}", exc_info=True)
                time.sleep(60)  # Wait 1 minute before retrying on error
    
    def start(self):
        """Start the background scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        logger.info("✅ Background scheduler started")
    
    def stop(self):
        """Stop the background scheduler."""
        if not self._running:
            return
        
        logger.info("Stopping background scheduler...")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=10)
        
        logger.info("✅ Background scheduler stopped")
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
    
    def get_last_sync(self, app_id: str) -> Optional[datetime]:
        """Get last sync time for an app."""
        return self._last_sync.get(app_id)
    
    def force_sync_now(self, app_id: Optional[str] = None):
        """
        Force an immediate sync (outside regular schedule).
        
        Args:
            app_id: If provided, sync only this app. Otherwise sync all.
        """
        import json
        
        if not os.path.exists(self.registry_file):
            logger.warning("No app registry found")
            return None
        
        with open(self.registry_file, "r", encoding="utf-8") as f:
            apps = json.load(f)
        
        if app_id:
            app = next((a for a in apps if a["id"] == app_id), None)
            if not app:
                logger.error(f"App {app_id} not found")
                return None
            return self._sync_app(app)
        else:
            self._sync_all_apps()
            return {"success": True, "message": "All apps synced"}


# Global singleton instance
_scheduler_instance: Optional[ReviewSyncScheduler] = None


def get_scheduler(
    apps_dir: str,
    registry_file: str,
    sync_interval_minutes: int = 5,
    use_transformer: bool = True,
    enable_embeddings: bool = True,
) -> ReviewSyncScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = ReviewSyncScheduler(
            apps_dir=apps_dir,
            registry_file=registry_file,
            sync_interval_minutes=sync_interval_minutes,
            use_transformer=use_transformer,
            enable_embeddings=enable_embeddings,
        )
    
    return _scheduler_instance
