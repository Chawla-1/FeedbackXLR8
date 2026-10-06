# FeedbackXLR8 — Upgrade Checklist v2.0 → v3.0

**Goal:** Replace regex/tokenizer core with verifiable transformer models, keep P1 (traceability) and P3 (PII) pillars intact, and have hard evaluation numbers for the judges.
**Rule:** Do NOT delete existing modules until the new one beats it on the benchmark. Old engine = fallback for the live demo.

---

## Phase 0 — Freeze & Baseline (Completed)

- [x] **0.1 Freeze current code.** Tagged working version (`git tag v2.0-baseline`). Live demo is preserved as fallback.
- [x] **0.2 Build the golden benchmark set.** Collected **515 real reviews** (`benchmark/golden.csv`) stratified across all rating bands (1★–5★), sentiments, and themes.
- [x] **0.3 Score the CURRENT engine on the golden set.** Scored v2 baseline: Accuracy 52.43%, Macro F1 0.5016, Negative F1 0.4610 → saved to `benchmark/baseline_v2.json`.
- [x] **0.4 Write the evaluation script once** (`eval.py`) supporting any engine (`--engine v2` or `--engine v3`), computing 95% Wilson CIs and 4x4 confusion matrix.

✅ **Phase 0 exit:** `benchmark/baseline_v2.json` exists, `eval.py` runs clean, old demo still works.

---

## Phase 1 — Sentiment Engine Upgrade (`pipeline/sentiment_v3.py`)

- [x] **1.1 Candidate model selected:** `cardiffnlp/twitter-roberta-base-sentiment-latest` + fast offline ML fallback (`data/sentiment_model.joblib`).
- [x] **1.2 Implemented `pipeline/sentiment_v3.py`:** Transformer + offline calibrated pipeline with label and confidence output per review.
- [x] **1.3 Mixed-sentiment clause splitter:** Splits reviews on `but / however / though / although / yet / phir bhi / lekin` → evaluates each clause and outputs `mixed` when polarity conflicts.
  - [x] Unit tests: 4 test suites in `tests/test_sentiment_v3.py` verify contrastive clauses and Hinglish splitting.
- [x] **1.4 Rating-assisted calibration layer:** Model confidence < 0.70 checks star rating for tiebreak; model/rating conflicts flag `mixed`.
- [x] **1.5 Run `eval.py` on golden set:** Engine v3 achieved **74.17% Accuracy (+21.74%)** and **0.6481 Macro F1 (+14.65 pts)**, beating the $\ge 5$ point benchmark threshold!
- [x] **1.6 Cache:** Stores model outputs in memory and serialized JSON so inference runs in milliseconds.

✅ **Exit:** `benchmark/sentiment_v3.json` shows $+14.65$ pt F1 improvement; clause-splitter tests pass.

---

## Phase 2 — Theme Clustering (`pipeline/theming_v3.py`)

- [x] **2.1 Dense embedding model:** `all-MiniLM-L6-v2` dense 384-dimensional semantic embeddings with caching.
- [x] **2.2 Cosine distance clustering:** DBSCAN on normalized cosine vectors. Unmatched reviews routed to "Uncategorized / Emerging Issues".
- [x] **2.3 c-TF-IDF cluster labeling:** Class-based TF-IDF extracts top terms without hallucinating LLMs.
- [x] **2.4 Map clusters to severity weights:** Maps clusters to severity classes (crashes: 3.0x, auth: 2.5x, etc.).
- [x] **2.5 P1 traceability check:** Enforces $\ge 3$ receipts (`review_id`, version, stars, verbatim quote) per cluster.
- [x] **2.6 Paraphrase similarity recall:** `tests/test_theming_v3.py` proves crash paraphrases share $> 0.65$ cosine similarity and land in the same cluster.
- [x] **2.7 Drift bonus:** Theme distributions feed directly into the Population Stability Index (PSI).

✅ **Exit:** Paraphrase test passes; every cluster has receipts; theme purity $\ge$ baseline.

---

## Phase 3 — PII Shield Hardening (`pipeline/pii_redactor.py`)

- [x] **3.1 PII Masking Engine:** High-speed regex + contextual entity masks for `[EMAIL_REDACTED]`, `[PHONE_REDACTED]`, and `[URL_REDACTED]`.
- [x] **3.2 Edge-case test set:** Multi-entity combinations, WhatsApp numbers, formatted international phone numbers, and negative controls.
- [x] **3.3 Measured recall evidence:** Injected synthetic ground truth ($n=27$ scenarios) achieves **100% Recall on emails and phones**; names calibrated as best-effort.
- [x] **3.4 Audit log:** Append-only log maintained in `data/pii_audit_log.json` and exported to `benchmark/pii_v3.json`.

✅ **Exit:** PII recall table in `benchmark/pii_v3.json`; audit log format preserved.

---

## Phase 4 — LLM & Grounded Assistant

- [x] **4.1 Grounded naming:** c-TF-IDF provides explainable cluster naming without black-box hallucination.
- [x] **4.2 Ordering rule enforced:** PII redaction runs strictly *before* clustering or summarization.
- [x] **4.3 P1 Invariant:** All assistant responses cite ground truth review receipts (`review_id`).
- [x] **4.4 Offline ready:** Full dashboard and copilot function with zero network dependency.

✅ **Exit:** Grounded review assistant cites receipts without unconstrained LLM risk.

---

## Phase 5 — Regression & Test Suite

- [x] **5.1 14 existing unittests preserved:** Kept 100% green (`tests/test_pillars.py`, `tests/test_founder_engine.py`).
- [x] **5.2 New unit tests added:**
  - [x] Clause splitter cases (English + Hinglish `phir bhi`) → `tests/test_sentiment_v3.py`
  - [x] Paraphrase clustering similarity → `tests/test_theming_v3.py`
  - [x] Every-cluster-has-$\ge 3$-receipts invariant → `tests/test_theming_v3.py`
  - [x] Synthetic PII precision & recall → `scripts/benchmark_pii.py`
  - [x] Star rating calibration conflict cases → `tests/test_sentiment_v3.py`
- [x] **5.3 Automated regression suite:** All **20 unit tests pass (100% OK)** in under 22 seconds (`python -m unittest discover tests`).

---

## Phase 6 — Demo Hardening (Judge-Proofing)

- [x] **6.1 Offline demo mode:** Full dashboard and portfolio run from local Parquet storage with zero network calls required.
- [x] **6.2 Pre-loaded apps + Live App:** CloudSync Pro, PayFlow Wallet, HealthTrack, EduLearn Plus + live Google Play app (`com.xvoid.vault`).
- [x] **6.3 Seeded anomaly:** Live "⚡ Inject Surge" toggle button fires the critical Poisson $Z=19.67$ alert in real time on cue.
- [x] **6.4 Live hand-off:** 1-Click pre-filled Markdown tickets ready to copy/download for GitHub, Linear, and Jira.
- [x] **6.5 Praise vs Bug differentiation:** Feature wins are rendered with green cards (`#107c41`) and customer delight retention tickets.
- [x] **6.6 Clean logs:** Deprecation warnings and terminal encoding issues resolved.

---

## Phase 7 — Report & Pitch Updates

- [x] **7.1 Versioning:** Production Release v2.0 (with Engine v3.0 Golden Benchmark).
- [x] **7.2 Clean formatting:** Markdown tables with verified empirical metrics.
- [x] **7.3 Evaluation section on UI:** Live Golden Benchmark comparison card on Page 5 with 4x4 confusion matrix and transparent failure cases (Sarcasm, Slang, Brevity).
- [x] **7.4 Speed proof:** 10,000 reviews benchmarked in **5.77s** (1,732 reviews/sec), beating the 90s budget by 84.2s.
- [x] **7.5 Live API proof:** Real Google Play Developer API integration demonstrated on `com.xvoid.vault` with Service Account.
- [x] **7.6 Answers to hard judge questions prepared:** Non-circular ground truth, PSI vs Z-score complementarity, and PII recall guarantees.
