"""
Competitive Analysis Engine - Analyze competitor reviews to find weaknesses and opportunities

This module provides competitive intelligence by:
1. Analyzing competitor app reviews to identify their weak points
2. Comparing your app's strengths vs competitor weaknesses
3. Finding gaps where competitors are failing but you can excel
4. Identifying areas where you're weak compared to competitors
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
import json
from datetime import datetime, timedelta


class CompetitiveAnalyzer:
    """Analyzes competitor reviews to find strategic opportunities and threats"""
    
    def __init__(self):
        self.theme_weights = {
            "App Stability & Launch Crashes": 10,  # Critical
            "Authentication & Account": 9,
            "Billing & Subscriptions": 9,
            "Performance & Battery": 8,
            "Ads & Monetization": 7,
            "Update & Version Issues": 6,
            "UI/UX & Design": 5,
            "General Praise & Feature Experience": 3,
            "Uncategorized / Emerging Issues": 4,
        }
    
    def analyze_competitor_weakness(
        self, 
        competitor_reviews: pd.DataFrame,
        app_name: str,
        time_window_days: int = 90
    ) -> Dict[str, Any]:
        """
        Analyze competitor reviews to find their weaknesses
        
        Args:
            competitor_reviews: DataFrame with columns [review_text, rating, sentiment, theme_title, date]
            app_name: Name of competitor app
            time_window_days: Only analyze reviews from last N days (default: 90)
        
        Returns:
            Dict with competitor weakness analysis
        """
        # Filter recent reviews
        if 'date' in competitor_reviews.columns:
            cutoff = datetime.now() - timedelta(days=time_window_days)
            df = competitor_reviews[pd.to_datetime(competitor_reviews['date']) >= cutoff].copy()
        else:
            df = competitor_reviews.copy()
        
        if len(df) == 0:
            return {"error": "No reviews in time window"}
        
        # 1. Identify problem themes (negative sentiment)
        negative_reviews = df[df['sentiment'] == 'negative']
        theme_problems = negative_reviews.groupby('theme_title').agg({
            'review_text': 'count',
            'rating': 'mean'
        }).rename(columns={'review_text': 'count'})
        
        theme_problems['severity'] = theme_problems.apply(
            lambda row: row['count'] * (5 - row['rating']) * self.theme_weights.get(row.name, 5),
            axis=1
        )
        theme_problems = theme_problems.sort_values('severity', ascending=False)
        
        # 2. Find top 5 weaknesses with sample reviews
        top_weaknesses = []
        for theme, row in theme_problems.head(5).iterrows():
            sample_reviews = negative_reviews[negative_reviews['theme_title'] == theme]['review_text'].head(3).tolist()
            top_weaknesses.append({
                "theme": theme,
                "negative_count": int(row['count']),
                "avg_rating": round(row['rating'], 2),
                "severity_score": round(row['severity'], 1),
                "sample_complaints": sample_reviews
            })
        
        # 3. Identify pain points from review text patterns
        pain_points = self._extract_pain_points(negative_reviews)
        
        # 4. Sentiment breakdown
        sentiment_dist = df['sentiment'].value_counts()
        sentiment_breakdown = {
            "negative": int(sentiment_dist.get('negative', 0)),
            "mixed": int(sentiment_dist.get('mixed', 0)),
            "positive": int(sentiment_dist.get('positive', 0)),
            "neutral": int(sentiment_dist.get('neutral', 0)),
            "negative_percentage": round(sentiment_dist.get('negative', 0) / len(df) * 100, 1)
        }
        
        # 5. Rating distribution
        rating_dist = df['rating'].value_counts().sort_index()
        low_ratings_pct = (rating_dist.get(1, 0) + rating_dist.get(2, 0)) / len(df) * 100
        
        # 6. Emerging issues (recent spike in complaints)
        emerging_issues = self._detect_emerging_issues(df, time_window_days)
        
        return {
            "competitor_name": app_name,
            "analysis_period": f"Last {time_window_days} days",
            "total_reviews_analyzed": len(df),
            "overall_weakness_score": round(sentiment_breakdown['negative_percentage'] + low_ratings_pct, 1),
            "top_weaknesses": top_weaknesses,
            "pain_points": pain_points,
            "sentiment_breakdown": sentiment_breakdown,
            "rating_distribution": {int(k): int(v) for k, v in rating_dist.items()},
            "low_rating_percentage": round(low_ratings_pct, 1),
            "emerging_issues": emerging_issues,
            "recommendations": self._generate_opportunity_recommendations(top_weaknesses, pain_points)
        }
    
    def compare_apps(
        self,
        my_app_reviews: pd.DataFrame,
        competitor_reviews: pd.DataFrame,
        my_app_name: str,
        competitor_name: str,
        time_window_days: int = 90
    ) -> Dict[str, Any]:
        """
        Compare your app against competitor to find strengths and weaknesses
        
        Args:
            my_app_reviews: Your app's review DataFrame
            competitor_reviews: Competitor's review DataFrame
            my_app_name: Your app name
            competitor_name: Competitor app name
            time_window_days: Analysis time window
        
        Returns:
            Comprehensive comparison analysis
        """
        # Analyze both apps
        my_analysis = self._quick_app_analysis(my_app_reviews, time_window_days)
        competitor_analysis = self._quick_app_analysis(competitor_reviews, time_window_days)
        
        # Find themes where you're BETTER (your strength, their weakness)
        your_advantages = []
        for theme in set(my_analysis['theme_scores'].keys()) | set(competitor_analysis['theme_scores'].keys()):
            my_score = my_analysis['theme_scores'].get(theme, {'score': 0})['score']
            comp_score = competitor_analysis['theme_scores'].get(theme, {'score': 0})['score']
            
            if my_score > comp_score + 15:  # Significant advantage threshold
                your_advantages.append({
                    "theme": theme,
                    "your_score": round(my_score, 1),
                    "competitor_score": round(comp_score, 1),
                    "advantage_margin": round(my_score - comp_score, 1),
                    "status": "💪 Your Strength"
                })
        
        # Find themes where you're WORSE (competitor strength, your weakness)
        your_weaknesses = []
        for theme in set(my_analysis['theme_scores'].keys()) | set(competitor_analysis['theme_scores'].keys()):
            my_score = my_analysis['theme_scores'].get(theme, {'score': 0})['score']
            comp_score = competitor_analysis['theme_scores'].get(theme, {'score': 0})['score']
            
            if comp_score > my_score + 15:  # Significant disadvantage threshold
                your_weaknesses.append({
                    "theme": theme,
                    "your_score": round(my_score, 1),
                    "competitor_score": round(comp_score, 1),
                    "gap": round(comp_score - my_score, 1),
                    "status": "⚠️ Improvement Needed"
                })
        
        # Find opportunities (both are weak, market gap)
        market_gaps = []
        for theme in set(my_analysis['theme_scores'].keys()) | set(competitor_analysis['theme_scores'].keys()):
            my_score = my_analysis['theme_scores'].get(theme, {'score': 0})['score']
            comp_score = competitor_analysis['theme_scores'].get(theme, {'score': 0})['score']
            
            if my_score < 60 and comp_score < 60:  # Both below 60 = market opportunity
                market_gaps.append({
                    "theme": theme,
                    "your_score": round(my_score, 1),
                    "competitor_score": round(comp_score, 1),
                    "opportunity": "🎯 Market Gap - Both apps weak here",
                    "priority": "HIGH" if comp_score < 40 else "MEDIUM"
                })
        
        # Overall comparison
        my_overall = my_analysis['overall_score']
        comp_overall = competitor_analysis['overall_score']
        
        return {
            "my_app": my_app_name,
            "competitor": competitor_name,
            "analysis_period": f"Last {time_window_days} days",
            "overall_comparison": {
                "your_score": round(my_overall, 1),
                "competitor_score": round(comp_overall, 1),
                "verdict": "🏆 You're winning" if my_overall > comp_overall else "⚠️ Competitor ahead",
                "score_gap": round(abs(my_overall - comp_overall), 1)
            },
            "your_advantages": sorted(your_advantages, key=lambda x: x['advantage_margin'], reverse=True),
            "your_weaknesses": sorted(your_weaknesses, key=lambda x: x['gap'], reverse=True),
            "market_gaps": sorted(market_gaps, key=lambda x: (x['priority'], -x['your_score'])),
            "strategic_recommendations": self._generate_strategic_recommendations(
                your_advantages, your_weaknesses, market_gaps
            ),
            "detailed_breakdown": {
                "your_app": my_analysis,
                "competitor": competitor_analysis
            }
        }
    
    def _quick_app_analysis(self, df: pd.DataFrame, time_window_days: int) -> Dict[str, Any]:
        """Quick analysis of an app's reviews"""
        if 'date' in df.columns:
            cutoff = datetime.now() - timedelta(days=time_window_days)
            df = df[pd.to_datetime(df['date']) >= cutoff].copy()
        
        if len(df) == 0:
            return {
                "overall_score": 0,
                "theme_scores": {},
                "sentiment_pct": {"positive": 0, "negative": 0, "mixed": 0, "neutral": 0}
            }
        
        # Theme-wise scoring (0-100 scale)
        theme_scores = {}
        for theme in df['theme_title'].unique():
            theme_df = df[df['theme_title'] == theme]
            
            # Calculate positive percentage
            pos_count = (theme_df['sentiment'] == 'positive').sum()
            neg_count = (theme_df['sentiment'] == 'negative').sum()
            
            if len(theme_df) > 0:
                score = (pos_count / len(theme_df)) * 100
                theme_scores[theme] = {
                    "score": score,
                    "positive": int(pos_count),
                    "negative": int(neg_count),
                    "total": len(theme_df)
                }
        
        # Overall score (weighted by theme importance)
        weighted_sum = 0
        weight_sum = 0
        for theme, data in theme_scores.items():
            weight = self.theme_weights.get(theme, 5)
            weighted_sum += data['score'] * weight
            weight_sum += weight
        
        overall_score = weighted_sum / weight_sum if weight_sum > 0 else 0
        
        # Sentiment distribution
        sentiment_dist = df['sentiment'].value_counts()
        sentiment_pct = {
            "positive": round(sentiment_dist.get('positive', 0) / len(df) * 100, 1),
            "negative": round(sentiment_dist.get('negative', 0) / len(df) * 100, 1),
            "mixed": round(sentiment_dist.get('mixed', 0) / len(df) * 100, 1),
            "neutral": round(sentiment_dist.get('neutral', 0) / len(df) * 100, 1)
        }
        
        return {
            "overall_score": overall_score,
            "theme_scores": theme_scores,
            "sentiment_pct": sentiment_pct,
            "avg_rating": round(df['rating'].mean(), 2),
            "total_reviews": len(df)
        }
    
    def _extract_pain_points(self, negative_reviews: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract specific pain points from negative reviews"""
        pain_keywords = {
            "crashes": ["crash", "crashes", "crashing", "force close", "freezes"],
            "slow_performance": ["slow", "lag", "laggy", "sluggish", "hangs"],
            "login_issues": ["can't login", "cant login", "login fail", "authentication"],
            "too_many_ads": ["too many ads", "ads everywhere", "spam", "popup"],
            "expensive": ["expensive", "too much money", "price", "cost too much"],
            "battery_drain": ["battery drain", "drains battery", "kills battery"],
            "bugs": ["bug", "buggy", "broken", "doesn't work", "not working"],
            "poor_ui": ["confusing", "hard to use", "bad ui", "ugly design"]
        }
        
        pain_points = []
        for pain_type, keywords in pain_keywords.items():
            count = 0
            examples = []
            
            for _, row in negative_reviews.iterrows():
                text = str(row['review_text']).lower()
                if any(kw in text for kw in keywords):
                    count += 1
                    if len(examples) < 2:
                        examples.append(row['review_text'][:100] + "...")
            
            if count > 0:
                pain_points.append({
                    "pain_point": pain_type.replace("_", " ").title(),
                    "mention_count": count,
                    "examples": examples
                })
        
        return sorted(pain_points, key=lambda x: x['mention_count'], reverse=True)[:5]
    
    def _detect_emerging_issues(self, df: pd.DataFrame, time_window_days: int) -> List[Dict[str, Any]]:
        """Detect issues that are spiking recently"""
        if 'date' not in df.columns or len(df) < 20:
            return []
        
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # Split into recent vs older
        mid_point = datetime.now() - timedelta(days=time_window_days // 2)
        recent = df[df['date'] >= mid_point]
        older = df[df['date'] < mid_point]
        
        if len(recent) < 5 or len(older) < 5:
            return []
        
        emerging = []
        for theme in df['theme_title'].unique():
            recent_neg = ((recent['theme_title'] == theme) & (recent['sentiment'] == 'negative')).sum()
            older_neg = ((older['theme_title'] == theme) & (older['sentiment'] == 'negative')).sum()
            
            recent_total = (recent['theme_title'] == theme).sum()
            older_total = (older['theme_title'] == theme).sum()
            
            if recent_total > 3 and older_total > 3:
                recent_pct = (recent_neg / recent_total) * 100 if recent_total > 0 else 0
                older_pct = (older_neg / older_total) * 100 if older_total > 0 else 0
                
                # Spike detected if recent complaints are 30%+ higher
                if recent_pct > older_pct + 30:
                    emerging.append({
                        "theme": theme,
                        "spike": f"+{round(recent_pct - older_pct, 1)}%",
                        "recent_complaints": int(recent_neg),
                        "status": "🚨 Spiking"
                    })
        
        return sorted(emerging, key=lambda x: float(x['spike'].replace('+', '').replace('%', '')), reverse=True)
    
    def _generate_opportunity_recommendations(
        self, 
        weaknesses: List[Dict], 
        pain_points: List[Dict]
    ) -> List[str]:
        """Generate actionable recommendations based on competitor weaknesses"""
        recommendations = []
        
        if weaknesses:
            top_weakness = weaknesses[0]
            recommendations.append(
                f"🎯 EXPLOIT: Competitor struggles with {top_weakness['theme']} "
                f"({top_weakness['negative_count']} complaints). Make this YOUR strength in marketing."
            )
        
        if len(weaknesses) >= 2:
            recommendations.append(
                f"💡 OPPORTUNITY: Build features addressing {weaknesses[0]['theme']} and "
                f"{weaknesses[1]['theme']} - both are competitor weak points."
            )
        
        if pain_points:
            top_pain = pain_points[0]
            recommendations.append(
                f"🔨 FIX THIS: Users complain about '{top_pain['pain_point']}' "
                f"({top_pain['mention_count']} times). Solve this better than them."
            )
        
        return recommendations
    
    def _generate_strategic_recommendations(
        self,
        advantages: List[Dict],
        weaknesses: List[Dict],
        gaps: List[Dict]
    ) -> List[str]:
        """Generate strategic recommendations for competitive positioning"""
        recommendations = []
        
        # Leverage advantages
        if advantages:
            top = advantages[0]
            recommendations.append(
                f"🏆 DOUBLE DOWN: You're {top['advantage_margin']}pts ahead on {top['theme']}. "
                f"Market this heavily!"
            )
        
        # Address critical weaknesses
        if weaknesses:
            critical = weaknesses[0]
            recommendations.append(
                f"⚠️ URGENT: Fix {critical['theme']} - you're {critical['gap']}pts behind competitor. "
                f"This is a competitive risk."
            )
        
        # Exploit market gaps
        if gaps:
            opportunity = gaps[0]
            recommendations.append(
                f"🎯 MARKET GAP: Both apps weak on {opportunity['theme']}. "
                f"Innovate here to capture unmet demand!"
            )
        
        # Strategic positioning
        if len(advantages) > len(weaknesses):
            recommendations.append(
                "💪 STRATEGY: You have more strengths than weaknesses. "
                "Focus on aggressive growth and marketing your differentiators."
            )
        elif len(weaknesses) > len(advantages):
            recommendations.append(
                "🔧 STRATEGY: Focus on product improvement first. "
                "Close the gap before investing heavily in marketing."
            )
        
        return recommendations
    
    def generate_competitive_report(
        self,
        comparison: Dict[str, Any],
        output_path: str = None
    ) -> str:
        """Generate a formatted competitive analysis report"""
        report_lines = []
        report_lines.append("=" * 100)
        report_lines.append("COMPETITIVE ANALYSIS REPORT")
        report_lines.append("=" * 100)
        report_lines.append(f"\n📊 {comparison['my_app']} vs {comparison['competitor']}")
        report_lines.append(f"Period: {comparison['analysis_period']}\n")
        
        # Overall comparison
        overall = comparison['overall_comparison']
        report_lines.append("OVERALL SCORE")
        report_lines.append("-" * 100)
        report_lines.append(f"Your Score:       {overall['your_score']}/100")
        report_lines.append(f"Competitor Score: {overall['competitor_score']}/100")
        report_lines.append(f"Verdict:          {overall['verdict']} (Gap: {overall['score_gap']} points)\n")
        
        # Your advantages
        if comparison['your_advantages']:
            report_lines.append("💪 YOUR COMPETITIVE ADVANTAGES")
            report_lines.append("-" * 100)
            for i, adv in enumerate(comparison['your_advantages'][:5], 1):
                report_lines.append(
                    f"{i}. {adv['theme']}: You're +{adv['advantage_margin']}pts ahead "
                    f"(You: {adv['your_score']}, Them: {adv['competitor_score']})"
                )
            report_lines.append("")
        
        # Your weaknesses
        if comparison['your_weaknesses']:
            report_lines.append("⚠️  YOUR WEAKNESSES VS COMPETITOR")
            report_lines.append("-" * 100)
            for i, weak in enumerate(comparison['your_weaknesses'][:5], 1):
                report_lines.append(
                    f"{i}. {weak['theme']}: You're -{weak['gap']}pts behind "
                    f"(You: {weak['your_score']}, Them: {weak['competitor_score']})"
                )
            report_lines.append("")
        
        # Market gaps
        if comparison['market_gaps']:
            report_lines.append("🎯 MARKET OPPORTUNITIES (Both Apps Weak)")
            report_lines.append("-" * 100)
            for i, gap in enumerate(comparison['market_gaps'][:3], 1):
                report_lines.append(
                    f"{i}. {gap['theme']} [{gap['priority']} PRIORITY]: "
                    f"You: {gap['your_score']}, Them: {gap['competitor_score']} - {gap['opportunity']}"
                )
            report_lines.append("")
        
        # Strategic recommendations
        report_lines.append("💡 STRATEGIC RECOMMENDATIONS")
        report_lines.append("-" * 100)
        for i, rec in enumerate(comparison['strategic_recommendations'], 1):
            report_lines.append(f"{i}. {rec}")
        report_lines.append("")
        
        report_lines.append("=" * 100)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 100)
        
        report = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report


# Helper function for easy use
def analyze_competitor(
    competitor_package_name: str,
    my_package_name: str = None,
    time_window_days: int = 90
) -> Dict[str, Any]:
    """
    Convenience function to analyze competitor
    
    Args:
        competitor_package_name: Google Play package name of competitor
        my_package_name: Your app's package name (optional, for comparison)
        time_window_days: Days of reviews to analyze
    
    Returns:
        Analysis results
    """
    from pipeline.playstore_fetcher import fetch_and_process_app_reviews
    import os
    
    # Fetch and process competitor reviews
    print(f"Fetching competitor reviews for {competitor_package_name}...")
    comp_result = fetch_and_process_app_reviews(
        package_name=competitor_package_name,
        use_transformer=True,
        enable_embeddings=False
    )
    
    analyzer = CompetitiveAnalyzer()
    
    # If my_package_name provided, do comparison
    if my_package_name:
        print(f"Fetching your app reviews for {my_package_name}...")
        my_result = fetch_and_process_app_reviews(
            package_name=my_package_name,
            use_transformer=True,
            enable_embeddings=False
        )
        
        comparison = analyzer.compare_apps(
            my_app_reviews=my_result['processed_reviews'],
            competitor_reviews=comp_result['processed_reviews'],
            my_app_name=my_package_name.split('.')[-1],
            competitor_name=competitor_package_name.split('.')[-1],
            time_window_days=time_window_days
        )
        
        # Generate report
        report = analyzer.generate_competitive_report(comparison)
        print("\n" + report)
        
        return comparison
    else:
        # Just analyze competitor weakness
        weakness_analysis = analyzer.analyze_competitor_weakness(
            competitor_reviews=comp_result['processed_reviews'],
            app_name=competitor_package_name.split('.')[-1],
            time_window_days=time_window_days
        )
        
        return weakness_analysis
