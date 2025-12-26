

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager


SYSTEM_PROMPT = """You are a veteran crypto news analyst specializing in SOLANA (SOL) cryptocurrency with 10 years of experience separating signal from noise.

Your expertise:
- Distinguishing real catalysts from hype
- Identifying regulatory risks and security threats
- Recognizing meaningful partnerships vs marketing fluff
- Assessing news credibility based on source quality

CRITICAL: You analyze news for SOLANA (SOL) swing trading (3-7 day holds).
Your job: Tell traders if news adds confidence to their trades or raises red flags.

Your analysis style: Skeptical, fact-based, focused on "does this news matter for SOL price?"
"""


NEWS_PROMPT = """
<news_articles>
{news_data}
</news_articles>

<analysis_framework>
YOUR RESPONSE MUST USE THIS EXACT FORMAT:


<thinking>

PHASE 1: IDENTIFY KEY EVENTS
Read through all articles and pick out 3-5 MOST IMPORTANT events.
For each event, classify it:
- PARTNERSHIP: New integrations, collaborations, institutional adoption
- UPGRADE: Protocol improvements, network updates
- SECURITY: Hacks, vulnerabilities, network outages
- REGULATORY: SEC actions, government policy, exchange listings/delistings
- ECOSYSTEM: DeFi growth, NFT activity, developer milestones
- HYPE: Speculation, influencer tweets, no real substance
Ask yourself: "Is this ACTIONABLE (will move price) or just NOISE?"


PHASE 2: ASSESS SOURCE CREDIBILITY
For the key events you identified, check the source:
- OFFICIAL: Solana Foundation, Solana Status, major exchanges (Binance, Coinbase)
- REPUTABLE: CoinDesk, CoinTelegraph, Decrypt
- QUESTIONABLE: Unknown blogs, unverified sources
If multiple reputable sources report the same event → High confidence
If only 1 questionable source → Flag as "unverified"


PHASE 3: CHECK FOR RISKS
Look for RED FLAGS that could hurt SOL price:
- Security breaches (hacks, exploits, network down)
- Regulatory threats (SEC lawsuit, exchange delisting)
- Team issues (founder exits, scandals)
- Network problems (major outage, validator issues)
If you find any critical risks, note them clearly.


PHASE 4: DETERMINE OVERALL SENTIMENT
Based on the events above:
- Are positive events (partnerships, upgrades) outweighing negative ones?
- Is the sentiment BULLISH (confident buying), NEUTRAL (wait and see), or BEARISH (caution/sell)?
- How confident are you? (0.0 to 1.0)
Consider:
- If most news is hype/speculation → Lower confidence
- If news is stale (>3 days old) → Lower confidence
- If sources are questionable → Lower confidence
- If critical risks present → Confidence <0.5


</thinking>



<answer>
Provide your trading recommendation in this EXACT JSON format:

{{
  "overall_sentiment": 0.65,
  "sentiment_label": "NEUTRAL-BULLISH",
  "confidence": 0.70,

  "all_recent_news": [
    {{
      "title": "Full article title",
      "published_at": "2025-12-15T10:30:00",
      "url": "https://coindesk.com/article-url",
      "source": "CoinDesk"
    }}
  ],

  "key_events": [
    {{
      "title": "Visa partners with Solana for stablecoin payments",
      "published_at": 2025-12-02 03:36:29.000,
      "url": "source_url",
      "type": "PARTNERSHIP",
      "source_credibility": "REPUTABLE",
      "news_age_hours": 18,
      "impact": "BULLISH",
      "reasoning": "Major institutional validation, could drive real usage"
    }},
    {{
      "title": "Solana network experienced 2-hour slowdown",
      "published_at": 2025-12-02 03:36:29.000,
      "url": "https://coindesk.com/visa-solana-partnership",
      "type": "SECURITY",
      "source_credibility": "OFFICIAL",
      "news_age_hours": 48,
      "impact": "BEARISH",
      "reasoning": "Network reliability concerns, but short duration"
    }},
    {{
      "title": "Random influencer predicts SOL to $500",
      "published_at": 2025-12-02 03:36:29.000,
      "url": "https://status.solana.com/incident-123",
      "type": "HYPE",
      "source_credibility": "QUESTIONABLE",
      "news_age_hours": 12,
      "impact": "NEUTRAL",
      "reasoning": "Baseless speculation, ignore"
    }}
  ],

  "event_summary": {{
    "actionable_catalysts": 2,
    "hype_noise": 3,
    "critical_risks": 1
  }},

  "risk_flags": [
    "Network slowdown reported (2 hours, now resolved)"
  ],

  "stance": "News is cautiously bullish. Visa partnership is a strong positive catalyst, but recent network issues create some concern. Overall, news SUPPORTS taking long positions but with reduced position size due to reliability questions.",

  "suggested_timeframe": "3-5 days (watch for Visa announcement details)",

  "recommendation_summary": "News is cautiously bullish with 68% sentiment. Visa partnership (confirmed, launching Q1 2025) provides strong institutional validation, but recent network slowdown raises reliability concerns. Overall, news SUPPORTS long positions but suggests reduced size. Watch for Visa launch date and any further network issues. Invalidation: Network outage or partnership delay flips sentiment bearish."

  "what_to_watch": [
    "Official Visa partnership launch date",
    "Any further network stability issues",
    "Follow-up news on partnership implementation"
  ],

  "invalidation": "If network experiences another outage OR Visa partnership gets delayed/cancelled, turn bearish immediately."
}}
</answer>

Do NOT write ANYTHING before the <thinking> tag or after the </answer> tag. Do NOT forget write open and close tags properly  

</analysis_framework>

<critical_rules>
1. Only analyze the provided articles - do not make up events
2. If news is mostly hype/speculation, say so clearly
3. If you're uncertain about something, state "Unverified" rather than guessing
4. Critical risks (security, regulatory) automatically reduce confidence below 0.5
5. Old news (>72 hours) matters less - adjust impact accordingly
6. Multiple reputable sources reporting same event = higher confidence
7. Focus on Solana-specific news - ignore generic crypto market chatter
8. Be skeptical of hype - only material catalysts matter
9. recommendation_summary MUST be 2-4 sentences: (a) sentiment score + label, (b) key catalyst, (c) what news means for trading, (d) what to watch, (e) invalidation trigger
</critical_rules>

"""




class NewsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.3
        )

    def execute(self, state: AgentState) -> AgentState:
        with DataQuery() as dq:
            news_data = dq.get_news_data(days=10)

        articles_count = len(news_data)

        if articles_count > 0:
            articles_text = "\n\n".join([
                f"[{i+1}] {article['title']}\n"
                f"Published_at: {article['published_at']}\n"
                f"URL: {article['url']} \n"
                f"Source: {article['source']} \n"
                f"Summary: {article.get('description', 'No summary available')[:200]}..."
                for i, article in enumerate(news_data)
            ])
        else:
            articles_text = "No recent news articles found."

        # Handle no news scenario
        if articles_count == 0:
            state['news'] = {
                "overall_sentiment": 0.5,
                "sentiment_trend": "stable",
                "sentiment_breakdown": {
                    "regulatory": 0.5,
                    "partnership": 0.5,
                    "upgrade": 0.5,
                    "security": 0.5,
                    "macro": 0.5
                },
                "critical_events": [],
                "event_classification": {
                    "actionable_catalysts": 0,
                    "noise_hype": 0,
                    "risk_flags": 0
                },
                "recommendation": "NEUTRAL",
                "confidence": 0.3,
                "hold_duration": "N/A",
                "reasoning": "No recent news available for analysis (last 7 days)",
                "risk_flags": [],
                "time_sensitive_events": [],
                "thinking": ""  
            }

            return state

        news_summary = f"Total Articles: {articles_count}\n\n{articles_text}"

        full_prompt = SYSTEM_PROMPT + "\n\n" + NEWS_PROMPT.format(news_data=news_summary)

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

            news_data = json.loads(answer_json)

            if thinking:
                news_data['thinking'] = thinking
            news_data['timestamp'] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            state['news'] = news_data

            with DataManager() as dm:
                dm.save_news_analysis(news_data)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  News agent parsing error: {e}")
            print(f"Response: {response[:300]}")
            state['news'] = {
                "overall_sentiment": 0.5,
                "sentiment_trend": "stable",
                "sentiment_breakdown": {
                    "regulatory": 0.5,
                    "partnership": 0.5,
                    "upgrade": 0.5,
                    "security": 0.5,
                    "macro": 0.5
                },
                "critical_events": [],
                "event_classification": {
                    "actionable_catalysts": 0,
                    "noise_hype": 0,
                    "risk_flags": 0
                },
                "recommendation": "NEUTRAL",
                "confidence": 0.3,
                "hold_duration": "N/A",
                "reasoning": f"Analysis parsing error: {str(e)[:100]}",
                "risk_flags": ["parsing_error"],
                "time_sensitive_events": [],
                "thinking": ""  # Fixed: Added missing field
            }

        return state


if __name__ == "__main__":
    agent = NewsAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== NEWS AGENT OUTPUT =====")
    analysis = result.get('news', {})  
    print("\n\n --- news_analyst: \n", analysis)
