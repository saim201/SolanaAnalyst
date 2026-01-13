# sentiment.py - Optimised for Claude Haiku 4.5

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from typing import Dict

from anthropic import Anthropic

from app.agents.base import BaseAgent, AgentState
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager




SENTIMENT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation_signal": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD", "WAIT"],
            "description": "Primary trading recommendation"
        },
        "market_condition": {
            "type": "string",
            "enum": ["BULLISH", "BEARISH", "NEUTRAL"],
            "description": "Overall market sentiment"
        },
        "confidence": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": "Confidence level 0.0-1.0"
                },
                "reasoning": {
                    "type": "string",
                    "description": "2-3 sentences with CFGI score, news titles/dates, sources"
                }
            },
            "required": ["score", "reasoning"],
            "additionalProperties": False
        },
        "thinking": {
            "type": "string",
            "description": "Chain-of-thought reasoning process"
        },
        "market_fear_greed": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "classification": {"type": "string"},
                "social": {"type": ["number", "null"]},
                "whales": {"type": ["number", "null"]},
                "trends": {"type": ["number", "null"]},
                "sentiment": {
                    "type": "string",
                    "enum": ["BULLISH", "BEARISH", "NEUTRAL"]
                },
                "confidence": {"type": "number"},
                "interpretation": {"type": "string"}
            },
            "required": ["score", "classification", "sentiment", "confidence", "interpretation"],
            "additionalProperties": False
        },
        "news_sentiment": {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["BULLISH", "BEARISH", "NEUTRAL"]
                },
                "confidence": {"type": "number"}
            },
            "required": ["sentiment", "confidence"],
            "additionalProperties": False
        },
        "combined_sentiment": {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["BULLISH", "BEARISH", "NEUTRAL"]
                },
                "confidence": {"type": "number"}
            },
            "required": ["sentiment", "confidence"],
            "additionalProperties": False
        },
        "key_events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["PARTNERSHIP", "UPGRADE", "SECURITY", "REGULATORY", "ECOSYSTEM", "HYPE"]
                    },
                    "impact": {
                        "type": "string",
                        "enum": ["BULLISH", "BEARISH", "NEUTRAL"]
                    },
                    "source": {"type": "string"},
                    "url": {"type": "string"},
                    "published_at": {"type": "string"}
                },
                "required": ["title", "type", "impact", "source", "url", "published_at"],
                "additionalProperties": False
            }
        },
        "risk_flags": {
            "type": "array",
            "items": {"type": "string"}
        },
        "what_to_watch": {
            "type": "array",
            "items": {"type": "string"}
        },
        "invalidation": {
            "type": "string",
            "description": "What would flip this analysis"
        },
        "suggested_timeframe": {
            "type": "string",
            "description": "Recommended holding period"
        }
    },
    "required": [
        "recommendation_signal",
        "market_condition",
        "confidence",
        "thinking",
        "market_fear_greed",
        "news_sentiment",
        "combined_sentiment",
        "key_events",
        "risk_flags",
        "what_to_watch",
        "invalidation",
        "suggested_timeframe"
    ],
    "additionalProperties": False
}


SENTIMENT_SYSTEM_PROMPT = """You are a senior cryptocurrency sentiment analyst with 10 years of experience, specializing in Solana (SOL) swing trading (3-10 day holds).

CORE PHILOSOPHY:
- Contrarian approach: extreme fear = buy opportunity, extreme greed = take profits
- Security/regulatory news overrides all other signals
- News older than 72 hours has diminishing impact
- Multiple reputable sources = higher confidence
- Discount hype and speculation heavily

CFGI INTERPRETATION (0-100):
- 0-19: EXTREME FEAR → Strong buy (contrarian)
- 20-39: FEAR → Accumulation zone
- 40-59: NEUTRAL → No clear bias
- 60-79: GREED → Take profits
- 80-100: EXTREME GREED → Strong sell (contrarian)

You are skeptical, data-driven, and always consider "what could go wrong."
"""



SENTIMENT_PROMPT = """
<market_sentiment_data>
## CFGI Fear & Greed Index (Solana)
Score: {cfgi_score}/100 ({cfgi_classification})
Social: {cfgi_social}/100 | Whales: {cfgi_whales}/100 | Trends: {cfgi_trends}/100
Data Age: {cfgi_age}
</market_sentiment_data>

<news_articles>
{news_data}
</news_articles>

---

<instructions>
Analyse sentiment data thoroughly. Consider CFGI score (contrarian), news impact and credibility, security/regulatory risks, and how they combine.

First, write your reasoning inside <thinking> tags covering:
- CFGI interpretation (what does {cfgi_score} mean? social/whale/trends alignment?)
- News classification (PARTNERSHIP, SECURITY, REGULATORY, etc. + impact + credibility + age)
- Critical risks (security issues, regulatory threats - these override positive signals)
- Sentiment synthesis (does news confirm or contradict CFGI? conflicts = lower confidence)
- Final recommendation (BUY if bullish + catalysts, SELL if bearish + risks, HOLD if moderate, WAIT if conflicting/stale)

Then output JSON inside <answer> tags.

CRITICAL RULES:
- News age weighting: <24h=100%, 24-48h=75%, 48-72h=50%, >72h=25%
- Security/Regulatory news OVERRIDES everything
- Include 3-5 MOST IMPORTANT events only in key_events
- Confidence reasoning: Include CFGI score, specific news titles/dates, source names

CONFIDENCE SCALE:
- 0.80-1.00: Very strong signal, multiple credible sources
- 0.65-0.79: Strong signal, good quality
- 0.50-0.64: Moderate signal, mixed/aging news
- 0.35-0.49: Weak signal, conflicting data
- 0.00-0.34: No clear signal, noise only

Output valid JSON matching the schema exactly.
</instructions>
"""



def format_for_sentiment_agent(cfgi_data: dict, news_articles: list) -> dict:
    cfgi_score = cfgi_data.get("score", 50) if cfgi_data else 50
    cfgi_classification = cfgi_data.get("classification", "Neutral") if cfgi_data else "Neutral"
    cfgi_social = cfgi_data.get("social") if cfgi_data else None
    cfgi_whales = cfgi_data.get("whales") if cfgi_data else None
    cfgi_trends = cfgi_data.get("trends") if cfgi_data else None

    # Calculate CFGI data age
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

    # Format news articles concisely
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
                f"   Published: {pub_date} | Priority: {article.get('priority', 'MEDIUM')}\n"
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
        "cfgi_age": cfgi_age,
        "news_data": news_data,
        "news_count": len(news_articles) if news_articles else 0
    }


class SentimentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-haiku-4-5-20251001",
            temperature=0.3
        )
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def execute(self, state: AgentState) -> AgentState:

        # Step 1: Fetch data from DB
        with DataQuery() as dq:
            news_articles = dq.get_news_data(days=10)

        with DataManager() as dm:
            cfgi_data = dm.get_cfgi_with_cache()

        # Step 2: Format and make API call (no DB connection held)
        formatted_data = format_for_sentiment_agent(cfgi_data, news_articles)

        full_prompt = SENTIMENT_SYSTEM_PROMPT + "\n\n" + SENTIMENT_PROMPT.format(**formatted_data)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2500,
            temperature=self.temperature,
            messages=[{"role": "user", "content": full_prompt}],
            extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
            extra_body={
                "output_format": {
                    "type": "json_schema",
                    "schema": SENTIMENT_ANALYSIS_SCHEMA
                }
            }
        )

        response_text = response.content[0].text

        answer_match = re.search(r'<answer>(.*?)</answer>', response_text, re.DOTALL)
        if answer_match:
            json_text = answer_match.group(1).strip()
        else:
            json_text = response_text

        json_text = re.sub(r'^```json\s*|\s*```$', '', json_text.strip())

        sentiment_data = json.loads(json_text)

        sentiment_data['timestamp'] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        state['sentiment'] = sentiment_data

        # Step 3: Save result to DB
        with DataManager() as dm:
            dm.save_sentiment_analysis(sentiment_data)

        return state


if __name__ == "__main__":
    agent = SentimentAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== SENTIMENT AGENT OUTPUT =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
