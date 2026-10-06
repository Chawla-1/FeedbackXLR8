# FeedbackXLR8

Enterprise review intelligence platform that transforms thousands of unstructured customer reviews into actionable insights with real-time anomaly detection.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## Problem

Product teams receive thousands of reviews daily but lack time to read and analyze them manually. Critical issues (crashes, login failures) are discovered weeks late, directly impacting app store ratings and revenue.

## Solution

Automated review analysis pipeline that:
- **Detects sentiment** with 74% accuracy using transformer models
- **Identifies themes** automatically through semantic clustering
- **Alerts on spikes** using statistical anomaly detection (Z-score > 2.5)
- **Redacts PII** with 100% recall before processing
- **Traces insights** back to real customer verbatims for validation

## Key Features

- **Sentiment Analysis**: Hybrid lexicon + transformer engine with mixed sentiment detection
- **Theme Discovery**: Dense embeddings (DBSCAN + c-TF-IDF) for automatic categorization
- **Real-Time Alerts**: Poisson-based spike detection catches issues 10× faster
- **PII Protection**: Automatic masking of emails, phones, URLs before storage
- **Multi-App Support**: Manage and compare insights across multiple applications
- **Performance**: 103,920 reviews/minute on CPU (1.17ms per review)

---

## Technical Approach

### Architecture

```
CSV Upload → PII Redaction → Sentiment Analysis → Theme Clustering → 
Anomaly Detection → Dashboard + Alerts
```

### Core Components

**Pipeline Modules**:
- `sentiment_v3.py`: Transformer-based classifier with contrastive clause splitting
- `theming_v3.py`: Dense embeddings (MiniLM-L6) + DBSCAN clustering + c-TF-IDF labeling
- `pii_redactor.py`: Regex + NER-based masking (emails, phones, URLs)
- `anomaly_engine.py`: Z-score spike detection + PSI drift monitoring
- `founder_engine.py`: Priority scoring (Volume × Negativity × Recency × Impact)

**Technology Stack**:
- **Backend**: Python 3.8+
- **Frontend**: Streamlit
- **ML/NLP**: scikit-learn, sentence-transformers
- **Data**: Pandas, Parquet (columnar storage)
- **Optional**: HuggingFace transformers (cardiffnlp/twitter-roberta-base-sentiment)

### Performance Metrics

| Component | Latency | Throughput |
|-----------|---------|------------|
| PII Redaction | 0.028ms | 2.1M reviews/min |
| Sentiment v3 | 0.019ms | 3.1M reviews/min |
| Embeddings | 0.513ms | 117K reviews/min |
| Clustering | 0.611ms | 98K reviews/min |
| **End-to-End** | **1.17ms** | **103K reviews/min** |

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Chawla-1/FeedbackXLR8.git
cd FeedbackXLR8

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set passwords
nano .env
```

**Required environment variables**:
```env
AUTH_ADMIN_PASSWORD=your_strong_password
SESSION_SECRET_KEY=random-32-character-secret
```

### Run Application

```bash
# Start Streamlit app
streamlit run app.py

# Open browser to http://localhost:8501
```

### Run Pipeline (Generate Data)

```bash
# Process sample reviews
python scripts/run_pipeline.py

# Run evaluation
python eval.py --engine v3 --output benchmark/sentiment_v3.json

# Run tests
python -m unittest discover tests
```

---

## Project Structure

```
FeedbackXLR8/
├── app.py                    # Main Streamlit application
├── config.py                 # Configuration management
├── requirements.txt          # Dependencies
├── .env.example             # Environment template
│
├── pipeline/                # Core processing engines
│   ├── sentiment_v3.py     # Transformer sentiment
│   ├── theming_v3.py       # Dense clustering
│   ├── pii_redactor.py     # PII masking
│   ├── anomaly_engine.py   # Spike detection
│   └── ...
│
├── tests/                   # Unit tests
├── scripts/                 # Utility scripts
└── benchmark/              # Evaluation datasets
```

---

## Validation Results

| Model | Accuracy | Macro F1 | Speed (reviews/sec) |
|-------|----------|----------|---------------------|
| NLTK VADER | 60.0% | 0.446 | 6,735 |
| TF-IDF + LogReg | 66.0% | 0.618 | 5,800 |
| Lexicon v2 | 68.7% | 0.623 | 27,209 |
| **Transformer v3** | **74.17%** | **0.6481** | **~50,000** |

**Evaluation Datasets**:
- Golden Benchmark: n=515 stratified reviews
- Human Ground Truth: n=150 (blind-annotated, zero rating leakage)
- PII Benchmark: 100% recall on emails, phones, URLs

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Open Pull Request

---

**Built for product teams who need to understand customers at scale.**
