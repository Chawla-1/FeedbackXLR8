# FeedbackXLR8 — Engine Upgrade Checklist (v2.0 → v3.0)

**Release Target:** FeedbackXLR8 v3.0 (Transformer Sentiment, Dense Theming & Golden Benchmark)  
**Verified Baseline Fallback:** FeedbackXLR8 v2.0 Baseline (`git tag v2.0-baseline`)  
**Core Invariant:** Keep P1 (Traceability Receipts) and P3 (Zero-Leakage PII) intact. The old v2 engine remains functional as a live demo fallback.

---

## Performance & Throughput Overview (CPU-Only)

Measured on standard single-node consumer CPU hardware with zero GPU and zero network dependencies:
- **Sustained Throughput:** **103,920 reviews/minute (1,732 reviews/second)**
- **End-to-End Latency:** **~1.17 ms per review** (10,000 reviews benchmarked in 5.77s)
- **Per-Stage Latency Breakdown:**
  - PII Masking: **0.028 ms** (~2.1M reviews/min)
  - Sentiment v3 Inference: **0.019 ms** (~3.1M reviews/min)
  - 384d Dense Embeddings (batched MiniLM): **0.513 ms** (~117,000 reviews/min)
  - Theme Clustering & Priority Scoring: **0.611 ms** (~98,000 reviews/min)
- **Economic Advantage:** Cloud LLMs process ~50 reviews/min at $15–$150 per 10k reviews with 1–3s latency. FeedbackXLR8 executes at **>100,000 reviews/min locally at $0.00 cost**.

---

## Phase 0 — Freeze & Baseline (Completed)

- [x] **0.1 Freeze current code:** Tagged working version (`git tag v2.0-baseline`). Live demo is permanently preserved as a reliable fallback.
- [x] **0.2 Build the golden benchmark set:** Curated **515 real reviews** (`benchmark/golden.csv`) stratified across all rating bands (1★ to 5★), sentiments, and themes.
- [x] **0.3 Score the CURRENT engine on the golden set:** Scored v2 baseline: Accuracy 52.43%, Macro F1 0.5016, Negative F1 0.4610 -> saved to `benchmark/baseline_v2.json`.
- [x] **0.4 Evaluation harness:** Built unified evaluation harness (`eval.py`) supporting any engine (`--engine v2` or `--engine v3`), computing 95% Wilson confidence intervals and 4x4 confusion matrices.

Exit Criteria: `benchmark/baseline_v2.json` exists, `eval.py` runs cleanly, v2 baseline preserved.

---

## Phase 1 — Sentiment Engine Upgrade (`pipeline/sentiment_v3.py`)

- [x] **1.1 Model selection:** Selected `cardiffnlp/twitter-roberta-base-sentiment-latest` + high-speed calibrated offline fallback (`data/sentiment_model.joblib`).
- [x] **1.2 Pipeline implementation:** Implemented `pipeline/sentiment_v3.py` with confidence scores and normalized label outputs per review.
- [x] **1.3 Contrastive clause splitter:** Splits reviews on contrast markers (`but`, `however`, `though`, `although`, `yet`, `phir bhi`, `lekin`, `magar`, `par`) -> evaluates clauses separately and assigns `mixed` when polarities conflict.
- [x] **1.4 Rating-assisted calibration layer:** When model confidence is below 0.70, utilizes star rating for tiebreak; explicit text/rating conflicts are flagged as `mixed`.
- [x] **1.5 Golden set evaluation:** Engine v3 achieved **74.17% Accuracy (+21.74%)** and **0.6481 Macro F1 (+14.65 pts)**, beating the >= 5.0 point improvement requirement.
- [x] **1.6 Multilingual Hinglish benchmark:** Validated on 20 code-switched Hindi-English reviews (`scripts/benchmark_multilingual.py` -> `benchmark/multilingual_v3.json`): **90.0% overall accuracy, 80.0% mixed recall, 100% precision, 0.8889 F1**.
- [x] **1.7 Inference caching:** In-memory LRU and serialized caches ensure inference executes in milliseconds.

Exit Criteria: `benchmark/sentiment_v3.json` shows +14.65 pt F1 gain; clause-splitter unit tests pass.

---

## Phase 2 — Theme Clustering (`pipeline/theming_v3.py`)

- [x] **2.1 Dense embedding model:** Integrated `all-MiniLM-L6-v2` dense 384-dimensional semantic embeddings with local tensor caching.
- [x] **2.2 Cosine distance clustering:** DBSCAN on normalized cosine vectors. Novel or outlier reviews are routed to "Uncategorized / Emerging Issues".
- [x] **2.3 c-TF-IDF cluster labeling:** Class-based TF-IDF extracts explainable top keywords without hallucinating generative LLMs.
- [x] **2.4 Severity weighting:** Clusters mapped to severity multipliers (crashes: 3.0x, auth/billing: 2.5x, UI: 1.0x).
- [x] **2.5 P1 traceability invariant:** Every cluster strictly enforces >= 3 receipts (`review_id`, version, star rating, verbatim quote).
- [x] **2.6 Paraphrase similarity recall:** `tests/test_theming_v3.py` verifies crash paraphrases share > 0.65 cosine similarity and map to the same cluster.
- [x] **2.7 Drift tracking:** Theme distributions feed directly into the Population Stability Index (PSI = 0.0088).

Exit Criteria: Paraphrase unit tests pass; every theme cluster provides >= 3 verbatim receipts; theme purity >= baseline.

---

## Phase 3 — PII Shield Hardening (`pipeline/pii_redactor.py`)

- [x] **3.1 PII Masking Engine:** High-speed regex and contextual entity boundary masks for `[EMAIL_REDACTED]`, `[PHONE_REDACTED]`, and `[URL_REDACTED]`.
- [x] **3.2 Edge-case test set:** Multi-entity strings, international formats, WhatsApp numbers, and negative controls.
- [x] **3.3 Measured recall evidence:** 27 synthetic edge cases (`benchmark/pii_v3.json`) achieve **100% Recall on emails and phone numbers**; names masked via high-precision prefix heuristics.
- [x] **3.4 Audit log:** Append-only compliance ledger maintained in `data/pii_audit_log.json`.

### Architectural Decision on Microsoft Presidio
- **Presidio Evaluation:** Microsoft Presidio was formally evaluated for review PII sanitization.
- **Decision (Skipped in Runtime):** Presidio requires heavy C++ dependencies, `spacy`, and >400 MB language model downloads, adding 45–60 ms per-review overhead.
- **Why Custom Engine Won:** Our compiled regex and contextual boundary redactor executes in **0.028 ms per review** (>35,000 reviews/sec), has zero external dependencies, and delivers **100% empirical recall** on emails and phone numbers on our synthetic benchmark (`benchmark/pii_v3.json`).

Exit Criteria: PII recall table documented in `benchmark/pii_v3.json`; audit ledger active and deterministic.

---

## Phase 4 — Grounded Assistant & LLM Safety

- [x] **4.1 Grounded naming:** c-TF-IDF extracts verified cluster terms; eliminates hallucinated titles.
- [x] **4.2 Processing order enforced:** PII redaction runs strictly *before* clustering, embedding, or copilot access.
- [x] **4.3 P1 Invariant:** All assistant responses cite ground-truth review receipts (`review_id`).
- [x] **4.4 Offline ready:** Full dashboard, search, and copilot run with zero network connectivity.

Exit Criteria: Copilot responses cite exact review IDs without ungrounded hallucinations.

---

## Phase 5 — Regression & Test Suite

- [x] **5.1 14 baseline unit tests preserved:** 100% green (`tests/test_pillars.py`, `tests/test_founder_engine.py`).
- [x] **5.2 New unit tests added:**
  - [x] Contrastive clause splitting (English + Hinglish `phir bhi`, `lekin`) -> `tests/test_sentiment_v3.py`
  - [x] Paraphrase semantic clustering similarity -> `tests/test_theming_v3.py`
  - [x] Theme cluster >= 3 receipts invariant -> `tests/test_theming_v3.py`
  - [x] Rating-assisted calibration conflict handling -> `tests/test_sentiment_v3.py`
  - [x] Synthetic PII precision & recall -> `scripts/benchmark_pii.py`
- [x] **5.3 Automated regression suite:** All **20 unit tests pass (100% OK)** in under 22 seconds (`python -m unittest discover tests`).

---

## Phase 6 — Demo Hardening & Judge-Proofing

### Code & Artifacts Verified
- [x] **6.1 Offline demo mode verified:** Local Parquet storage and cached models ensure zero network dependency.
- [x] **6.2 Pre-loaded apps ready:** 4 portfolio apps pre-loaded in `data/apps/registry.json`:
  1. CloudSync Pro (`com.cloudsync.pro`)
  2. PayFlow Wallet (`com.payflow.wallet`)
  3. HealthTrack (`com.healthtrack.fitness`)
  4. EduLearn Plus (`com.edulearn.plus`)
  Plus live Google Play integration: Google Play Vault (`gps_com_xvoid_vault`).
- [x] **6.3 Seeded anomaly button:** Implemented in `app.py` sidebar (`🚨 Simulate v3.4 Surge`). Injects 100 crash reviews on version 3.4.0, immediately firing the Critical Alert banner, 22.08x velocity spike, and Poisson Z-score alert (**Z = 19.67**). A "↺ Reset Surge Baseline" button restores normal state.
- [x] **6.4 Live ticket generation:** 1-Click "📋 Copy Theme to Ticket" creates formatted Markdown with title, impact score, and 3 verbatim quotes for GitHub, Linear, or Jira.
- [x] **6.5 Praise vs. Bug visual differentiation:** Features and customer delight cards are styled with distinct green tiles (`#107c41`, `rgba(16, 124, 65, 0.15)`) to generate retention tickets rather than bug tickets.
- [x] **6.6 Engine kill-switch built into UI:** Added 1-click "ENGINE MODE (DEMO KILL-SWITCH)" dropdown in `app.py` sidebar. Allows falling back instantly from `v3.0 (Transformer & c-TF-IDF)` to `v2.0 (Lexicon Baseline)` if any issue arises on stage.
- [x] **6.7 Comparison slide ready:** Slide 2b created in `docs/SLIDE_DECK.md` comparing Raw Reviews vs. Pie Charts vs. FeedbackXLR8 Action Queue ("Why Existing Tools Fail").

### Stage Rehearsal Tasks (Actions to perform before presenting)
- [ ] **Rehearsal Task 1 (Poisson Alert on Cue):** Practice clicking "🚨 Simulate v3.4 Surge" at exactly the 1:30 mark in the pitch, confirming the Z = 19.67 alert banner appears instantly.
- [ ] **Rehearsal Task 2 (Live GitHub Paste):** Practice clicking "Copy Theme to Ticket" and pasting the Markdown into a real GitHub Issues page on screen.
- [ ] **Rehearsal Task 3 (Kill-Switch Rehearsal):** Practice flipping the sidebar Engine Mode dropdown to "v2.0 (Lexicon Baseline)" to show judges the fallback resilience.
- [ ] **Rehearsal Task 4 (Fallback App Tab Switching):** Practice switching between CloudSync Pro and PayFlow Wallet if judges ask: "Does this work on other apps?".

---

## Phase 7 — Report & Presentation Delivery

- [x] **7.1 Versioning:** FeedbackXLR8 v3.0 Production Upgrade (with verified v2.0-baseline fallback preserved).
- [x] **7.2 Document cleanup:** Removed all raw LaTeX delimiters (`$..$`) across all documentation; clean, judge-friendly plain text throughout.
- [x] **7.3 Evaluation section on UI:** Page 5 displays live Golden Benchmark comparison card, 4x4 confusion matrix, and transparent failure analysis (Sarcasm, Slang, Brevity).
- [x] **7.4 Speed proof:** Benchmarked at **103,920 reviews/min on CPU** (10,000 reviews in 5.77s), beating the 90-second hackathon requirement by 84.2s.
- [x] **7.5 Real Google Play integration:** Authenticated via Service Account on `com.xvoid.vault`.
- [x] **7.6 Judge defense prepared:** Non-circular blind evaluation, Z-score vs. PSI complementarity, Presidio architectural tradeoffs, and P1 receipt invariants.
