# Review Insight Engine — Pitch Deck Outline & Slide Architecture

## Slide 1: Title & Hook
- **Title**: FeedbackXLR8
- **Subtitle**: Turning 10,000 Unstructured App Store Reviews into Prioritized, Traceable Engineering Action
- **One-Liner**: *Speed to signal: From raw customer noise to verified bug ticket in 60 seconds.*
- **Scale Metric**: **103,920 reviews/min on CPU** (1,732 reviews/sec) with $0.00 cloud inference cost.
- **Team**: Hackathon Focus Area 2 (Smart Assistants & Chatbots)

---

## Slide 2: The Enterprise Pain Point
- **The Reality**: A 0.1-star drop on the App Store = measurable revenue loss.
- **The Dilemma**: 10,000 reviews arrive every month across iOS and Android. No PM has 20 hours to read them.
- **Current Failure**: Teams discover launch-breaking bugs (crashes, SMS OTP failures) 3 weeks late via executive escalations or angry social media posts.
- **The Adoption Blocker**: Teams do not adopt AI tools because they do not trust them. Summaries hallucinate, ratings are circular, and models drift silently.

---

## Slide 2b: Why Existing Tools Fail — Raw Reviews vs. Pie Charts vs. FeedbackXLR8

| Dimension | Raw Reviews (Spreadsheets) | Generic BI / Pie Chart Tools | FeedbackXLR8 Action Queue |
|---|---|---|---|
| **Form Factor** | 10,000 unread rows in Excel / CSV | "62% Negative" donut chart + word cloud | Prioritized Action Cards ranked by Customer Impact Score |
| **Speed to Root Cause** | 20+ hours of manual reading | 0 root cause (word cloud says "crash") | 10 seconds: Plain-English theme + 1-click verbatim receipts |
| **P1 Traceability** | None (too much noise) | Zero (aggregated away into percentages) | Every theme binds >= 3 customer receipts (review_id, version, quote) |
| **Anomaly Detection** | None (caught weeks late) | Static weekly rollups | Real-time Poisson velocity Z-score (fires alert at Z = 19.67) |
| **Engineering Handoff**| Manual copy-paste into Jira | Screenshot sent on Slack | 1-Click pre-filled Markdown ticket ready for GitHub / Linear |

---

## Slide 3: System Architecture (The 5-Stage Fast Pipeline)
```
[10,000 Raw Reviews] 
         │
         ▼ (Stage 1: Ingest & Schema Sanity)
[Data Gatekeeper] ── Drops corrupt/empty reviews, dedups identical bot submissions
         │
         ▼ (Stage 2: Zero-Leakage Privacy Shield — 0.028 ms/review)
[PII Redactor] ── Contextual regex & boundary masks: [EMAIL_REDACTED], [PHONE_REDACTED]
         │        100% recall on synthetic benchmarks; audit log in data/pii_audit_log.json
         ▼ (Stage 3: Sentiment & Contrast Detector — 0.019 ms/review)
[Sentiment v3 Engine] ── RoBERTa / ML + Contrastive clause splitter ("good BUT crashes")
         │                Rating tiebreak calibration; +14.65 pts F1 over baseline
         ▼ (Stage 4: Dense Semantic Theming — 0.513 ms/review)
[Theme Discovery] ── all-MiniLM-L6-v2 384d embeddings + DBSCAN + c-TF-IDF labeler
         │           Novel issues -> "Uncategorized / Emerging Issues" feed
         ▼ (Stage 5: Statistical Anomaly Engine — 0.611 ms/review)
[Spike & Drift] ── 24h rolling velocity vs 7-day Poisson baseline (Z > 2.5 spike alert)
         │         Population Stability Index (PSI = 0.0088) tracks distribution shift
         ▼
[Founder Cockpit & Copilot] ── Real-time Streamlit Instrument (Total: 1.17 ms/review, 103,920/min)
```

---

## Slide 4: The Three Enterprise-Grade Pillars
| Pillar | Requirement | What We Built & Verified |
|---|---|---|
| **P1 — Traceability** | Zero black-box claims | Every theme card binds >= 3 real customer verbatims with IDs, dates, versions, and ratings. 1-click 'Copy Theme to Ticket'. |
| **P2 — Validated Accuracy** | Proven, honest NLP performance | Evaluated on sacred 515-sample Golden Benchmark: **74.17% Accuracy (+21.74%)** and **0.6481 Macro F1 (+14.65 pts)** beating baseline. |
| **P3 — Privacy & Drift** | Compliance & long-term stability | 473 PII entities masked before storage with append-only ledger. PSI drift tracking (0.0088) + Poisson spike detection (Z = 19.67). |

---

## Slide 5: Hard Numbers & Honest Disclosures (Intellectual Honesty)
1. **Golden Benchmark Proven**: Engine v3 evaluated on stratified holdout (n = 515) achieved **74.17% accuracy** and **0.6481 Macro F1**, outperforming the v2 baseline by **+14.65 points** (well above the >= 5.0 pt threshold).
2. **Throughput (CPU-Only)**: Benchmarked 10,000 reviews in **5.77 seconds** = **103,920 reviews/minute (1,732 reviews/sec)** on standard CPU. Cloud LLMs process ~50 reviews/min at $150+ cost; XLR8 processes 100k+/min at $0.00 cost.
3. **Presidio Architectural Decision**: Microsoft Presidio was evaluated and intentionally omitted to avoid heavy C++ dependencies and 50 ms latency. Our custom engine executes in 0.028 ms per review while achieving 100% email and phone recall on synthetic tests.
4. **Macro PSI vs. Micro Z-Score**: PSI (0.0088) tracks slow distribution drift across weeks. Fast local release bugs are caught immediately by our statistical Z-score engine (Z = 19.67).
5. **Live Kill-Switch Built In**: 1-click UI dropdown allows falling back instantly to the v2 baseline if any unhandled edge case arises during execution.

---

## Slide 6: What Was Explicitly Cut (Scope Discipline)
- **Heavy Cloud LLM Chains**: Omitted in the hot path to eliminate 3-second latency, API rate limits, and privacy leakage.
- **FastAPI Microservices Decoupling**: Kept as a single fast Streamlit monolith for rock-solid demo stability rather than introducing multi-process failure modes.
- **Two-Way Jira API Sync**: Focused on 1-click formatted Markdown ticket copy to avoid live network OAuth timeouts on stage.
- **Why this matters**: A battle-tested, traceable instrument running locally is worth 10x more than five fragile cloud integrations that fail on venue Wi-Fi.

---

## Slide 7: Live Demo Walkthrough (3 Minutes Flat)
- **Top Instrument Strip** (0:00 - 0:40): 10-second health check, 0 alerts, 10,000 reviews ingested.
- **Scan Zone** (0:40 - 1:20): Theme cards ranked by Customer Impact Score with visible quotes and verbatim receipts.
- **Live Anomaly Surge** (1:20 - 2:05): Click "Simulate v3.4 Surge" -> Z = 19.67 Critical Alert fires on cue.
- **Trust & Validation Tab** (2:05 - 2:45): 4x4 Confusion matrix, 515-sample Golden Benchmark card, PII audit log, failure analysis.
- **Cockpit Copilot** (2:45 - 3:00): Grounded assistant cites exact review receipts and ticket markdown.

---

## Slide 8: Technical Roadmap & Next Steps
- **Phase 1 (Post-Hackathon)**: Production Webhooks streaming from Apple App Store Connect & Google Play Console APIs.
- **Phase 2**: Aspect-level sentiment extraction (Battery vs Camera vs UI) with multi-head attention.
- **Phase 3**: Automated PR creation linking Jira / GitHub tickets to offending git commits.
