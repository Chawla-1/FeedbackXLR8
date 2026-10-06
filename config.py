"""
FeedbackXLR8 Configuration Module
Loads environment variables and provides centralized config access.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
APPS_DIR = BASE_DIR / os.getenv("APPS_DIR", "data/apps")
BENCHMARK_DIR = BASE_DIR / os.getenv("BENCHMARK_DIR", "benchmark")

# ============================================
# Authentication Configuration
# ============================================
class AuthConfig:
    """Authentication settings"""
    ENABLED = os.getenv("ENABLE_LOGIN", "true").lower() == "true"
    SESSION_SECRET = os.getenv("SESSION_SECRET_KEY", "dev-secret-change-in-production")
    
    # Default demo accounts (override via environment)
    ACCOUNTS = {
        os.getenv("AUTH_ADMIN_EMAIL", "admin@feedbackxlr8.io"): {
            "password": os.getenv("AUTH_ADMIN_PASSWORD", "feedbackxlr8"),
            "name": os.getenv("AUTH_ADMIN_NAME", "Admin User"),
            "role": os.getenv("AUTH_ADMIN_ROLE", "Admin")
        },
        os.getenv("AUTH_DEMO_EMAIL", "demo@feedbackxlr8.io"): {
            "password": os.getenv("AUTH_DEMO_PASSWORD", "demo1234"),
            "name": os.getenv("AUTH_DEMO_NAME", "Demo Analyst"),
            "role": os.getenv("AUTH_DEMO_ROLE", "Analyst")
        },
        os.getenv("AUTH_FOUNDER_EMAIL", "founder@company.io"): {
            "password": os.getenv("AUTH_FOUNDER_PASSWORD", "founder2026"),
            "name": os.getenv("AUTH_FOUNDER_NAME", "Founder"),
            "role": os.getenv("AUTH_FOUNDER_ROLE", "Founder")
        }
    }

# ============================================
# Application Configuration
# ============================================
class AppConfig:
    """General application settings"""
    NAME = os.getenv("APP_NAME", "FeedbackXLR8")
    ENV = os.getenv("APP_ENV", "development")
    IS_PRODUCTION = ENV == "production"
    
    # Feature flags
    ENABLE_GOOGLE_PLAY_SYNC = os.getenv("ENABLE_GOOGLE_PLAY_SYNC", "false").lower() == "true"
    ENABLE_SURGE_SIMULATION = os.getenv("ENABLE_SURGE_SIMULATION", "true").lower() == "true"

# ============================================
# Google Play API Configuration
# ============================================
class GooglePlayConfig:
    """Google Play Store API settings"""
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    PACKAGE_NAME = os.getenv("GOOGLE_PLAY_PACKAGE_NAME", "")
    
    @classmethod
    def is_configured(cls):
        """Check if Google Play API is properly configured"""
        return bool(cls.SERVICE_ACCOUNT_FILE and 
                   os.path.exists(cls.SERVICE_ACCOUNT_FILE) and
                   cls.PACKAGE_NAME)

# ============================================
# Model Configuration
# ============================================
class ModelConfig:
    """ML/NLP model settings"""
    # Sentiment
    SENTIMENT_ENGINE = os.getenv("SENTIMENT_ENGINE", "v3")
    SENTIMENT_MODEL = os.getenv("SENTIMENT_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest")
    USE_TRANSFORMER = os.getenv("USE_TRANSFORMER", "true").lower() == "true"
    
    # Theme clustering
    THEME_ENGINE = os.getenv("THEME_ENGINE", "v3")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ============================================
# Performance Configuration
# ============================================
class PerformanceConfig:
    """Performance and caching settings"""
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "10000"))
    ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

# ============================================
# Alerting Configuration
# ============================================
class AlertConfig:
    """Anomaly detection and alerting thresholds"""
    Z_SCORE_THRESHOLD = float(os.getenv("ALERT_Z_SCORE_THRESHOLD", "2.5"))
    DRIFT_WARNING_THRESHOLD = float(os.getenv("DRIFT_WARNING_THRESHOLD", "0.10"))
    DRIFT_CRITICAL_THRESHOLD = float(os.getenv("DRIFT_CRITICAL_THRESHOLD", "0.25"))

# ============================================
# Logging Configuration
# ============================================
class LogConfig:
    """Logging settings"""
    LEVEL = os.getenv("LOG_LEVEL", "INFO")
    FILE = os.getenv("LOG_FILE", "logs/feedbackxlr8.log")
    
    @classmethod
    def setup(cls):
        """Initialize logging configuration"""
        import logging
        
        # Create logs directory if not exists
        log_dir = Path(cls.FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, cls.LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(cls.FILE),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger("FeedbackXLR8")

# ============================================
# Helper Functions
# ============================================
def get_data_path(filename: str) -> Path:
    """Get full path to data file"""
    return DATA_DIR / filename

def get_app_data_path(app_id: str, filename: str = None) -> Path:
    """Get path to app-specific data"""
    path = APPS_DIR / app_id
    return path / filename if filename else path

def ensure_directories():
    """Create necessary directories if they don't exist"""
    for directory in [DATA_DIR, APPS_DIR, BENCHMARK_DIR, Path("logs")]:
        directory.mkdir(parents=True, exist_ok=True)

# Initialize directories on import
ensure_directories()
