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
## Confidence Score (0.0-1.0)
How confident are you in this sentiment-based recommendation?

- 0.80-1.00: Very strong sentiment signal, multiple credible sources
- 0.65-0.79: Strong signal, good source quality
- 0.50-0.64: Moderate signal, mixed or aging news
- 0.35-0.49: Weak signal, conflicting data or questionable sources
- 0.00-0.34: No clear signal, noise only

## Confidence Reasoning (CRITICAL)
Write 2-3 sentences that paint the sentiment picture:

 **Must include**:
- CFGI score and what it means (e.g., "CFGI at 66 (Greed)")
- Specific news titles and dates (e.g., "Morgan Stanley ETF filing on Jan 6")
- Source credibility (e.g., "from reputable CoinDesk")
- How CFGI + news combine to create edge

**Natural storytelling** - connect the dots, don't just list
**No vague phrases** like "sentiment is positive"
**No listing** without context

**GOOD Examples**:

"High confidence (0.82) - CFGI at 72 (Greed) but justified by genuine catalysts: Morgan Stanley ETF filing (Jan 6, CoinDesk) and Ondo Finance tokenization partnership (Dec 24, official). Retail excitement backed by institutional validation creates strong bullish edge, though brief stablecoin depeg adds minor caution."

"Low confidence (0.38) despite CFGI showing Fear at 28 - all recent news is 5+ days old with no fresh catalysts. Whale accumulation mentioned on Jan 1 (Santiment) lacks volume confirmation from technicals. Sentiment signal exists but stale data means edge has likely faded."

"Strong confidence (0.78) in BEARISH call - CFGI hit Extreme Greed at 84 (contrarian sell signal) while key risk flag emerged: Solana network outage (2 hours on Dec 30, verified by official sources). Euphoric retail positioning into reliability concerns creates high-probability reversal setup."

**BAD Examples** :

"Bullish sentiment from positive news and good CFGI score"
→ No specifics, no dates, doesn't paint picture

"Confidence is high because multiple factors align"
→ Generic, could apply to anything

"News sentiment at 0.68 with CFGI showing greed"
→ Just stating data, not explaining WHY it matters
</confidence_guidelines>

### OUTPUT FORMAT:

After your thinking, output the final JSON inside <answer> tags. The JSON must follow this EXACT structure:

{{
    "recommendation_signal": "BUY|SELL|HOLD|WAIT",

    "market_condition": "BULLISH|BEARISH|NEUTRAL",

    "confidence": {{
        "score": 0.68,
        "reasoning": "Write 2-3 sentences: [CFGI interpretation] → [News analysis with specific titles/dates/sources] → [How they combine for overall edge]. Be specific and tell the story."
    }},

    "timestamp": "2026-01-06T12:34:56Z",

    "market_fear_greed": {{
        "score": {cfgi_score},
        "classification": "{cfgi_classification}",
        "social": {cfgi_social_raw},
        "whales": {cfgi_whales_raw},
        "trends": {cfgi_trends_raw},
        "sentiment": "BULLISH|BEARISH|NEUTRAL",
        "confidence": 0.75,
        "interpretation": "Your interpretation of what CFGI data means for trading"
    }},

    "news_sentiment": {{
        "sentiment": "BULLISH|BEARISH|NEUTRAL",
        "confidence": 0.65,
        "positive_catalysts": 3,
        "negative_risks": 1
    }},

    "combined_sentiment": {{
        "sentiment": "BULLISH|BEARISH|NEUTRAL",
        "confidence": 0.68
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

5. market_condition must be: BULLISH (optimistic sentiment), BEARISH (pessimistic sentiment), or NEUTRAL (unclear/mixed sentiment)

6. recommendation_signal must be: BUY (strong bullish + catalysts), SELL (strong bearish + risks), HOLD (moderate signal, no urgency), WAIT (conflicting or stale data)

7. confidence is simplified: {{score: 0.0-1.0, reasoning: "2-3 sentences with CFGI score, news titles/dates, source credibility"}}

8. fear_greed_index includes sentiment and confidence for CFGI analysis

9. news_sentiment includes sentiment and confidence for news analysis

10. combined_sentiment is the synthesis of CFGI + news (this should match market_condition)
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
            # Extract thinking
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            thinking = thinking_match.group(1).strip() if thinking_match else ""

            # Extract JSON from answer tags
            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            answer_json = answer_match.group(1).strip() if answer_match else response

            # Minimal JSON cleaning
            answer_json = re.sub(r'^```json\s*|\s*```$', '', answer_json.strip())
            answer_json = answer_json[answer_json.find('{'):answer_json.rfind('}')+1] if '{' in answer_json else answer_json

            # Parse and add thinking
            sentiment_data = json.loads(answer_json)
            if thinking:
                sentiment_data['thinking'] = thinking
            state['sentiment'] = sentiment_data

            dm.save_sentiment_analysis(sentiment_data)

        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            print(f"⚠️  Sentiment agent parsing error: {e}")
            print(f"Response: {response[:300]}")

            # Simplified fallback
            state['sentiment'] = {
                "recommendation_signal": "HOLD",
                "market_condition": "NEUTRAL",
                "confidence": {
                    "score": 0.3,
                    "reasoning": f"Sentiment analysis failed: {str(e)[:100]}. Defaulting to HOLD."
                },
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "market_fear_greed": {
                    "score": formatted_data["cfgi_score"],
                    "classification": formatted_data["cfgi_classification"],
                    "sentiment": "NEUTRAL",
                    "confidence": 0.5,
                    "interpretation": "Unable to analyze due to error"
                },
                "news_sentiment": {
                    "sentiment": "NEUTRAL",
                    "confidence": 0.5
                },
                "positive_catalysts": 0,
                "negative_risks": 0,
                "key_events": [],
                "risk_flags": ["Parsing error"],
                "what_to_watch": [],
                "invalidation": "N/A",
                "suggested_timeframe": "N/A",
                "thinking": f"Error: {str(e)}"
            }

        return state


if __name__ == "__main__":
    agent = SentimentAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== SENTIMENT AGENT OUTPUT =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
