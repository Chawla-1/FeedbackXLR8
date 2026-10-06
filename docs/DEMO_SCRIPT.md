# Review Insight Engine — On-Stage Demo Script & Rehearsal Guide

## Duration: 3 Minutes Flat
**Target Audience**: Technical & Product Judges (Focus Area 2 / Hackathon Challenge #17)

---

### Act 1: The Founder's 10-Second Check (0:00 – 0:40)
*Action*: Open `http://localhost:8501`.

**What to Say**:
> "As a founder opening this dashboard at 9 AM, I have exactly 10 seconds before my first meeting. I don't want a wall of charts or a blank chatbot prompt. I need to know one thing: **is something broken right now, and can I trust what this tells me?**
>
> Look at the top instrument strip:
> - Instrument Health reads: **● ALL STABLE**.
> - Active Spike Alerts: **0**.
> - 10,000 real customer reviews ingested across 60 days.
> - 7-Day Negative Friction: **9.2%**.
> 
> Within 5 seconds, I know I don't have a burning fire today. Now let's look at the Scan Zone."

---

### Act 2: The Scan Zone & Verbatim Traceability (Pillar P1) (0:40 – 1:20)
*Action*: Scroll slightly down to the product theme cards.

**What to Say**:
> "Our second layer is the Scan Zone. Themes aren't alphabetized or dumped randomly—they are strictly sorted by **Customer Impact Score**, which weights Volume, Negativity, and Recency.
>
> Notice what is on the card face:
> 1. **Plain English Title**: 'App Stability & Launch Crashes', not 'Cluster_1'.
> 2. **Trend Arrow**: Real rolling 7-day velocity change.
> 3. **Compact Ratio Bar**: Green, gray, red—no slow-to-read pie charts.
> 4. **Visible Quote Without Clicking**: The #1 representative customer quote is right there on the card.
>
> And here is our **Pillar P1 (Traceability Invariant)**: I never have to trust an AI summary blindly.
> *(Click expander on App Stability)*
> One click opens the direct verbatim ledger—exact review IDs, versions, and customer quotes extracted before any LLM touches the text. I can click 'Copy Theme to Ticket' and forward it straight to my lead engineer."

---

### Act 3: The Killer Demo — Live Bug Spike Alert (1:20 – 2:05)
*Action*: Click the top sidebar button: **`🚨 Simulate v3.4 Crash Surge`**.

**What to Say**:
> "Now, what happens when an engineering release goes wrong?
>
> *(Click Simulate v3.4 Crash Surge)*
>
> Watch the screen live. We just injected 100 simulated bug reports on version 3.4.0 into the recent window:
> - The top strip immediately flips to **● 1 ISSUE NEEDS ATTENTION** in red.
> - An action banner appears: 'App Stability & Launch Crashes is spiking at **22x above baseline**.'
> - In Tab 3 (Spike Alert Log), our statistical engine reports a **Z-Score of 19.67** (threshold > 2.5), backed by immediate trigger quotes.
> 
> A product team catches this in 6 hours instead of waiting 3 weeks for an app store rating drop."
>
> *(Click 'Reset Surge to Baseline' to return to green)*

---

### Act 4: The 5 Honest Disclosures & Pillar P2/P3 Defense (2:05 – 2:45)
*Action*: Switch to Tab 2: **`🛡️ Trust & Validation`**.

**What to Say**:
> "The biggest barrier to adopting AI in the enterprise is trust. We defend this system across three rigor pillars:
>
> **1. Validation Rigor (Pillar P2)**:
> - Look at our numbers: We don't hide behind a single inflated metric.
> - Our **Holdout Set (n=500)** achieved **48.4% Text-Only Accuracy** with zero rating leakage. We deliberately tested text words alone—no cheating by reading the star rating column.
> - Our **Human Ground Truth (n=150)**, annotated completely blind with ratings hidden, scored **68.7% Accuracy (0.623 Macro-F1)**.
> - When we allow star rating calibration, accuracy reaches **91.8%**. We report this honestly as a tautological ceiling, not an NLP claim.
> - Our Mixed-Sentiment Detector scores **66.7% Precision**.
>
> **2. Privacy & Drift (Pillar P3)**:
> - Zero PII leakage: 473 emails, phones, and names were masked before storage or clustering, tracked in our compliance audit log.
> - Population Stability Index (PSI = 0.0088) monitors macro distribution drift across weeks.
>
> *(Point to terminal or test suite slide)*
> We backed all of this with an automated test suite (`tests/test_pillars.py`) where all 6 tests pass in 0.2 seconds."

---

### Act 5: Cockpit Copilot & Scope Discipline (2:45 – 3:00)
*Action*: Open bottom-right expander **`💬 Cockpit Copilot`** and ask a question.

**What to Say**:
> "Finally, our conversational assistant isn't a gimmicky front door—it's a drill-down instrument in the bottom-right drawer. A founder asks: *'Why did stability spike?'* and the bot answers with **inline review ID receipts and quotes**.
>
> **Our Scope Discipline**: We deliberately chose a deterministic 4.6-second pipeline over slow 3-minute transformers, and prioritized verifiable validation rigor over unverified UI bells and whistles. Everything you see is tested, traceable, and production-ready."
