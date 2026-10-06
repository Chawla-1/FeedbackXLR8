# Review Insight Engine — Project Requirements Document

**Hackathon**: Focus Area 2 — Smart Assistants & Chatbots (Enterprise Conversational AI)
**Challenge #17**: 10,000 Reviews, No Time to Read Them (Feedback & Review Analyzer)
**Document status**: v1.0 — working guide
**Last updated**: 2026-09-21

---

## 1. Vision & Elevator Pitch

**One-liner**: An enterprise feedback intelligence platform that turns thousands of unstructured reviews into prioritized, traceable, and validated themes — with alerts that surface emerging issues before they hurt ratings or revenue.

**Core value proposition**: Not "sentiment scores" — *speed to signal*. A product manager opens the dashboard (or receives a morning digest) and in 60 seconds knows: what broke, who's angry, whether it's getting worse, and the exact customer quotes to back it up.

**Why an enterprise pays for this**:
- App-store rating directly drives downloads (ASO). A 0.1-star drop = measurable revenue loss.
- Critical complaints (crashes after update, login failures, pricing anger) are discovered weeks late today.
- Trust is the adoption blocker: every insight must be traceable to real verbatims, sentiment must be validated, PII must be redacted, and model drift must be monitored.

---

## 2. The Three Enterprise-Grade Pillars (Non-Negotiable)

These map directly to the rubric. Every design decision must serve at least one.

| Pillar | Requirement | Success Criteria |
|---|---|---|
| **P1 — Traceability** | Every theme, summary, and insight links back to raw example verbatims | One click from any theme card to ≥3 real quotes; no "black-box" claims |
| **P2 — Validated Accuracy** | Sentiment model validated against a labelled sample with a visible report | Stratified sample (n ≥ 500), precision/recall/F1 published, confusion matrix shown, failure modes honestly discussed |
| **P3 — PII Redaction + Drift Monitoring** | Personal data redacted before processing/analysis; model drift tracked over time | Before/after redaction demo; drift dashboard showing rolling sentiment distribution + new-theme detection vs. baseline |

---

## 3. Personas & User Stories

### Primary persona: Priya, Product Manager (mid-size app, 2,000 reviews/day)
- "Every Monday I spend 3 hours reading reviews and still miss things. I need the top 3 emerging issues by 9am."
- **Stories**:
  - As a PM, I want theme cards ranked by business impact so I know what to fix first.
  - As a PM, I want to click any theme and see real customer quotes so I can trust and forward the insight.
  - As a PM, I want a spike alert ("login failures up 4x in 6h") so I catch critical issues same-day.

### Secondary persona: David, Customer Success Lead
- **Stories**: filter themes by platform/version/segment; export a board-ready brief; verify a reported theme against raw data.

### Tertiary persona: Legal/Compliance reviewer
- **Stories**: confirm PII redaction is on and working; confirm the model has a documented accuracy report.

---

## 4. Scope

### 4.1 In scope (MVP — must build)
1. Batch CSV upload of reviews (dataset: app-store reviews / Sentiment140-style Kaggle set).
2. Preprocessing pipeline: dedup, language filter, PII redaction.
3. Sentiment classification (positive / negative / neutral; aspect-level where feasible).
4. Theme discovery: clustering into named themes (e.g., "crash after update", "login failure", "pricing anger").
5. Theme summarization: auto title + one-line summary + representative verbatims (extractive first; LLM-assisted second).
6. Dashboard: theme cards (volume, sentiment mix, trend arrow, top verbatims), filters (date, rating, platform, version), sentiment distribution charts.
7. **Emerging-issue alert**: theme spike detection vs. rolling baseline, with severity = volume × negativity × recency.
8. **Validation report page**: labelled-sample accuracy metrics + confusion matrix + failure-mode notes.
9. **Drift monitor page**: rolling sentiment distribution, new-theme emergence, confidence trend.
10. **Morning-brief generator**: auto one-paragraph digest + top 3 themes, copyable/forwardable.

### 4.2 Stretch goals (if time permits)
- Aspect-based sentiment ("battery: neg / camera: pos").
- Theme lifecycle tracking: tag a theme "fixed in v2.5", show sentiment recovery (proves ROI).
- Cohort comparison (Android vs iOS, free vs paid, region).
- Multi-source ingestion (support tickets + surveys joined into one theme view).
- Natural-language query chatbot over the review corpus ("what do users say about the new pricing?") with cited verbatims.

### 4.3 Out of scope (say no, loudly, in the pitch)
- Real-time streaming ingestion (batch + simulated freshness is enough for the demo).
- Fine-tuning custom LLMs (use off-the-shelf models; time budget doesn't allow).
- User auth / multi-tenancy (demo as single-tenant).

---

## 5. Functional Requirements

### FR-1 Ingestion
- **FR-1.1** Accept CSV upload with columns: `review_text`, `rating` (1–5), `date`, `platform`, `app_version` (optional: `source`, `user_segment`).
- **FR-1.2** Accept the provided Kaggle dataset with zero config (auto column mapping).
- **FR-1.3** Simulate freshness: dataset includes timestamps spanning weeks; the pipeline processes in "batches" so drift and alerts can be demonstrated live.

### FR-2 Preprocessing & PII Redaction (P3)
- **FR-2.1** Deduplicate near-identical reviews.
- **FR-2.2** Language detection; keep English for MVP (log others).
- **FR-2.3** Redact: emails, phone numbers, person names, URLs, addresses. Show before/after on the dashboard (demo gold).
- **FR-2.4** Redaction must happen *before* clustering/summarization so no PII leaks into stored themes.

### FR-3 Sentiment Analysis (P2)
- **FR-3.1** Classify each review positive/negative/neutral. Baseline: VADER/TextBlob; preferred: small HF transformer (`cardiffnlp/twitter-roberta-base-sentiment` or similar).
- **FR-3.2** Handle mixed sentiment explicitly: flag reviews with contrasting clauses ("Love the app BUT the update ruined it") — these are the highest-value reviews.
- **FR-3.3** Store per-review confidence score.

### FR-4 Theme Discovery & Summarization (P1)
- **FR-4.1** Cluster reviews (embeddings + HDBSCAN or TF-IDF + NMF fallback) into themes; minimum cluster size enforced; noise cluster labelled "Misc".
- **FR-4.2** Auto-name each theme (top keywords → readable label).
- **FR-4.3** Each theme carries: representative verbatims (extractive, 3–5), one-line LLM summary, volume, sentiment mix, first/last seen, trend vs previous period.
- **FR-4.4** **Traceability invariant**: no theme is displayed without its linked verbatims. This is a hard rule, tested in the demo.

### FR-5 Dashboard
- **FR-5.1** KPI strip: total reviews, % negative, avg rating trend, active themes, open alerts.
- **FR-5.2** Theme cards sorted by **impact score = normalized(volume) × negativity_ratio × recency_weight**.
- **FR-5.3** Filters: date range, rating, platform, version, sentiment.
- **FR-5.4** Theme detail drawer: title, summary, trend sparkline, sentiment breakdown, full verbatim list (paginated), confidence.
- **FR-5.5** Sentiment distribution + volume-over-time charts.

### FR-6 Emerging-Issue Alerts (Killer Feature)
- **FR-6.1** Compare last-24h (or last batch) theme activity vs. 7/30-day rolling baseline.
- **FR-6.2** Alert when mentions of a theme exceed threshold (e.g., z-score > 2.5 or 3× baseline).
- **FR-6.3** Alert card shows: theme, spike factor, % negative, sample verbatims, severity score.
- **FR-6.4** Demo hook: inject a synthetic "update broke login" surge mid-dataset so the alert fires live on stage.

### FR-7 Validation Report (P2)
- **FR-7.1** Hold out a stratified labelled sample (n ≥ 500, balanced across sentiment classes).
- **FR-7.2** Compute precision/recall/F1 per class + overall accuracy; render confusion matrix.
- **FR-7.3** Show failure-mode analysis: sarcasm, negation ("not bad"), mixed sentiment, short reviews.
- **FR-7.4** One-click "re-run validation" after model swap (shows the comparison mentality enterprises want).

### FR-8 Drift Monitoring (P3)
- **FR-8.1** Rolling sentiment distribution (7-day window) vs. historical baseline.
- **FR-8.2** Embedding-space drift: distribution distance (KL divergence or PSI) between recent and baseline review embeddings.
- **FR-8.3** New-theme emergence feed: themes that appeared in the last N days with no prior history (novel issues = model blind spots).
- **FR-8.4** Drift "health" indicator (green/yellow/red) on the dashboard header.

### FR-9 Morning Brief
- **FR-9.1** Auto-generate a 3–5 sentence digest: overall sentiment movement, top 3 themes with one-line context, active alerts.
- **FR-9.2** Copy-to-clipboard / export as Markdown. This is the "forward to leadership" artifact.

---

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Process 10,000 reviews in < 90 seconds on a laptop (demo must not stall) |
| **Reproducibility** | Fixed seeds; pipeline is a single deterministic script/notebook |
| **Trust** | Every AI-generated string in the UI carries its source verbatims within one click |
| **Privacy** | No raw PII persisted after redaction stage; redaction report logged |
| **Usability** | A judge can reach the "wow moment" (alert firing + verbatim traceability) in < 3 minutes unassisted |
| **Explainability** | Every score (impact, severity, drift) has a documented formula shown in the UI (info tooltip) |

---

## 7. Data Plan

- **Primary dataset**: Kaggle app-store product reviews (or Sentiment140 for scale). Target: ≥ 10,000 reviews with text + rating + date.
- **Enrichment (strongly recommended)**: merge a second small labelled sentiment dataset purely for the validation report (FR-7) — this makes P2 credible because validation happens on *independent* labels, not the model's own training data.
- **Synthetic surge injection**: handcraft 80–150 realistic reviews ("Updated yesterday and now I can't log in!!") dated inside the recent window to trigger FR-6 live.
- **Data quality checks**: null/empty text, encoding issues, duplicate bursts (review-bombing detection is a nice talking point).

---

## 8. Proposed Architecture

```
CSV Upload
   │
   ▼
[Ingest & Validate] ──► data-quality report
   │
   ▼
[Preprocess] dedup → language filter → PII REDACTION (Presidio/spaCy NER + regex) ──► redaction before/after log
   │
   ├──► [Sentiment Model] ──► per-review label + confidence
   │
   ├──► [Embeddings] ──► [Clustering: HDBSCAN / NMF] ──► themes
   │
   ▼
[Theme Engine] name, summarize, representative verbatims, impact score
   │
   ├──► [Alert Engine] spike detection vs rolling baseline
   ├──► [Drift Monitor] sentiment distribution + embedding distance + new themes
   ├──► [Validation Engine] labelled-sample metrics + confusion matrix
   │
   ▼
[Dashboard] Streamlit (MVP) / React + FastAPI (stretch)
   └──► [Brief Generator] LLM digest of top themes + alerts
```

**Tech stack (free, hackathon-proven)**:
- Python + pandas, scikit-learn
- Sentiment: VADER (baseline) → `cardiffnlp/twitter-roberta-base-sentiment-latest` (main)
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Clustering: HDBSCAN (fallback: K-means on TF-IDF, or NMF topics)
- PII: Microsoft Presidio (or spaCy `en_core_web_sm` NER + regex)
- Charts: Plotly (Streamlit) or Chart.js (React)
- LLM summarization: free-tier API or local small model — extractive verbatims remain the source of truth
- App: **Streamlit for the MVP** (fastest path to a working dashboard); re-skin into React only if time allows

---

## 9. Demo Script (8–10 minutes)

1. **Hook (60s)**: "This app gets 2,000 reviews a day. Nobody can read them. Here's what they've been missing." Show raw review wall.
2. **Upload & pipeline (60s)**: drop the CSV → live processing log → redaction before/after flashes on screen.
3. **Dashboard reveal (90s)**: KPIs, theme cards ranked by impact. Click the top card → verbatims drawer → *"Every claim is one click from real customer quotes."* (P1 ✔)
4. **Validation (60s)**: open the accuracy report — confusion matrix, F1, failure-mode honesty slide. *"We don't ask you to trust it — we show you the numbers."* (P2 ✔)
5. **Alert moment (90s)**: run the recent batch → alert fires: "Login failures up 4.2x, 78% negative." Click through to verbatims. This is the wow moment — pause here.
6. **Drift (60s)**: drift health flips yellow/red on the new batch; new-theme feed shows "update-related login" as a novel cluster. (P3 ✔)
7. **Morning brief (45s)**: generate and copy the digest. *"This is what a PM forwards to leadership every morning."*
8. **Close (30s)**: roadmap slide (multi-source, lifecycle ROI tracking) + the three pillars recap.

---

## 10. Success Metrics & Judging-Criteria Mapping

| Judging expectation | Where we prove it |
|---|---|
| Theme traceability to real verbatims | FR-4.4 invariant + demo step 3 |
| Validated sentiment accuracy | FR-7 report + demo step 4 |
| PII redaction | FR-2 + before/after in demo step 2 |
| Drift monitoring over time | FR-8 + demo step 6 |
| Enterprise relevance & innovation | Alert engine, morning brief, impact scoring, ROI roadmap |

Internal build targets:
- Sentiment macro-F1 ≥ 0.80 on validation sample (adjust expectation to what the model actually achieves; honesty > inflation)
- Theme cluster quality: ≥ 70% of reviews assigned to non-Misc themes; spot-check readability of top 10 theme names
- End-to-end runtime < 90s for 10k reviews
- Demo completes in < 10 min with zero manual intervention

---

## 11. Milestones & Time Budget (suggested 2–3 day sprint)

| Phase | Deliverable | Est. effort |
|---|---|---|
| M0 — Setup | Repo, dataset downloaded & cleaned, synthetic surge injection script | 0.5 day |
| M1 — Core pipeline | Ingest → redact → sentiment → clustering → theme cards (terminal/JSON output first) | 1 day |
| M2 — Dashboard | Streamlit UI: KPIs, theme cards, verbatim drawer, filters | 1 day |
| M3 — The three pillars | Validation report, drift monitor, redaction viewer | 1 day |
| M4 — Killer features | Alert engine + brief generator | 0.5 day |
| M5 — Polish & rehearse | Demo script run-through ×3, failure fallbacks (pre-computed outputs if live run risks failing), slide deck | 0.5 day |

**Rule**: dashboard polish is *last*. A working pipeline with an honest accuracy report beats a beautiful UI with a fake backend — judges probe traceability, not gradients.

---

## 12. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Live processing stalls on stage | Pre-compute everything; live run on a 500-review subset, full dataset results cached |
| Clustering produces garbage theme names | Fallback to rating+keyword buckets; hand-curate top themes for the demo dataset |
| Sentiment model underperforms on app reviews (sarcasm) | Report it honestly as a failure mode; show aspect-level flagging as mitigation |
| PII tool misses edge cases | Layered approach (regex + NER); demo uses obvious cases (emails, phone numbers) |
| Scope creep into chatbot stretch | Chatbot is explicitly stretch; the three pillars + alert engine are the score |

---

## 13. Naming & Positioning

- Working name: **Review Insight Engine** (swap freely)
- Positioning sentence for the deck: *"Turns 10,000 unread reviews into three decisions a day — every insight traceable, every model validated, every risk monitored."*
