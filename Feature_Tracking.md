# Review Insight Engine — Feature Tracking

**Purpose**: Living checklist to track build progress against `Project_Requirements.md`. Update status inline as you go. Review before every demo rehearsal.

**Status legend**: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked/at risk · `[-]` cut (document why)

---

## Open Issues From PRD Review (resolve before/during build)

- [x] Decide validation-set source: Diagnosed and disclosed circularity of rating-derived labels. Built independent human labeling tool (`scripts/create_human_labels.py` + `scripts/validate_human_labels.py`) for non-circular ground truth.
- [x] Define FR-3.2 mixed-sentiment detection method: Contrastive conjunctions regex + polarity conflict detection. Validated with explicit precision (0.667), recall (0.444), F1 (0.533).
- [x] Confirm PII pipeline meets <90s NFR: Achieved 0.23s on 10k rows.
- [x] Pre-cache ALL theme summaries + morning brief at build time.
- [x] Define redaction audit log schema: `review_id`, `pii_type`, `original`, `redacted`, `timestamp`.
- [x] Clarify theme taxonomy vs clustering: Taxonomy-based regex classification + TF-IDF fallback + 'Uncategorized/Emerging' bucket.
- [x] Clarify PSI vs Z-Score division of labor: Global macro population shift (PSI) vs rapid local failure bursts (Z-score spike engine).

---

## M0 — Setup (0.5 day)

- [x] Repo initialized, project structure ready
- [x] Dataset downloaded (sealuzh/app_reviews academic Google Play corpus, 288,065 real reviews)
- [x] Dataset cleaned & curated: `data/reviews_10k.csv` (10,000 rows across 60 days, 4 versions, 2 platforms)
- [x] Independent validation-label source prepared: `data/validation_500.csv` (500 stratified ground-truth reviews)
- [x] Synthetic surge injection script written: `data/surge_injection.csv` (100 critical failure reviews)

## M1 — Core Pipeline (1 day)

### FR-1 Ingestion
- [x] FR-1.1 CSV upload accepts required columns (review_id, review_text, rating, date, platform, app_version)
- [x] FR-1.2 Data quality report & validation check implemented (`pipeline/ingest.py`)
- [x] FR-1.3 Batch processing simulates freshness over rolling 60-day window

### FR-2 Preprocessing & PII Redaction (Pillar P3)
- [x] FR-2.1 Near-duplicate deduplication
- [x] FR-2.2 Cleaning & length filtering
- [x] FR-2.3 Redaction: emails, phones, names, URLs — masks personal data in 0.38s
- [x] FR-2.4 Redaction runs BEFORE clustering/summarization (tested & verified)
- [x] Redaction audit log implemented (`data/pii_audit_log.json` tracking before/after pairs)
- [x] Timed test: full preprocessing stage on 10k rows completed in <0.5s

### FR-3 Sentiment Analysis (Pillar P2)
- [x] FR-3.1 Calibrated sentiment classification working end-to-end
- [x] FR-3.2 Mixed-sentiment flagging implemented (contrastive conjunction detector: "but", "however")
- [x] FR-3.3 Per-review confidence score stored

### FR-4 Theme Discovery & Summarization (Pillar P1)
- [x] Semantic theme taxonomy & feature space mapping implemented (`pipeline/clustering.py`)
- [x] Cluster quality check: 100% of reviews mapped to coherent product categories
- [x] FR-4.2 Auto-naming of themes from domain keywords & descriptions
- [x] FR-4.3 Each theme has: volume, negativity ratio, impact score, and representative verbatims
- [x] FR-4.4 Traceability invariant enforced in code (every theme card links to 3-5 real customer verbatims)


**M1 exit check**: terminal/JSON output shows themes with linked verbatims, sentiment, and confidence — before any UI work starts.

## M2 — Dashboard (1 day)

- [x] FR-5.1 KPI strip (total reviews, % negative, avg rating trend, active themes, open alerts)
- [x] FR-5.2 Theme cards sorted by impact score = normalized(volume) × negativity_ratio × recency_weight
- [x] FR-5.3 Filters: date range, rating, platform, version, sentiment
- [x] FR-5.4 Theme detail drawer / expandable quotes: title, volume, negativity, verbatims (P1 Traceability)
- [x] FR-5.5 Sentiment distribution + volume-by-category Plotly charts
- [x] Streamlit app running end-to-end on real pipeline output (`http://localhost:8501`)
- [x] Info tooltips on every computed score (impact, severity, drift) showing the formula — NFR: Explainability

## M3 — The Three Pillars (1 day)

### Validation Report (FR-7 / Pillar P2)
- [x] FR-7.1 Stratified labelled sample held out, n ≥ 500, balanced across classes (`data/validation_500.csv`)
- [x] FR-7.2 Real NLP performance honestly reported: Text-Only Accuracy 48.4%, Macro F1 0.482 (zero rating leakage)
- [x] FR-7.2 Rating-Assisted ceiling disclosed as near-tautological baseline (91.8% Acc, 0.886 F1)
- [x] FR-7.2 Mixed-sentiment detector independently reported (Precision: 0.667, Recall: 0.444, F1: 0.533)
- [x] FR-7.2 Interactive 3x3 Text-Only Confusion Matrix rendered in UI (Plotly heatmap)
- [x] FR-7.3 Documented rationale for 'Why NLP over Star Rating' in UI & reports
- [x] FR-7.4 Tooling for independent non-circular human ground truth (`data/human_labels_150.csv`) ready

### Drift Monitor (FR-8 / Pillar P3)
- [x] FR-8.1 Rolling 7-day sentiment distribution vs. historical baseline (interactive comparison chart)
- [x] FR-8.2 Population Stability Index (PSI = 0.0005) metric implemented and rendered
- [x] FR-8.3 New-theme emergence feed (detects novel themes appearing without historical baseline)
- [x] FR-8.4 Drift health indicator (HEALTHY / DRIFT DETECTED) on dashboard header

### Redaction Viewer (FR-2 / Pillar P3)
- [x] Before/after redaction live interactive test bench in UI
- [x] Audit log viewable & searchable in table (`data/pii_audit_log.json`, 473 entities captured)

## M4 — Killer Features (0.5 day)

### Emerging-Issue Alerts (FR-6)
- [x] FR-6.1 Last-24h/batch activity compared to 7-day rolling baseline
- [x] FR-6.2 Alert threshold logic (z-score > 2.5 or 2.5× velocity) implemented
- [x] FR-6.3 Alert card: theme, velocity multiplier (7.66x), % negative, sample verbatims, severity score
- [x] FR-6.4 Live Demo "⚡ Inject Surge" toggle button in sidebar fires the critical alert in real-time

### Morning Brief (FR-9)
- [x] FR-9.1 3–5 sentence executive auto-digest (overall movement, top themes, active alerts, model health)
- [x] FR-9.2 1-Click "Export Brief as Markdown" download button for leadership sharing

## Non-Functional Requirements Checklist

- [x] Performance: 10,000 reviews processed in 4.64s (<90s NFR target — EXCEEDED!)
- [x] Reproducibility: fixed seeds; pipeline runs as single deterministic script (`scripts/run_pipeline.py`)
- [x] Trust: every theme card has real customer verbatims one click away (P1 Traceability)
- [x] Privacy: PII masked before storage & clustering; full audit log maintained (P3 Privacy)
- [x] Explainability: Impact, Z-score, and PSI formulas displayed directly in UI
- [x] Automated Testing: 6-test suite (`tests/test_pillars.py`) passes in 0.22s, verifying all 3 pillars

## Scope Discipline & Explicit Cuts (Demo Day Freeze)

- [-] Drag-and-drop CSV upload: Cut from demo UI to maintain zero-crash reliability; pipeline function ready in `pipeline/ingest.py`.
- [-] FastAPI split: Kept as high-performance Streamlit monolith to eliminate network latency and multi-process risk.
- [-] Heavy PyTorch transformers: Cut in favor of deterministic fast lexicon (<5s runtime vs 3min CPU stall).
- [-] Jira / Linear live sync: Replaced with 1-click 'Copy Theme to Ticket' export.

## Judging-Criteria Self-Check (Demo Ready)

- [x] Can a stranger click a theme and see ≥3 real verbatims within one click? (P1) — YES!
- [x] Is there an honest validation report with non-circular ground truth? (P2) — YES! (68.7% Human / 48.4% Holdout / 91.8% Ceiling)
- [x] Is there a live before/after redaction example on screen? (P3) — YES!
- [x] Does the drift dashboard show a real distribution shift & PSI score? (P3) — YES!
- [x] Does the pitch demonstrate a live spike alert firing during the demo? (Killer Feature) — YES! (Z=19.67 surge)

---

## M5 — Mentor Roadmap & Credibility Upgrades (Completed)

- [x] **Trained Offline ML Sentiment Model**: TF-IDF + Logistic Regression trained on 10,000 weak rating labels (`scripts/train_weak_sentiment.py` -> `data/sentiment_model.joblib`).
- [x] **Comprehensive Baseline Benchmark on n=150 Human Ground Truth**:
  - Scored on identical 150 non-circular reviews: Majority Baseline (37.3%), NLTK VADER (60.0%), Lexicon Engine (68.7%), TF-IDF + Logistic Regression (66.0%).
  - Exact 95% Wilson Score Confidence Intervals computed for all models (`scripts/evaluate_sentiment_baselines.py` -> `data/sentiment_baselines_comparison.json`).
- [x] **Empirical Synthetic PII Evaluation Harness**:
  - Evaluated on 27 injected synthetic ground truth scenarios (`scripts/benchmark_pii.py` -> `data/pii_benchmark_metrics.json`).
  - Achieved 100% recall on emails, phone numbers, and URLs; calibrated claim clearly distinguishes empirical guarantees from best-effort NER.
- [x] **Founder Action Center**:
  - Implemented mentor Priority Score formula: `Volume Share × Severity Weight × (1 + WoW Growth) × Rating Drag` (`pipeline/founder_engine.py`).
  - Calculated Estimated Rating Lift: projects app store rating recovery when friction themes are resolved.
  - Release Regression Card: detects surges between Version N and N-1 (e.g. 4.1x crash surge in v3.4 vs v3.3).
  - 1-Click Ticket Hand-off: generates prefilled Markdown/Jira/Linear issues with 3 verified customer verbatims.
- [x] **Live Interactive Drift Simulator**:
  - In-app slider allowing judges to inject sentiment drift and visually watch PSI cross 0.10 (Watch) and 0.25 (Action).
  - Documented regulatory risk justification for why 0.10 and 0.25 are standard thresholds.
- [x] **10,000 Review Scale Verification**:
  - End-to-end benchmark on 10,000 reviews completed in 5.77 seconds (1,732 reviews/sec), beating the 90s budget by 84.2s (`scripts/benchmark_10k_scale.py` -> `data/scale_benchmark_metrics.json`).
  - 1-Click Sample Dataset button added to sidebar for instant evaluation.
- [x] **Innovation & Differentiators**:
  - Interactive What-If Simulator: dynamic slider allowing founders to simulate sprint resolution and see projected rating lift.
  - Transparent Failure Cases post-mortem analysis (sarcasm, slang, truncation).
  - 3-Minute Demo Pitch Guide & Judge Defense Q&A with prepared answers to all 7 critical questions.
- [x] **Automated Regression Suite**:
  - Expanded unittest suite (`tests/test_pillars.py`) to 9 passing tests covering all pillars, priority formulas, PII benchmarks, and confidence intervals.


