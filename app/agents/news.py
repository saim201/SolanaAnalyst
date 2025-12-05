"""
News Agent - Analyzes news sentiment with event classification.
Categorizes events to identify actionable catalysts vs noise.
Uses structured 5-step analysis framework 
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.agents.formatter import LLMDataFormatter


SYSTEM_PROMPT = """You are a veteran crypto news analyst with 10 years of experience separating signal from noise in the cryptocurrency market. You worked as a hedge fund analyst covering blockchain events and regulatory developments.

Your expertise:
- Distinguishing hype from material catalysts
- Identifying regulatory risk early
- Recognizing partnership/upgrade announcements with real impact
- Detecting FUD campaigns and manipulation attempts
- Understanding macro correlation (crypto follows risk-on/risk-off cycles)

Your analysis style is skeptical, fact-based, and focused on "will this move the price in 3-7 days?"
"""


NEWS_PROMPT = """
RECENT NEWS ARTICLES (last 7 days):
{news_data}

<analysis_framework>
You MUST analyse news in this EXACT order:

<thinking>
STEP 1: EVENT CLASSIFICATION
For each article, classify the event type:
- REGULATORY: SEC actions, government policy, legal developments
- PARTNERSHIP: New integrations, collaborations, ecosystem growth
- UPGRADE: Protocol upgrades, new features, technical improvements
- SECURITY: Hacks, exploits, vulnerabilities, audits
- MACRO: Federal Reserve, inflation, risk-on/risk-off, Bitcoin correlation
- HYPE: Influencer tweets, speculation, no material substance

Identify which events are ACTIONABLE (likely to move price) vs NOISE.
Document: [List 3-5 key events with classifications]

STEP 2: SENTIMENT SCORING
- What's the overall tone? (bullish, neutral, bearish)
- Is sentiment improving, stable, or declining vs last week?
- Are positive events outweighing negative events?
- Is there FUD (fear, uncertainty, doubt) being spread?
Document: [Write 2-3 sentences]

STEP 3: CATALYST IDENTIFICATION
- Are there any near-term catalysts (next 3-7 days)?
- Examples: Upcoming upgrade launch, pending regulatory decision, partnership announcement
- Will these catalysts drive REAL volume or just hype?
Document: [List specific catalysts with expected timing]

STEP 4: RISK FLAG DETECTION
Check for RED FLAGS:
- Regulatory crackdown (SEC lawsuit, exchange delisting threats)
- Security breach (protocol hack, smart contract exploit)
- Team/founder drama (exits, scandals, investigations)
- Exchange issues (liquidity problems, withdrawal delays)
Document: [List any critical risk flags]

STEP 5: FINAL SENTIMENT ASSESSMENT
- Given ALL news above, what's your overall sentiment? (0.0 = extremely bearish, 0.5 = neutral, 1.0 = extremely bullish)
- How confident are you in this sentiment? (0.0 to 1.0)
- Should traders be BULLISH, NEUTRAL, or BEARISH based on news alone?
</thinking>

<answer>
Based on the above 5-step analysis, provide your news sentiment assessment in this EXACT JSON format:

{{
  "overall_sentiment": 0.65,
  "sentiment_trend": "improving",
  "sentiment_breakdown": {{
    "regulatory": 0.7,
    "partnership": 0.8,
    "upgrade": 0.6,
    "security": 0.9,
    "macro": 0.5
  }},
  "critical_events": [
    "Solana DeFi TVL hits $5B (bullish - ecosystem growth)",
    "SEC approves Bitcoin ETF (bullish macro - risk-on sentiment)",
    "Minor Solana validator bug patched (neutral - no exploits)"
  ],
  "event_classification": {{
    "actionable_catalysts": 2,
    "noise_hype": 3,
    "risk_flags": 0
  }},
  "recommendation": "BULLISH",
  "confidence": 0.70,
  "hold_duration": "5-7 days (wait for ecosystem growth to reflect in price)",
  "reasoning": "Strong ecosystem growth with DeFi TVL hitting $5B and new partnership announcements. Positive macro tailwind from Bitcoin ETF approval creating risk-on sentiment. No major regulatory or security concerns.",
  "risk_flags": [],
  "time_sensitive_events": [
    "Solana Mobile Chapter 2 launch (May 15th) - expect hype spike"
  ]
}}
</answer>
</analysis_framework>

CRITICAL RULES:
1. overall_sentiment must be 0.0 to 1.0 (0.0 = bearish, 0.5 = neutral, 1.0 = bullish)
2. If you find ANY critical risk flags (security breach, regulatory action), set confidence < 0.5
3. "Hype" events (influencer tweets, speculation) should NOT heavily influence sentiment
4. If no news or all noise, return sentiment=0.5 (neutral) and confidence=0.3
5. time_sensitive_events should only include events with SPECIFIC DATES in next 7 days
6. Do not hallucinate events - only analyse provided articles
"""


class NewsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.3
        )

    def execute(self, state: AgentState) -> AgentState:
        llm_data = LLMDataFormatter.format_for_news_agent()

        articles = llm_data.get("articles", [])
        articles_count = llm_data.get("articles_count", 0)

        # Handle no news scenario
        if articles_count == 0:
            state['news_analysis'] = json.dumps({
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
                "time_sensitive_events": []
            })
            return state

        # Format articles for LLM
        articles_text = "\n".join([
            f"[{i+1}] [{a.get('priority', 'MEDIUM')}] {a['title']}\n"
            f"    Source: {a['source']} | Published: {a.get('published_at', 'N/A')}\n"
            f"    Summary: {a.get('content', 'No summary available')[:150]}..."
            for i, a in enumerate(articles[:20])  # Limit to 20 most recent/important
        ])

        news_summary = f"Total Articles: {articles_count}\n\n{articles_text}"

        full_prompt = SYSTEM_PROMPT + "\n\n" + NEWS_PROMPT.format(news_data=news_summary)

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=800
        )

        try:
            # Extract <thinking> for debugging
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            thinking = thinking_match.group(1).strip() if thinking_match else ""

            # Extract <answer> JSON 
            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            if answer_match:
                answer_json = answer_match.group(1).strip()
            else:
                # Fallback: try to extract JSON without tags
                answer_json = response

            answer_json = re.sub(r'```json\s*|\s*```', '', answer_json).strip()
            news_data = json.loads(answer_json)

            state['news_analysis'] = json.dumps(news_data)

            if thinking:
                state['news_thinking'] = thinking[:500] 

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  News agent parsing error: {e}")
            print(f"Response: {response[:300]}")

            # Safe fallback
            state['news_analysis'] = json.dumps({
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
                "time_sensitive_events": []
            })

        return state


if __name__ == "__main__":
    agent = NewsAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== NEWS AGENT OUTPUT =====")
    print(f"\n ---- 1st news analysis: \n {result}")
    analysis = json.loads(result.get('news_analysis', '{}'))
    print(f"\n ---- 2nd news analysis: \n {analysis}")
    print(f"Sentiment: {analysis.get('overall_sentiment')}")
    print(f"Recommendation: {analysis.get('recommendation')}")
    print(f"Reasoning: {analysis.get('reasoning')}")
    print(f"Risk Flags: {analysis.get('risk_flags')}")
