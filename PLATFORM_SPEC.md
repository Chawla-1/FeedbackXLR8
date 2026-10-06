# Review Insight Engine — Platform Spec

Reference document for frontend layout, backend architecture, and build order.
Update this as decisions change — it's the source of truth, not the pitch deck.

---

## 1. Design Principles (hold every screen to these)

1. Every pixel answers "is something wrong?" faster, or it's decoration.
2. Red is reserved for status that requires action. If everything is colorful, nothing communicates.
3. Plain English first, the statistic (Z-score, PSI, F1) second — as a subline or on hover, never the headline.
4. Never hide a limitation the data already tells you (circularity, multi-theme overlap, PSI insensitivity) — label it on the screen it affects, not just in a report.
5. The dashboard answers 90% of questions with zero typing. The copilot is for the follow-up question the dashboard can't anticipate.

---

## 2. Global Shell (present on every screen)

### Top bar (single row)
- Left: logo + workspace selector (`Production Workspace ▾`)
- Center-left: live freshness indicator — `● Updated 4 min ago` (green dot)
- Right: dark/light toggle, user menu, single primary action (`Share` / `Deploy`)

### KPI strip (below top bar)
- ONE health chip only: `🟢 All stable` / `🟡 N watching` / `🔴 N critical`
- Total reviews processed + date range (secondary weight)
- 7-day sentiment sparkline (no axis labels, shape only)
- If amber/red: exactly one banner below, plain-English headline, stat as subline

### Left sidebar navigation (not top tabs — scales better as sections grow)
1. Cockpit (default landing)
2. Theme Explorer
3. Validation & Trust
4. Drift & Alerts
5. Data & Ingestion
6. Settings (bottom, separated, low-frequency)

### Copilot
- Floating bottom-right drawer, available from every tab, NOT a nav item
- Every answer must cite theme + verbatim IDs, rendered as clickable links back into the dashboard

---

## 3. Tab-by-Tab Spec

### 3.1 Cockpit (landing page)
**Purpose**: answer "do I need to worry today" in under 10 seconds.
- Theme cards, ranked by impact score (not alphabetical, not chronological)
- Per card: plain-language name, trend arrow, sentiment bar (stacked, not pie), ONE representative verbatim, `Copy Slack Brief` + `Create Ticket` actions
- Click expands inline (accordion/drawer) — never navigates away from the ranked list

### 3.2 Theme Explorer
**Purpose**: deep-dive and filter.
- Full theme list including "Uncategorized / Emerging Issues" bucket
- Filters: date range, platform, app version, sentiment, rating
- Table view toggle for sorting by raw numbers
- All verbatims (not just 1), paginated
- Multi-theme overlap disclaimer visible here: *"Themes are non-exclusive — totals may exceed unique review count."*

### 3.3 Validation & Trust
**Purpose**: the "defend this to legal/board" tab — written for a skeptical non-technical reader.
- Text-only accuracy vs. rating-assisted ceiling, shown side by side, both clearly labeled (one is the real NLP metric, one is a tautological baseline)
- Confusion matrix
- Mixed-sentiment precision/recall/F1 breakdown with confusion counts
- PII redaction audit log — before/after examples, entity counts, timestamp
- One-paragraph honest model disclosure (lexicon vs. transformer tradeoff, why)

### 3.4 Drift & Alerts
**Purpose**: separate the macro signal from the micro signal, explicitly.
- PSI trend chart (macro, rolling weeks) with band legend (<0.1 stable / 0.1–0.25 moderate / >0.25 severe)
- Z-score spike history (micro, per-theme velocity) as a separate chart
- One-line explainer pinned above both: *"PSI measures overall distribution shift. Spike alerts measure per-theme velocity. They are complementary, not redundant."*
- Alert history log: past alerts, action taken, resolution status

### 3.5 Data & Ingestion
- Drag-and-drop CSV upload with live progress bar through pipeline stages
- Batch history (source, row count, timestamp, triggered by)
- Corpus/source metadata lives HERE, not in the main header

---

## 4. Color System

| Token | Light | Dark | Use |
|---|---|---|---|
| Background | `#F7F8FA` | `#14161B` | Page background only |
| Text primary | `#1C1E26` | `#E8E9EC` | Body text |
| Status — stable | `#1E9E6B` | same | Chips, bars, "all clear" states ONLY |
| Status — watch | `#D9A441` | same | Chips, bars, moderate alerts ONLY |
| Status — critical | `#D14343` | same | Chips, bars, critical alerts ONLY |
| Accent | `#3B7A8C` | lighten ~15% | Buttons, links — nothing else |

Rules: no gradients, no decorative color. If you can't explain why an element is red, it shouldn't be red.

---

## 5. Backend Architecture

```
Ingestion → Redaction → Sentiment → Theme Classification → Aggregation → Storage → API → Frontend
                                                                      ↓
                                                    Alert/Drift Engine (scheduled)
```

- **Storage**: Parquet (processed reviews) + DuckDB query layer on top (interactive filtering without re-scanning) + JSON (config, audit logs, alert defs — human-readable, git-diffable)
- **API**: FastAPI wrapping existing pipeline functions — decouples frontend from Streamlit's single-process model
- **Background jobs**: scheduled drift/alert recomputation after each ingestion batch (APScheduler to start)
- **Copilot backend**: retrieval-augmented — retrieve relevant theme summaries + verbatims (your existing traceability structure IS the retrieval index, no separate vector DB needed yet) → pass to LLM with question → return answer + verbatim IDs for clickable citations

### Core API endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/themes` | Ranked theme list, filterable |
| GET | `/themes/{id}/verbatims` | Paginated traceable quotes |
| GET | `/validation/metrics` | Accuracy, confusion matrix, PII audit |
| GET | `/alerts` | Active + historical alerts |
| GET | `/drift` | PSI series + Z-score history |
| POST | `/ingest` | Upload CSV, trigger pipeline, return job ID |
| GET | `/ingest/{job_id}/status` | Poll pipeline progress |
| POST | `/copilot/ask` | RAG-grounded Q&A with citations |

---

## 6. Build Order (avoid rework)

1. Data layer: Parquet + DuckDB query layer on existing pipeline output
2. API layer: FastAPI endpoints wrapping existing pipeline functions, test with curl/Postman
3. Frontend shell: top bar, sidebar, KPI strip, wired to real API, no styling polish
4. Cockpit tab (80% of daily usage)
5. Validation & Trust tab (numbers exist, mostly wiring + honest labeling)
6. Drift & Alerts tab
7. Data & Ingestion tab (self-contained, judge/demo-facing)
8. Copilot (depends on 1–7 existing as retrieval source)
9. Polish pass: color system, freshness timestamps, alert consolidation, bug fixes
10. Rehearse

---

## 7. Open Decisions Log

- [ ] Frontend framework: Streamlit (fast, current) vs. React/Next.js (scales, multi-user) — decide based on remaining time
- [ ] When to introduce a real vector DB for copilot retrieval vs. staying on structured theme/verbatim lookup
- [ ] Human-labelled validation set size beyond the initial 150 (see earlier validation discussion)
