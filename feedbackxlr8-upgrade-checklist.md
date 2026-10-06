# FeedbackXLR8 — Upgrade Checklist v2.0 → v3.0

**Goal:** Replace regex/tokenizer core with verifiable transformer models, keep P1 (traceability) and P3 (PII) pillars intact, and have hard evaluation numbers for the judges.
**Rule:** Do NOT delete existing modules until the new one beats it on the benchmark. Old engine = fallback for the live demo.

---

## Phase 0 — Freeze & Baseline (Do First, ~half day)

- [ ] **0.1 Freeze current code.** Tag/branch current working version (`git tag v2.0-baseline`). The live demo must always run from a version that works.
- [ ] **0.2 Build the golden benchmark set.** Collect **500+ real reviews** (mix from your live app + 2–3 other Play Store apps, stratified by rating 1★–5★).
  - [ ] Hand-label sentiment: positive / negative / mixed / neutral (aim: at least 200 labeled by you).
  - [ ] Hand-label theme for each review (crash, auth/OTP, performance, billing, UI/UX, praise, other).
  - [ ] Save as `benchmark/golden.csv` — this file is sacred. Never edit labels after finalizing.
- [ ] **0.3 Score the CURRENT engine on the golden set.** Record precision / recall / F1 per class + confusion matrix → `benchmark/baseline_v2.json`. These are the numbers you must beat.
- [ ] **0.4 Write the evaluation script once** (`eval.py`) so every future engine is scored identically. One command, one JSON out.

✅ **Phase 0 exit:** `baseline_v2.json` exists, `eval.py` runs clean, old demo still works.

---

## Phase 1 — Sentiment Engine Upgrade (`sentiment.py`)

- [ ] **1.1 Choose candidate models** (pick 2 to test, don't test five):
  - [ ] `cardiffnlp/twitter-roberta-base-sentiment-latest` (English)
  - [ ] `nlptown/bert-base-multilingual-uncased-sentiment` (1–5 stars, multilingual, aligns with rating drag math) ← **recommended if any Hinglish/non-English reviews exist**
  - [ ] Runner-up if multilingual matters more: `cardiffnlp/twitter-xlm-roberta-base-sentiment`
- [ ] **1.2 Implement `sentiment_v3.py`** — transformers pipeline, label + confidence output per review.
- [ ] **1.3 Mixed-sentiment clause splitter:** split reviews on `but / however / though / although / yet / phir bhi` → run model per clause, combine.
  - [ ] Unit tests: "Great UI, BUT crashes after 5 minutes" → UI: pos, crash: neg, review: mixed.
- [ ] **1.4 Keep rating-assisted calibration as a layer:** model_conf < 0.6 → check star rating for tiebreak; rating/model conflict → tag `mixed` + boost audit flag.
- [ ] **1.5 Run `eval.py`** → must beat baseline F1 by ≥5 points or keep old engine for that class.
- [ ] **1.6 Cache:** store model outputs per review_id in Parquet so demo never re-runs inference.

✅ **Exit:** `benchmark/sentiment_v3.json` shows improved F1; clause-splitter tests pass.

---

## Phase 2 — Theme Clustering (`app.py` theme logic → new `theming_v3.py`)

- [ ] **2.1 Add embedding model:** `all-MiniLM-L6-v2` (English) or `paraphrase-multilingual-MiniLM-L12-v2` (multilingual). Embed all reviews → 384-dim vectors, cached in Parquet.
- [ ] **2.2 Cluster with HDBSCAN** (min_cluster_size ≈ 5, cosine metric). Noise points = "misc/other" bucket.
- [ ] **2.3 Label clusters via c-TF-IDF top terms** (BERTopic-style). No LLM needed for naming yet.
- [ ] **2.4 Map clusters to existing severity weights** — each cluster gets severity class via keyword rules + manual review of top 10 terms.
- [ ] **2.5 P1 traceability check:** every cluster must expose ≥3 receipts (review_id, version, stars, verbatim) — enforce in code, add a test.
- [ ] **2.6 Evaluate:** theme purity on golden set (same-cluster reviews share theme?) vs. old regex grouping. Add "paraphrase recall" test set: "app won't open" / "crashes on launch" / "force closes" must land in the same cluster.
- [ ] **2.7 Drift bonus:** topic distribution over weekly windows → feeds your existing PSI calculation. Cheap win for the report.

✅ **Exit:** paraphrase test passes; every cluster has receipts; theme purity ≥ baseline.

---

## Phase 3 — PII Shield Hardening (`pii_redactor.py`)

- [ ] **3.1 Add Microsoft Presidio** (local, free) behind your existing `[EMAIL_REDACTED]` / `[PHONE_REDACTED]` masks — keep your exact output format so downstream code doesn't change.
- [ ] **3.2 Edge-case test set:** "call me at five five five one two three", "ping me on whatsapp at...", Hindi text with phone numbers, emails in unicode, @handles, order IDs.
- [ ] **3.3 Prove recall honestly:** build a synthetic PII test set (~100 reviews with planted PII), report recall **per entity type** — drop the blanket "100% recall" claim from the report unless the number holds.
- [ ] **3.4 Keep `pii_audit_log.json`** — extend it to log which detector (regex vs Presidio) caught each hit.

✅ **Exit:** PII recall table in `benchmark/pii_v3.json`; audit log unchanged in format.

---

## Phase 4 — LLM (Optional, Surgical)

- [ ] **4.1 Only if theme names from 2.3 look bad in demo:** add small LLM pass to name/summarize the top clusters (NOT per review).
- [ ] **4.2 Ordering rule (say this in pitch):** PII redaction → clustering → LLM naming. LLM never touches raw reviews.
- [ ] **4.3 Enforce P1:** every LLM sentence must cite receipt IDs; add a validator that rejects LLM output with no cited IDs.
- [ ] **4.4 Cache LLM outputs** — demo runs offline from cache.

✅ **Exit:** either LLM naming live + validated, or decision documented to skip it.

---

## Phase 5 — Regression & Test Suite

- [ ] **5.1 Update the 14 existing unittests** for new module signatures; keep them green.
- [ ] **5.2 Add new tests:**
  - [ ] clause splitter cases (≥6 including Hinglish)
  - [ ] paraphrase clustering (≥3 crash variants same cluster)
  - [ ] every-alert-has-≥3-receipts invariant
  - [ ] PII recall on synthetic set
  - [ ] confidence/rating calibration conflict case
- [ ] **5.3 `python -m unittest` green + `eval.py` numbers exported** before any report edits.

---

## Phase 6 — Demo Hardening (Judge-Proofing)

- [ ] **6.1 Offline demo mode:** full pipeline runs from cached Parquet — no network calls on stage.
- [ ] **6.2 Pre-loaded apps:** 2–3 fallback Play Store apps configured; live app ingest tested morning-of.
- [ ] **6.3 Seeded anomaly:** inject a fake 24h crash spike so the Poisson Z > 2.5 alert fires on cue during demo.
- [ ] **6.4 Live hand-off:** 1-click copy → paste into a real GitHub issue during demo (create repo beforehand).
- [ ] **6.5 Comparison slide:** same reviews in (a) raw list, (b) generic "64% positive" pie chart, (c) FeedbackXLR8 priority queue.
- [ ] **6.6 Kill-switch script:** if live ingest fails, 10-second path to cached mode (rehearse twice).

---

## Phase 7 — Report & Pitch Updates

- [ ] **7.1 Version:** "Production Release v2.0" → keep simple, note engine v3.
- [ ] **7.2 Replace "$N \ge 500$" and all LaTeX with clean plain formatting; fix empty code-module cells in FR table.**
- [ ] **7.3 Add evaluation section:** baseline vs v3 F1 (before/after table), confusion matrix, PII recall per entity type.
- [ ] **7.4 Add "Built in X hours" + test count + live API facts slide** (effort signal).
- [ ] **7.5 Update architecture diagram:** PII → embeddings/cluster → sentiment+ABSA → priority engine (LLM naming as optional side-branch).
- [ ] **7.6 Prepare answers to the 3 hard judge questions:**
  - [ ] Severity weights → calibration story (derived from rating correlation on golden set, or drag regression)
  - [ ] "Why not just ChatGPT?" → P1 receipts + P3 redaction + verifiable small models
  - [ ] Scale numbers → rough throughput (reviews/min, CPU-only)

---

## Ordering Summary (if time is short)

| Priority | Task | Skip-if-desperate? |
|---|---|---|
| P0 | 0.1–0.4 baseline + eval harness | Never skip |
| P0 | 1.x sentiment transformer | Never skip (biggest accuracy jump) |
| P1 | 2.x embeddings + HDBSCAN | Skip only if theme purity already fine |
| P1 | 6.x demo hardening | Never skip — this wins/loses the hackathon |
| P2 | 3.x Presidio PII | Skip if time < 1 day |
| P2 | 7.x report polish | Never skip |
| P3 | 4.x LLM naming | Skip freely — least value, most risk |

**Estimated total: 2–3 focused days for P0+P1 items.**
