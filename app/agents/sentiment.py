# sentiment.py

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager


SENTIMENT_SYSTEM_PROMPT = """You are a senior cryptocurrency sentiment analyst with 10 years of experience, specializing in Solana (SOL) for swing trading (3-10 day holds).

Your expertise:
- Interpreting Fear & Greed indices (contrarian approach: fear = buy, greed = sell)
- Identifying market-moving news vs noise/hype
- Assessing source credibility and news freshness
- Combining quantitative sentiment data with qualitative news analysis
- Providing actionable trading recommendations

Your analysis philosophy:
- Extreme fear often marks bottoms - contrarian buy opportunity
- Extreme greed often precedes corrections - time to take profits
- News older than 72 hours has diminishing impact
- Multiple reputable sources = higher confidence
- Security/regulatory news overrides all other signals
- Hype and speculation should be discounted heavily

You are skeptical, data-driven, and always consider "what could go wrong."
"""


SENTIMENT_PROMPT = """
<market_sentiment_data>
## CFGI Fear & Greed Index (Solana)
- Score: {cfgi_score}/100
- Classification: {cfgi_classification}
- Social Sentiment: {cfgi_social}/100
- Whale Activity: {cfgi_whales}/100
- Google Trends: {cfgi_trends}/100
- Data Age: {cfgi_age}
</market_sentiment_data>

<news_articles>
{news_data}
</news_articles>

---

<instructions>
## YOUR TASK

Analyse the sentiment data above using chain-of-thought reasoning. You MUST:

1. First, write your detailed reasoning inside <thinking> tags
2. Then, provide your final analysis as JSON inside <answer> tags

### THINKING PROCESS (inside <thinking> tags):

Work through these steps IN ORDER:

<thinking>
## STEP 1: CFGI INTERPRETATION (Contrarian Analysis)
- What does the Fear & Greed score tell us? (0-19 = extreme fear/buy, 80-100 = extreme greed/sell)
- Is social sentiment confirming or diverging from the main score?
- What does whale activity suggest? (high whale activity in fear = smart money accumulating)
- Are Google trends rising or falling? (rising trends in fear = potential reversal)
- Document your reasoning: [Write 2-3 sentences]

## STEP 2: NEWS CLASSIFICATION
For each significant news article, classify:
- Type: PARTNERSHIP | UPGRADE | SECURITY | REGULATORY | ECOSYSTEM | HYPE
- Impact: BULLISH | BEARISH | NEUTRAL
- Source Credibility: OFFICIAL | REPUTABLE | QUESTIONABLE
- News Age: How many hours old? (>72h = reduced weight)
- Is this ACTIONABLE (price-moving) or just NOISE?
- Document your reasoning: [Write 2-3 sentences]

## STEP 3: RISK ASSESSMENT
Scan for RED FLAGS:
- Security issues (hacks, exploits, network outages)
- Regulatory threats (SEC, lawsuits, delistings)
- Team/foundation problems
- Network instability
- If ANY critical risk found, it overrides positive signals
- Document your reasoning: [Write 2-3 sentences]

## STEP 4: SENTIMENT SYNTHESIS
Combine CFGI + News:
- Does news sentiment CONFIRM or CONTRADICT the CFGI signal?
- If CFGI shows fear but news is positive = STRONG BUY signal
- If CFGI shows greed but news is negative = STRONG SELL signal
- If both align = higher confidence
- If they conflict = lower confidence, be cautious
- Document your reasoning: [Write 2-3 sentences]

## STEP 5: FINAL RECOMMENDATION
Based on all analysis:
- What is the overall sentiment signal?
- What is the actionable recommendation_signal? (BUY if bullish sentiment, SELL if bearish, HOLD if neutral with no clear direction, WAIT if conflicting signals)
- What confidence level (consider conflicting signals)?
- What specific action should a swing trader take?
- What would invalidate this analysis?
- Document your reasoning: [Write 2-3 sentences]

### CONFIDENCE GUIDELINES:

<confidence_guidelines>
## Analysis Confidence (0.70-0.95)
How confident are you in this SENTIMENT ANALYSIS?

- 0.90-0.95: Multiple reliable sources confirm, clear consensus
- 0.80-0.89: Good source quality, minor conflicts
- 0.70-0.79: Reasonable sources, some ambiguity

NOTE: Even a NEUTRAL signal should have HIGH analysis_confidence if you're confident sentiment is neutral!

## Signal Strength (0.0-1.0)
How strong is the DIRECTIONAL SIGNAL?

- 0.80-1.00: Very strong bullish/bearish signal, multiple catalysts
- 0.60-0.79: Strong signal, good catalysts
- 0.40-0.59: Moderate signal, mixed catalysts
- 0.20-0.39: Weak signal, few catalysts or conflicts
- 0.00-0.19: No clear signal, neutral

CRITICAL RULES:
- If signal is NEUTRAL → signal_strength should be ≤ 0.35
- If major risk flags present → signal_strength should be ≤ 0.45
- If CFGI extreme (>80 or <20) → contrarian signal should have high strength (≥0.70)
- If news is >72h old → signal_strength penalty

## Interpretation
Combine both into a short sentence:
- "High confidence in analysis, strong bullish signal from RWA catalysts"
- "Very confident sentiment is neutral - mixed news with no clear direction"
- "Clear bearish analysis from regulatory concerns"
</confidence_guidelines>

### OUTPUT FORMAT:

After your thinking, output the final JSON inside <answer> tags. The JSON must follow this EXACT structure:

{{
    "signal": "BULLISH",

    "recommendation_signal": "BUY|SELL|HOLD|WAIT",

    "confidence": {{
        "analysis_confidence": 0.85,
        "signal_strength": 0.72,
        "interpretation": "High confidence in analysis, strong bullish signal"
    }},

    "market_fear_greed": {{
        "score": {cfgi_score},
        "classification": "{cfgi_classification}",
        "social": {cfgi_social_raw},
        "whales": {cfgi_whales_raw},
        "trends": {cfgi_trends_raw},
        "interpretation": "Your interpretation of what CFGI data means for trading"
    }},

    "news_sentiment": {{
        "score": 0.68,
        "label": "CAUTIOUSLY_BULLISH",
        "catalysts_count": 3,
        "risks_count": 1
    }},

    "key_events": [
        {{
            "title": "Event title from news",
            "type": "PARTNERSHIP",
            "impact": "BULLISH",
            "source": "CoinDesk",
            "url": "https://...",
            "published_at": "2025-12-30"
        }}
    ],

    "risk_flags": [
        "Any identified risks"
    ],

    "summary": "2-4 sentence combined analysis of CFGI and news",

    "what_to_watch": [
        "Item to monitor 1",
        "Item to monitor 2"
    ],

    "invalidation": "What would flip this analysis bearish/bullish",

    "suggested_timeframe": "3-5 days"
}}

IMPORTANT NOTES:
- Write your full reasoning in <thinking> tags FIRST
- Then output ONLY valid JSON in <answer> tags
- All numeric values should be numbers, not strings
- Confidence is now a nested object with analysis_confidence, signal_strength, and interpretation
</instructions>

---

<critical_rules>
1. CFGI score interpretation (CONTRARIAN approach):
   - 0-19: EXTREME FEAR → Strong buy opportunity
   - 20-39: FEAR → Accumulation zone
   - 40-59: NEUTRAL → No clear bias
   - 60-79: GREED → Take profits
   - 80-100: EXTREME GREED → Strong sell signal

2. News age matters:
   - <24 hours: Full weight
   - 24-48 hours: 75% weight
   - 48-72 hours: 50% weight
   - >72 hours: 25% weight

3. Security/Regulatory news OVERRIDES everything

4. key_events: Include 3-5 MOST IMPORTANT events only, with URLs

5. summary: Must be 2-4 sentences covering overall sentiment and key catalyst

6. Valid signal values: STRONG_BULLISH, BULLISH, SLIGHTLY_BULLISH, NEUTRAL, SLIGHTLY_BEARISH, BEARISH, STRONG_BEARISH

7. recommendation_signal: Must be BUY, SELL, HOLD, or WAIT (actionable trading recommendation derived from the sentiment signal)

8. Confidence is a nested object:
   - analysis_confidence: 0.70-0.95 (how sure are you in the analysis)
   - signal_strength: 0.0-1.0 (how strong is the directional signal)
   - interpretation: Short sentence explaining both
</critical_rules>
"""


def format_for_sentiment_agent(cfgi_data: dict, news_articles: list) -> dict:
    cfgi_score = cfgi_data.get("score", 50) if cfgi_data else 50
    cfgi_classification = cfgi_data.get("classification", "Neutral") if cfgi_data else "Neutral"
    cfgi_social = cfgi_data.get("social") if cfgi_data else None
    cfgi_whales = cfgi_data.get("whales") if cfgi_data else None
    cfgi_trends = cfgi_data.get("trends") if cfgi_data else None

    cfgi_age = "No data"
    if cfgi_data and cfgi_data.get("fetched_at"):
        try:
            fetched_str = cfgi_data["fetched_at"]
            if isinstance(fetched_str, str):
                fetched = datetime.fromisoformat(fetched_str.replace("Z", "+00:00"))
            else:
                fetched = fetched_str.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
            cfgi_age = f"{age_hours:.1f} hours ago"
        except:
            cfgi_age = "Unknown"

    # Format news articles
    if news_articles:
        news_lines = []
        for i, article in enumerate(news_articles[:15], 1):
            pub_date = article.get("published_at", "Unknown date")
            if hasattr(pub_date, "strftime"):
                pub_date = pub_date.strftime("%Y-%m-%d %H:%M")
            elif hasattr(pub_date, "isoformat"):
                pub_date = pub_date.isoformat()[:16]

            content_preview = article.get("content", "")
            if content_preview:
                content_preview = content_preview[:200] + "..."

            news_lines.append(
                f"{i}. [{article.get('source', 'Unknown')}] {article.get('title', 'Untitled')}\n"
                f"   Published: {pub_date}\n"
                f"   Priority: {article.get('priority', 'MEDIUM')}\n"
                f"   URL: {article.get('url', 'N/A')}\n"
                f"   Preview: {content_preview}"
            )
        news_data = "\n\n".join(news_lines)
    else:
        news_data = "No recent Solana news articles available."

    return {
        "cfgi_score": cfgi_score,
        "cfgi_classification": cfgi_classification,
        "cfgi_social": cfgi_social if cfgi_social else "N/A",
        "cfgi_whales": cfgi_whales if cfgi_whales else "N/A",
        "cfgi_trends": cfgi_trends if cfgi_trends else "N/A",
        "cfgi_social_raw": cfgi_social if cfgi_social else "null",
        "cfgi_whales_raw": cfgi_whales if cfgi_whales else "null",
        "cfgi_trends_raw": cfgi_trends if cfgi_trends else "null",
        "cfgi_age": cfgi_age,
        "news_data": news_data,
        "news_count": len(news_articles) if news_articles else 0
    }


class SentimentAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022", 
            temperature=0.3
        )

    def execute(self, state: AgentState) -> AgentState:
        dq = DataQuery()
        news_articles = dq.get_news_data(days=10)

        dm = DataManager()
        cfgi_data = dm.get_cfgi_with_cache()

        formatted_data = format_for_sentiment_agent(cfgi_data, news_articles)

        full_prompt = SENTIMENT_SYSTEM_PROMPT + "\n\n" + SENTIMENT_PROMPT.format(**formatted_data)

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=2500
        )

        try:
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            thinking = thinking_match.group(1).strip() if thinking_match else ""

            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            if answer_match:
                answer_json = answer_match.group(1).strip()
            else:
                answer_json = response

            answer_json = re.sub(r'```json\s*|\s*```', '', answer_json).strip()
            answer_json = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', answer_json)

            sentiment_data = json.loads(answer_json)


            # confidence = sentiment_data.get('confidence', {})
            # if isinstance(confidence, (int, float)):
            #     confidence = {
            #         'analysis_confidence': 0.75,
            #         'signal_strength': float(confidence),
            #         'interpretation': f'Legacy format: {confidence:.0%} confidence'
            #     }
            # elif not isinstance(confidence, dict):
            #     # Fallback for invalid format
            #     confidence = {
            #         'analysis_confidence': 0.5,
            #         'signal_strength': 0.5,
            #         'interpretation': 'Default confidence'
            #     }
            # sentiment_data['confidence'] = confidence

            if thinking:
                sentiment_data['thinking'] = thinking
            state['sentiment'] = sentiment_data

            dm.save_sentiment_analysis(sentiment_data)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Sentiment agent parsing error: {e}")
            print(f"Response: {response[:300]}")
            # Fallback to neutral sentiment
            state['sentiment'] = {
                "signal": "NEUTRAL",
                "recommendation_signal": "HOLD",
                "confidence": {
                    "analysis_confidence": 0.5,
                    "signal_strength": 0.3,
                    "interpretation": f"Analysis error: {str(e)[:50]}"
                },
                "market_fear_greed": {
                    "score": formatted_data["cfgi_score"],
                    "classification": formatted_data["cfgi_classification"],
                    "social": None,
                    "whales": None,
                    "trends": None,
                    "interpretation": "Unable to analyze CFGI data"
                },
                "news_sentiment": {
                    "score": 0.5,
                    "label": "NEUTRAL",
                    "catalysts_count": 0,
                    "risks_count": 0
                },
                "key_events": [],
                "risk_flags": ["parsing_error"],
                "summary": f"Analysis parsing error: {str(e)[:100]}",
                "what_to_watch": [],
                "invalidation": "N/A",
                "suggested_timeframe": "N/A",
                "thinking": ""
            }

        return state


if __name__ == "__main__":
    agent = SentimentAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== SENTIMENT AGENT OUTPUT =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
