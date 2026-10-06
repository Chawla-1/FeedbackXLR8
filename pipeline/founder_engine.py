"""
Founder Decision & Priority Engine.
Implements the mentor-specified priority score formula, rating lift projection,
release regression detector (Version N vs N-1), and action hand-off issue generator.

Formula:
  Priority Score = Volume Share x Severity Weight x (1 + WoW Growth) x Rating Gap
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any

# Standard severity weights per feedback specification
SEVERITY_WEIGHTS = {
    "crash": 3.0,
    "stability": 3.0,
    "launch": 3.0,
    "data loss": 3.0,
    "login": 2.5,
    "auth": 2.5,
    "payment": 2.5,
    "billing": 2.5,
    "wallet": 2.5,
    "security": 2.5,
    "performance": 2.0,
    "sync": 2.0,
    "lag": 2.0,
    "battery": 2.0,
    "download": 2.0,
    "connection": 2.0,
    "ui": 1.5,
    "ux": 1.5,
    "navigation": 1.5,
    "dark mode": 1.5,
    "design": 1.5,
    "feature": 1.0,
    "request": 1.0,
    "sticker": 1.0,
    "general": 1.0
}


def get_severity_weight(theme_title: str) -> float:
    title_lower = theme_title.lower()
    for kw, weight in SEVERITY_WEIGHTS.items():
        if kw in title_lower:
            return weight
    return 1.5  # Default moderate severity


def calculate_theme_priority_metrics(df: pd.DataFrame, themes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes priority scores, rating lifts, and week-over-week trends for all themes.
    """
    if len(df) == 0 or not themes:
        return []

    total_reviews = len(df)
    app_avg_rating = float(df["rating"].mean())
    df = df.copy()
    
    # Ensure date is datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        max_date = df["date"].max()
        if pd.isna(max_date):
            cutoff_recent = None
            cutoff_prior = None
        else:
            cutoff_recent = max_date - pd.Timedelta(days=7)
            cutoff_prior = max_date - pd.Timedelta(days=14)
    else:
        cutoff_recent = None
        cutoff_prior = None

    enriched_themes = []

    for th in themes:
        title = th.get("title", "Unknown")
        theme_reviews = df[df["theme_title"] == title]
        count = len(theme_reviews)
        if count == 0:
            count = th.get("volume", 1)
            theme_avg = th.get("avg_rating", app_avg_rating)
        else:
            theme_avg = float(theme_reviews["rating"].mean())

        volume_share = count / max(1, total_reviews)
        severity_weight = get_severity_weight(title)

        # Rating gap: How much lower is this theme compared to app baseline?
        raw_gap = float(app_avg_rating - theme_avg)
        rating_gap = max(0.0, raw_gap)

        # Aspect sentiment ratio
        if count > 0 and "sentiment" in theme_reviews.columns:
            pos_ratio = round(len(theme_reviews[theme_reviews["sentiment"] == "positive"]) / count * 100, 1)
            neg_ratio = round(len(theme_reviews[theme_reviews["sentiment"] == "negative"]) / count * 100, 1)
        else:
            pos_ratio = 50.0
            neg_ratio = 0.0

        # Week-over-Week Growth calculation
        if cutoff_recent is not None and "date" in df.columns:
            recent_count = len(theme_reviews[theme_reviews["date"] >= cutoff_recent])
            prior_count = len(theme_reviews[(theme_reviews["date"] >= cutoff_prior) & (theme_reviews["date"] < cutoff_recent)])
            if prior_count > 0:
                raw_growth = (recent_count - prior_count) / prior_count
            else:
                raw_growth = 1.0 if recent_count > 0 else 0.0
            # Cap growth to avoid outlier noise on small volumes
            wow_growth = float(np.clip(raw_growth, -0.75, 3.0))
        else:
            recent_count = count
            prior_count = count
            wow_growth = 0.0

        # Determine if this theme represents positive praise / customer delight
        is_positive = (
            "praise" in title.lower()
            or "delight" in title.lower()
            or (theme_avg >= 4.0 and neg_ratio <= 15.0 and pos_ratio >= 50.0)
            or (raw_gap <= 0.0 and neg_ratio == 0.0 and theme_avg >= 3.5)
        )

        if is_positive:
            # Positive praise themes do not drag down ratings and require no bug remediation
            priority_score = 0.0
            rating_gap = 0.0
            estimated_lift = 0.0
            urgency_badge = "🌟 PRAISE / FEATURE WIN"
        else:
            # Mentor Priority Score Formula for Friction Bugs:
            # Score = Volume share x Severity weight x (1 + Week-over-week growth) x Rating gap
            effective_gap = max(0.1, rating_gap) if neg_ratio > 20.0 else max(0.0, rating_gap)
            raw_score = volume_share * severity_weight * (1.0 + max(0.0, wow_growth)) * effective_gap * 1000.0
            priority_score = round(float(raw_score), 1)

            # Estimated Rating Lift Calculation:
            non_theme_reviews = df[df["theme_title"] != title]
            if len(non_theme_reviews) > 0:
                non_theme_avg = float(non_theme_reviews["rating"].mean())
                projected_total_rating = (len(non_theme_reviews) * non_theme_avg + count * non_theme_avg) / total_reviews
                estimated_lift = max(0.01, round(float(projected_total_rating - app_avg_rating), 2))
            else:
                estimated_lift = 0.10

            urgency_badge = "P0 - URGENT" if priority_score >= 25 else ("P1 - HIGH" if priority_score >= 12 else "P2 - NORMAL")

        # Extract verbatims if missing
        verbatims = list(th.get("verbatims", []))
        if not verbatims and len(theme_reviews) > 0:
            for idx, r in theme_reviews.head(5).iterrows():
                verbatims.append({
                    "review_id": str(r.get("review_id", f"REV-{idx+1}")),
                    "quote": str(r.get("review_text", "")),
                    "rating": int(r.get("rating", 3)),
                    "date": str(r.get("date", ""))[:10],
                    "version": str(r.get("app_version", "Unknown")),
                })

        item = dict(th)
        item.update({
            "volume": count,
            "volume_share_pct": round(volume_share * 100, 1),
            "theme_avg_rating": round(theme_avg, 2),
            "app_avg_rating": round(app_avg_rating, 2),
            "rating_gap": round(rating_gap, 2),
            "severity_weight": severity_weight,
            "wow_growth_pct": round(wow_growth * 100, 1),
            "priority_score": priority_score,
            "estimated_rating_lift": estimated_lift,
            "aspect_positive_pct": pos_ratio,
            "aspect_negative_pct": neg_ratio,
            "recent_week_volume": recent_count,
            "urgency_badge": urgency_badge,
            "is_positive": is_positive,
            "verbatims": verbatims,
        })
        enriched_themes.append(item)

    # Sort: Friction bugs first descending by Priority Score, then Praise/Feature wins
    enriched_themes.sort(key=lambda x: (not x.get("is_positive", False), x.get("priority_score", 0.0)), reverse=True)
    return enriched_themes


def detect_release_regressions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Identifies complaint volume surges per theme between the latest two app versions (vN vs vN-1).
    """
    if len(df) == 0 or "app_version" not in df.columns or "theme_title" not in df.columns:
        return []

    # Get sorted versions by frequency or occurrence
    versions = [v for v in df["app_version"].dropna().unique() if str(v).lower() != "unknown"]
    if len(versions) < 2:
        return []

    # Sort versions if standard vX.Y pattern
    try:
        sorted_versions = sorted(versions, key=lambda x: [int(p) for p in str(x).lstrip('v').split('.') if p.isdigit()], reverse=True)
    except Exception:
        sorted_versions = list(versions)

    latest_ver = sorted_versions[0]
    prev_ver = sorted_versions[1]

    df_latest = df[df["app_version"] == latest_ver]
    df_prev = df[df["app_version"] == prev_ver]

    n_latest = max(1, len(df_latest))
    n_prev = max(1, len(df_prev))

    regressions = []
    themes = df["theme_title"].dropna().unique()

    for theme in themes:
        c_latest = len(df_latest[df_latest["theme_title"] == theme])
        c_prev = len(df_prev[df_prev["theme_title"] == theme])

        rate_latest = c_latest / n_latest
        rate_prev = c_prev / n_prev

        if c_prev > 0:
            multiplier = round(rate_latest / rate_prev, 1)
        elif c_latest >= 5:
            multiplier = round(float(c_latest), 1)
        else:
            multiplier = 1.0

        if multiplier >= 1.8 and c_latest >= 5:
            # Significant regression detected
            # Extract sample verbatims
            verbatims = []
            sample_rows = df_latest[df_latest["theme_title"] == theme].head(3)
            for _, r in sample_rows.iterrows():
                verbatims.append({
                    "review_id": str(r.get("review_id", "")),
                    "quote": str(r.get("review_text", ""))[:140],
                    "rating": int(r.get("rating", 1)),
                    "version": latest_ver
                })

            regressions.append({
                "theme": theme,
                "latest_version": latest_ver,
                "previous_version": prev_ver,
                "latest_count": c_latest,
                "previous_count": c_prev,
                "surge_multiplier": f"{multiplier}x",
                "severity_label": "CRITICAL REGRESSION" if multiplier >= 3.0 else "ELEVATED REGRESSION",
                "sample_verbatims": verbatims,
                "summary": f"{theme} complaints jumped {multiplier}x in {latest_ver} compared to {prev_ver} ({c_latest} vs {c_prev} reports)."
            })

    regressions.sort(key=lambda x: float(x["surge_multiplier"].rstrip("x")), reverse=True)
    return regressions


def generate_ticket_markdown(theme_item: Dict[str, Any], app_name: str = "Application") -> str:
    """
    Generates a prefilled, ready-to-paste markdown issue template for GitHub, Linear, or Jira.
    For positive praise themes, outputs a Customer Delight & Feature Win Card instead of a bug ticket.
    """
    title = theme_item.get("title", "Issue")
    score = theme_item.get("priority_score", 0.0)
    urgency = theme_item.get("urgency_badge", "P1")
    volume = theme_item.get("volume", 0)
    vol_pct = theme_item.get("volume_share_pct", 0)
    drag = theme_item.get("rating_gap", 0)
    lift = theme_item.get("estimated_rating_lift", 0)
    verbatims = theme_item.get("verbatims", [])
    is_positive = theme_item.get("is_positive", False) or "PRAISE" in str(urgency) or "WIN" in str(urgency) or score == 0.0

    if is_positive:
        pos_ratio = theme_item.get("aspect_positive_pct", 100.0)
        theme_avg = theme_item.get("theme_avg_rating", 5.0)
        lines = [
            f"## [🌟 FEATURE WIN] Customer Delight & Retention Anchor: {title}",
            f"**Target System:** `{app_name}` | **Theme Rating:** `{theme_avg:.1f}★` | **Status:** `Customer Delight (No Bug Action Required)`",
            "",
            "### 🌟 Customer Sentiment & Impact",
            f"- **Praise Volume:** {volume:,} verified reviews ({vol_pct}% of total customer feedback)",
            f"- **Satisfaction Index:** {pos_ratio}% Positive Sentiment",
            f"- **Rating Impact:** Exceeds baseline app average (Strengthens overall store rating)",
            "",
            "### 💬 Highlighted Customer Testimonials (Traceable Ground Truth)",
        ]
        for idx, v in enumerate(verbatims[:3], 1):
            stars = "★" * v.get("rating", 5)
            lines.append(f"{idx}. **[{v.get('review_id', 'REV')}]** ({stars}, Version: `{v.get('version', 'latest')}`)")
            lines.append(f"   > *\"{v.get('quote', '').strip()}\"*")

        lines.extend([
            "",
            "### 💡 Recommended Product Actions",
            "- [x] **No Defect Triage Needed:** Feature is functioning smoothly and delighting users.",
            "- [ ] **Marketing & ASO:** Feature this positive quote in Play Store screenshots and release notes.",
            "- [ ] **Protect Core UX:** Ensure upcoming release sprints do not alter or regress this praised workflow.",
            "- [ ] **Developer Appreciation:** Reply in Google Play Console to thank the customer for their review."
        ])
        return "\n".join(lines)

    lines = [
        f"## [{urgency}] Customer Friction Bug: {title}",
        f"**Target System:** `{app_name}` | **Priority Score:** `{score}` | **Urgency:** `{urgency}`",
        "",
        "### 📊 Business Impact Metrics",
        f"- **Complaint Volume:** {volume:,} reviews ({vol_pct}% of total customer feedback)",
        f"- **Rating Drag:** -{drag}★ below application average baseline",
        f"- **Projected Rating Lift on Resolution:** +{lift}★ rating recovery",
        "",
        "### 💬 Customer Verbatims (Traceable Ground Truth)",
    ]

    for idx, v in enumerate(verbatims[:3], 1):
        lines.append(f"{idx}. **[{v.get('review_id', 'REV')}]** (Rating: {v.get('rating', 1)}★, Ver: `{v.get('version', 'latest')}`)")
        lines.append(f"   > *\"{v.get('quote', '').strip()}\"*")

    lines.extend([
        "",
        "### 🛠️ Recommended Action",
        "- [ ] Triage root cause with mobile platform engineering",
        "- [ ] Validate telemetry logs against reported version stamps",
        "- [ ] Ship patch and monitor FeedbackXLR8 Velocity Alerts for regression drop"
    ])

    return "\n".join(lines)
