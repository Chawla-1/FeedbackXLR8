# Review Insight Engine — Pitch Deck Outline & Slide Architecture

## Slide 1: Title & Hook
- **Title**: Review Insight Engine
- **Subtitle**: Turning 10,000 Unstructured Reviews into Prioritized, Traceable Engineering Action
- **One-Liner**: *Speed to signal: From raw customer noise to verified bug ticket in 60 seconds.*
- **Team**: Hackathon Focus Area 2 (Smart Assistants & Chatbots)

---

## Slide 2: The Enterprise Pain Point
- **The Reality**: A 0.1-star drop on the App Store = measurable revenue loss.
- **The Dilemma**: 10,000 reviews arrive every month across iOS and Android. No PM has 20 hours to read them.
- **Current Failure**: Teams discover launch-breaking bugs (crashes, SMS OTP failures) 3 weeks late via executive escalations or angry social media posts.
- **The Adoption Blocker**: Teams don't adopt AI tools because they don't trust them. Summaries hallucinate, ratings are circular, and models drift silently.

---

## Slide 3: System Architecture (The 5-Stage Fast Pipeline)
```
[10,000 Raw Reviews] 
         │
         ▼ (Stage 1: Ingest & Schema Sanity)
[Data Gatekeeper] ── Drops corrupt/empty reviews, dedups identical bot submissions
         │
         ▼ (Stage 2: Zero-Leakage Privacy Shield)
[PII Redactor] ── Regex + spaCy NER masks emails, phones, names into [REDACTED_*]
         │        Creates compliance audit log (473 entities captured in 0.5s)
         ▼ (Stage 3: Sentiment & Contrast Detector)
[Sentiment Engine] ── Text-only lexicon + negation + contrastive clauses ("good BUT crashes")
         │            Zero rating leakage into NLP scores
         ▼ (Stage 4: Taxonomy Classification)
[Theme Discovery] ── Multi-theme pattern matching into 7 enterprise categories
         │           Unmatched reviews → "Emerging Issues" feed (FR-8.3 novel detector)
         ▼ (Stage 5: Statistical Anomaly Engine)
[Spike & Drift] ── 24h rolling velocity vs 7-day Poisson baseline (Z > 2.5 spike alert)
         │         Population Stability Index (PSI) tracks macro distribution shift
         ▼
[Founder Cockpit & Copilot] ── Real-time Streamlit Instrument (Total runtime: 4.64s)
```

---

## Slide 4: The Three Enterprise-Grade Pillars
| Pillar | Requirement | What We Built & Verified |
|---|---|---|
| **P1 — Traceability** | Zero black-box claims | Every theme card binds 3–5 real customer verbatims with IDs, dates, versions, and ratings. 1-click 'Copy Theme to Ticket'. |
| **P2 — Validated Accuracy** | Proven, honest NLP performance | Evaluated on two independent sets: Holdout (n=500, 48.4% text-only) and Blind Human Ground Truth (n=150, 68.7% text-only). Confusion matrix published. |
| **P3 — Privacy & Drift** | Compliance & long-term stability | 473 PII entities masked before storage with full audit ledger. PSI drift tracking + Z-Score spike detection ($Z=19.67$). |

---

## Slide 5: The 5 Honest Disclosures (Intellectual Honesty)
1. **Circularity Diagnosed**: Disclosed that the 500 holdout set labels were rating-derived. To eliminate circularity, we built a blind human-labeled test set ($n=150$) with ratings hidden, scoring **68.7% text-only accuracy**.
2. **Ceiling vs. NLP**: We report **48.4% text-only accuracy** as our real NLP metric. The 91.8% rating-assisted score is disclosed as a tautological ceiling, not a modeling triumph.
3. **Fixed Taxonomy vs. Clustering**: We use taxonomy classification (not unsupervised clustering) for determinism and $<1$s runtime. Genuinely novel bugs fall into our dedicated **"Uncategorized / Emerging"** bucket.
4. **Macro PSI vs. Micro Z-Score**: PSI ($0.0088$) tracks slow global shift across weeks. Fast local bugs are caught immediately by our statistical $Z$-score engine ($Z=19.67$).
5. **Engineering Tradeoff**: We chose an ultra-fast lexicon engine over heavy GPU transformers to guarantee a **4.6-second execution budget** with zero cloud latency.

---

## Slide 6: What Was Explicitly Cut (Scope Discipline)
- **Live CSV Drag-and-Drop Ingestion**: Architected in `ingest.py` but cut from UI to prioritize validation rigor and test suites.
- **FastAPI / Microservices Decoupling**: Kept as a single fast Streamlit monolith for demo stability rather than introducing multi-process risk.
- **Jira / Linear Live API Sync**: Replaced with 1-click direct text ticket exports.
- **Why this matters**: A working, thoroughly tested instrument is worth 10x more than five half-built, fragile integrations.

---

## Slide 7: Live Demo Walkthrough
- Top Strip (10-second health check)
- Scan Zone (Cards sorted by Impact Score with visible quotes)
- Live Surge Simulation (Click $\rightarrow$ $Z=19.67$ Critical Alert fires)
- Trust & Validation Tab (Confusion matrix, PII audit, non-circular benchmark)
- Cockpit Copilot (Conversational drill-down with verified verbatim receipts)

---

## Slide 8: Technical Roadmap & Next Steps
- **Phase 1 (Post-Hackathon)**: Connect streaming Webhooks to Apple App Store Connect & Google Play Console APIs.
- **Phase 2**: Aspect-level sentiment extraction (Battery vs Camera vs UI).
- **Phase 3**: Bidirectional ticket synchronization with Linear, Jira, and Slack alert webhooks.
