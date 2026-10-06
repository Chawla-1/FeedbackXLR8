# 📊 FeedbackXLR8

**Enterprise-Grade Multi-App Review Intelligence Platform**

Transform thousands of unstructured customer reviews into prioritized, traceable, and validated actionable insights with real-time anomaly detection.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)

---

## 🎯 **Key Features**

### **🔍 Smart Review Analysis**
- **Sentiment Analysis**: 74.17% accuracy with transformer-based engine + lexicon fallback
- **Theme Discovery**: Automatic clustering with dense embeddings (DBSCAN + c-TF-IDF)
- **Mixed Sentiment Detection**: Handles contrastive phrases ("Great UI BUT crashes")
- **Multilingual Support**: English + Hinglish code-switching (90% accuracy)

### **⚡ Real-Time Alerts**
- **Poisson-Based Spike Detection**: Z-score > 2.5 threshold
- **Live Anomaly Monitoring**: Catches critical issues 10× faster
- **Severity Scoring**: Volume × Negativity × Velocity × Severity Weight

### **🛡️ Enterprise Trust Pillars**
1. **Traceability (P1)**: Every insight links to ≥3 real customer verbatims
2. **Validated Accuracy (P2)**: Multi-tier validation with honest metrics
3. **Privacy + Drift (P3)**: PII redaction (100% recall) + PSI drift monitoring

### **🚀 Performance**
- **103,920 reviews/minute** (1,732 reviews/second) on CPU
- **1.17ms latency** per review end-to-end
- **10K reviews in 5.77 seconds** (beats 90s benchmark by 84.2s)

---

## 📦 **Quick Start**

### **Prerequisites**
- Python 3.8 or higher
- pip package manager

### **Installation**

```bash
# Clone the repository
git clone https://github.com/yourusername/feedbackxlr8.git
cd feedbackxlr8

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your credentials (IMPORTANT!)
# nano .env  # or use your preferred editor
```

### **Configuration**

Edit `.env` file and update these **critical** values:

```env
# Change these passwords immediately!
AUTH_ADMIN_PASSWORD=your_strong_password_here
AUTH_DEMO_PASSWORD=your_demo_password_here
AUTH_FOUNDER_PASSWORD=your_founder_password_here

# Generate a random secret key
SESSION_SECRET_KEY=your-random-32-char-secret-key

# Optional: Google Play API (if syncing live reviews)
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/service-account.json
GOOGLE_PLAY_PACKAGE_NAME=com.your.app
```

### **Run the Application**

```bash
# Development mode
streamlit run app.py

# Production mode (with environment)
APP_ENV=production streamlit run app.py --server.port 8501
```

Open your browser to **http://localhost:8501**

---

## 🏗️ **Project Structure**

```
feedbackxlr8/
├── app.py                      # Main Streamlit application
├── config.py                   # Centralized configuration
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
│
├── pipeline/                   # Core processing engines
│   ├── ingest.py              # CSV validation & ingestion
│   ├── pii_redactor.py        # PII masking (100% recall)
│   ├── sentiment.py           # v2 Lexicon engine
│   ├── sentiment_v3.py        # v3 Transformer + clause splitter
│   ├── clustering.py          # v2 TF-IDF themes
│   ├── theming_v3.py          # v3 Dense embeddings + DBSCAN
│   ├── anomaly_engine.py      # Z-score spike + PSI drift
│   ├── founder_engine.py      # Priority scoring + regressions
│   ├── playstore_fetcher.py   # Google Play API integration
│   └── validator.py           # Validation harness
│
├── scripts/                    # Utilities & benchmarks
│   ├── run_pipeline.py        # End-to-end pipeline
│   ├── benchmark_10k_scale.py # Performance test
│   ├── benchmark_pii.py       # PII recall test
│   ├── evaluate_sentiment_baselines.py
│   └── ...
│
├── tests/                      # Automated test suite
│   ├── test_pillars.py        # P1/P2/P3 validation
│   ├── test_founder_engine.py
│   ├── test_sentiment_v3.py
│   └── test_theming_v3.py
│
├── data/                       # Processed data (not in git)
│   ├── apps/                  # Per-app storage
│   │   └── registry.json      # App portfolio manifest
│   └── ...
│
├── benchmark/                  # Evaluation datasets
│   ├── golden.csv             # n=515 benchmark
│   ├── baseline_v2.json       # v2 results
│   └── sentiment_v3.json      # v3 results
│
└── docs/                       # Documentation
    ├── DEMO_SCRIPT.md         # Presentation guide
    └── SLIDE_DECK.md          # Pitch deck
```

---

## 🔧 **Configuration Options**

### **Authentication**
```env
# Enable/disable login gate
ENABLE_LOGIN=true

# Configure user accounts
AUTH_ADMIN_EMAIL=admin@yourcompany.com
AUTH_ADMIN_PASSWORD=strong_password_123
```

### **Feature Flags**
```env
# Google Play Store integration
ENABLE_GOOGLE_PLAY_SYNC=false

# Live surge simulation (demo feature)
ENABLE_SURGE_SIMULATION=true
```

### **Model Configuration**
```env
# Sentiment engine: v2 (lexicon, fast) or v3 (transformer, accurate)
SENTIMENT_ENGINE=v3
SENTIMENT_MODEL=cardiffnlp/twitter-roberta-base-sentiment-latest
USE_TRANSFORMER=true

# Theme clustering
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### **Performance Tuning**
```env
# Batch size for processing
MAX_BATCH_SIZE=10000

# Enable caching
ENABLE_CACHE=true
CACHE_TTL_SECONDS=3600
```

### **Alerting Thresholds**
```env
# Z-score threshold for spike alerts
ALERT_Z_SCORE_THRESHOLD=2.5

# PSI drift thresholds
DRIFT_WARNING_THRESHOLD=0.10
DRIFT_CRITICAL_THRESHOLD=0.25
```

---

## 📊 **Evaluation & Benchmarks**

### **Run Evaluation Harness**

```bash
# Evaluate v2 baseline
python eval.py --engine v2 --output benchmark/baseline_v2.json

# Evaluate v3 transformer
python eval.py --engine v3 --output benchmark/sentiment_v3.json

# Run PII benchmark
python scripts/benchmark_pii.py

# Run 10K scale test
python scripts/benchmark_10k_scale.py
```

### **Run Test Suite**

```bash
# Run all tests
python -m unittest discover tests

# Run specific test
python -m unittest tests.test_pillars
```

---

## 🧪 **Validation Results**

| **Model** | **Accuracy** | **Macro F1** | **Speed** |
|-----------|-------------|-------------|-----------|
| Majority Baseline | 37.3% | 0.136 | ∞ |
| NLTK VADER | 60.0% | 0.446 | 6,735 rev/sec |
| TF-IDF + LogReg | 66.0% | 0.618 | 5,800 rev/sec |
| **Lexicon v2** | **68.7%** | **0.623** | **27,209 rev/sec** |
| **Transformer v3** | **74.17%** | **0.6481** | **~50K rev/sec** |

**Human Ground Truth (n=150)**: 68.7% accuracy  
**Golden Benchmark (n=515)**: 74.17% accuracy  
**PII Redaction**: 100% recall (emails, phones)

---

## 🔒 **Security & Privacy**

### **PII Redaction**
- Emails, phone numbers, URLs masked **before** storage
- 100% empirical recall on synthetic benchmarks
- Append-only audit log for compliance

### **Authentication**
- Session-based login system
- Environment-based credential management
- NEVER commit passwords to git

### **Data Isolation**
- Per-app data storage in `data/apps/{app_id}/`
- No data mixing between applications
- Local processing (no external API calls for core functions)

---

## 🚀 **Deployment**

### **Production Checklist**

- [ ] Update `.env` with strong passwords
- [ ] Set `APP_ENV=production`
- [ ] Configure logging: `LOG_LEVEL=WARNING`
- [ ] Review `ENABLE_SURGE_SIMULATION=false` (disable demo features)
- [ ] Set up HTTPS/SSL (use reverse proxy like nginx)
- [ ] Configure firewall rules
- [ ] Set up monitoring (logs in `logs/feedbackxlr8.log`)
- [ ] Backup `data/` directory regularly

### **Docker Deployment** (Optional)

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
# Build and run
docker build -t feedbackxlr8 .
docker run -p 8501:8501 --env-file .env feedbackxlr8
```

---

## 📚 **Documentation**

- **[Demo Script](docs/DEMO_SCRIPT.md)**: 3-minute pitch guide
- **[Platform Spec](PLATFORM_SPEC.md)**: Architecture & design decisions
- **[Feature Tracking](Feature_Tracking.md)**: Completed milestones
- **[Upgrade Checklist](feedbackxlr8-upgrade-checklist.md)**: v2 → v3 migration

---

## 🤝 **Contributing**

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### **Development Setup**

```bash
# Install dev dependencies
pip install -r requirements-dev.txt  # if exists

# Run tests before committing
python -m unittest discover tests

# Check code style
flake8 pipeline/ tests/
```

---

## 📝 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **Dataset**: [sealuzh/app_reviews](https://github.com/sealuzh/user_quality) (288,065 real Google Play reviews)
- **Models**: 
  - [cardiffnlp/twitter-roberta-base-sentiment](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest)
  - [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- **Inspiration**: Hackathon Challenge #17 - "10,000 Reviews, No Time to Read Them"

---

## 📧 **Contact & Support**

- **Issues**: [GitHub Issues](https://github.com/yourusername/feedbackxlr8/issues)
- **Email**: support@feedbackxlr8.io (update with your email)
- **Demo**: [Live Demo](https://feedbackxlr8-demo.streamlit.app) (if deployed)

---

## 🎯 **Roadmap**

- [ ] FastAPI backend separation
- [ ] Real-time streaming ingestion
- [ ] Advanced aspect-based sentiment
- [ ] Multi-source integration (support tickets, surveys)
- [ ] Theme lifecycle tracking (ROI measurement)
- [ ] DeBERTa-v3 model upgrade (+5-10% accuracy)
- [ ] Elasticsearch integration for large-scale search

---

**Built with ❤️ for product teams who need to understand their customers at scale**

⭐ Star this repo if you find it useful!
