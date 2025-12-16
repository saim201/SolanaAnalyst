"""
Reflection Agent - Bull vs Bear debate system.
Forces consideration of opposing viewpoints to detect blind spots.
Uses structured 4-step analysis framework 
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.database.data_manager import DataManager


BULL_SYSTEM_PROMPT = """You are the BULL ADVOCATE in a professional trading debate. Your role is to argue for a LONG (BUY) position on Solana.

Your personality:
- Optimistic but not reckless
- Focus on growth catalysts, ecosystem expansion, technical breakouts
- Cite positive news, bullish chart patterns, strong support levels
- Challenge bearish arguments with counterpoints

You argue in good faith - if the setup is genuinely terrible, you'll admit weakness.
"""

BEAR_SYSTEM_PROMPT = """You are the BEAR ADVOCATE in a professional trading debate. Your role is to argue for a SHORT (SELL) position on Solana.

Your personality:
- Skeptical but not pessimistic
- Focus on risk factors, overextension, bearish divergences
- Cite negative news, resistance levels, overbought conditions
- Challenge bullish arguments with counterpoints

You argue in good faith - if the setup is genuinely strong, you'll admit strength.
"""



DEBATE_PROMPT = """
TECHNICAL ANALYSIS SUMMARY:
{technical_summary}

NEWS SENTIMENT SUMMARY:
{news_summary}

<debate_instructions>
You are participating in a structured debate about whether to trade Solana.

ROUND 1: OPENING ARGUMENT
Present your case in 3-4 bullet points:
- What's your primary thesis?
- What signals support your position?
- What's your biggest conviction point?

ROUND 2: COUNTERARGUMENT
After hearing the opposing view, respond:
- What's the strongest point your opponent made?
- How do you counter that point?
- What are they overlooking?

ROUND 3: FINAL VERDICT
- Given both sides, what's your confidence (0.0 to 1.0)?
- What would need to happen to invalidate your thesis?
- On a scale of 1-10, how strong is this setup?
</debate_instructions>

Provide your debate contribution in this format:

<debate>
ROUND 1 - OPENING ARGUMENT:
[Your 3-4 bullet points]

ROUND 2 - COUNTERARGUMENT:
[Your response to opponent]

ROUND 3 - FINAL VERDICT:
Confidence: [0.0 to 1.0]
Invalidation Trigger: [What would prove you wrong]
Setup Strength: [1-10]
</debate>
"""


SYNTHESIS_PROMPT = """
You are a neutral trade arbitrator reviewing a Bull vs Bear debate.

BULL CASE:
{bull_case}

BEAR CASE:
{bear_case}

TECHNICAL ANALYSIS:
Recommendation: {tech_recommendation}
Confidence: {tech_confidence}
Reasoning: {tech_reasoning}

NEWS SENTIMENT:
Recommendation: {news_recommendation}
Confidence: {news_confidence}
Reasoning: {news_reasoning}

<synthesis_task>
Your job is to synthesise both arguments and make a FINAL CALL.

<thinking>

STEP 1: IDENTIFY AGREEMENTS
Where do both bull and bear agree? (These are high-confidence facts)

STEP 2: IDENTIFY CONFLICTS
Where do they disagree? Which side has stronger evidence?

STEP 3: ASSESS BLIND SPOTS
What risks is the bull missing?
What opportunities is the bear missing?

STEP 4: FINAL RECOMMENDATION
Given BOTH perspectives:
- Should we BUY, SELL, or HOLD?
- What's your confidence (0.0 to 1.0)?
- What's the primary risk to this trade?
- What's the key monitoring point for next 24-48 hours?

</thinking>

<answer>
Provide your synthesis in EXACT JSON format:

{{
  "bull_case_summary": "...."
  "bear_case_summary": "..."
  "bull_strength": 0.65,
  "bear_strength": 0.55,
  "consensus_points": ["point1", "point2"],
  "conflict_points": ["conflict1", "conflict2"],
  "blind_spots": {{
    "bull_missing": ["risk1", "risk2"],
    "bear_missing": ["opportunity1", "opportunity2"]
  }},
  "recommendation": "BUY|SELL|HOLD",
  "confidence": 0.70,
  "primary_risk": "Description of main risk",
  "monitoring_trigger": "What to watch in next 24-48h",
  "reasoning": "Final synthesis in 2-3 sentences"
}}

</answer>

</synthesis_task>

"""


class ReflectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.5  # Higher temp for debate diversity
        )

    def execute(self, state: AgentState) -> AgentState:

        techAnalyst = state['technical']
        tech_recommendation = techAnalyst['recommendation']
        tech_confidence = techAnalyst['confidence']
        tech_reasoning = techAnalyst['reasoning']
        tech_keySignals = techAnalyst['key_signals']

        newsAnalyst = state['news']
        news_recommendation = newsAnalyst['recommendation']
        news_confidence = newsAnalyst['confidence']
        news_reasoning = newsAnalyst['reasoning']
        news_sentiment = newsAnalyst['overall_sentiment']
        news_criticalEvents = newsAnalyst['critical_events']



        # summaries for debate
        technical_summary = f"""
Recommendation: {tech_recommendation}
Confidence: {tech_confidence:.0%}
Key Signals: {', '.join(tech_keySignals)}
Reasoning: {tech_reasoning}
"""

        news_summary = f"""
Sentiment: {news_sentiment:.0%}
Recommendation: {news_recommendation}
Critical Events: {', '.join(news_criticalEvents)}
Reasoning: {news_reasoning}
"""

        # === ROUND 1: BULL ADVOCATE ===
        bull_prompt = BULL_SYSTEM_PROMPT + "\n\n" + DEBATE_PROMPT.format(
            technical_summary=technical_summary,
            news_summary=news_summary
        )

        bull_response = llm(
            bull_prompt,
            model=self.model,
            temperature=0.5,
            max_tokens=500
        )

        # === ROUND 2: BEAR ADVOCATE ===
        bear_prompt = BEAR_SYSTEM_PROMPT + "\n\n" + DEBATE_PROMPT.format(
            technical_summary=technical_summary,
            news_summary=news_summary
        )

        bear_response = llm(
            bear_prompt,
            model=self.model,
            temperature=0.5,
            max_tokens=500
        )

        # === SYNTHESIS: NEUTRAL ARBITRATOR ===
        synthesis_prompt = SYNTHESIS_PROMPT.format(
            bull_case=bull_response,
            bear_case=bear_response,
            tech_recommendation=tech_recommendation,
            tech_confidence=tech_confidence,
            tech_reasoning=tech_reasoning,
            news_recommendation=news_recommendation,
            news_confidence=news_confidence,
            news_reasoning=news_reasoning
        )

        synthesis_response = llm(
            synthesis_prompt,
            model=self.model,
            temperature=0.3,
            max_tokens=700
        )

        try:
            synthesis_json = re.sub(r'```json\s*|\s*```', '', synthesis_response).strip()

            json_match = re.search(r'\{.*\}', synthesis_json, re.DOTALL)
            if json_match:
                synthesis_json = json_match.group(0)

            synthesis_data = json.loads(synthesis_json)

            state['reflection'] = synthesis_data

            dm = DataManager()
            dm.save_reflection_analysis(data=state['reflection'])
        

        except (json.JSONDecodeError, ValueError) as e:
            print(f"  Reflection agent parsing error: {e}")
            print(f"Response: {synthesis_response[:300]}")

            state['reflection'] = {
                'bull_case_summary': bull_response[:300],
                'bear_case_summary': bear_response[:300],
                'recommendation': tech_recommendation,
                'confidence': tech_confidence * 0.9,
                'primary_risk': 'Synthesis error - proceed with caution',
                'monitoring_trigger': 'None identified',
                'reasoning': f"Debate synthesis failed: {str(e)[:100]}",
                'bull_strength': 0.5,
                'bear_strength': 0.5,
                'consensus_points': [],
                'conflict_points': [],
                'blind_spots': ['Synthesis failed - unable to identify blind spots']
            }

        return state


if __name__ == "__main__":
    agent = ReflectionAgent()
    test_state = AgentState({
        'technical': {
            'recommendation': 'BUY',
            'confidence': 0.72,
            'timeframe': '3-7 days',
            'key_signals': [
                "Strong bullish momentum with RSI at 68 (not overbought)",
                "Price breaking above EMA50 resistance at $145.20",
                "Volume surge of 1.8x average (institutional interest)",
                "MACD crossover indicating upward trend continuation",
                "Support level holding strong at $142.50"
            ],
            'entry_level': 145.50,
            'stop_loss': 142.00,
            'take_profit': 155.00,
            'reasoning': "Technical indicators suggest a strong bullish setup. The price has successfully broken above the key EMA50 resistance level with significant volume confirmation. RSI is in a healthy range (68), indicating room for further upside. The MACD crossover and strong support at $142.50 provide additional confidence. Risk/reward ratio is favorable at approximately 1:3.2.",
            'confidence_breakdown': {
                'trend_strength': 0.75,
                'momentum_confirmation': 0.80,
                'volume_quality': 0.85,
                'risk_reward': 0.60,
                'final_adjusted': 0.72
            },
            'recommendation_summary': 'HOLD CASH. The current Solana market is untradeable due to critically low volume (61,354 trades vs 3.4M average) and complete lack of directional momentum. Buy pressure has collapsed to 35.5%, signaling zero conviction. Do NOT attempt to trade until: (1) Daily volume returns to >3M trades, (2) Buy pressure recovers above 50%, (3) Price shows clear directional movement above or below key support/resistance levels. Potential downside risk is significant with current market structure.',
            'watch_list': {
                'confirmation_signals': ["Daily volume returns to >3M trades", "Buy pressure recovers above 50%", "Price breaks and holds above $136.48 or below $128.87 on strong volume"],
                'invalidation_signals': ["Continued low volume (<1M daily trades)", "Buy pressure remains below 40%", "Price continues to chop in narrow range"],
                'key_levels_24_48h': ["$136.48 - Potential resistance", "$128.87 - Potential support", "$125.92 - Lower support level"],
                'time_based_triggers': ["24 hours: Monitor volume and buy pressure", "48 hours: If no clear directional move, remain in cash"]
            }
        },
        'news': {
            'overall_sentiment': 0.62,
            'sentiment_label': 'NEUTRAL-BULLISH',
            'confidence': 0.65,
            'all_recent_news': [
                {'title': 'Ondo Finance Tokenized Stocks on Solana', 'published_at': '2025-12-15T15:49:41', 'url': 'https://www.coindesk.com/business/2025/12/15/ondo-finance-to-offer-tokenized-u-s-stocks-etfs-on-solana-early-next-year', 'source': 'CoinDesk'},
                {'title': 'CME Group Solana Futures', 'published_at': '2025-12-15T16:07:00', 'url': 'https://www.coindesk.com/markets/2025/12/15/cme-group-expands-crypto-derivatives-with-spot-quoted-xrp-and-solana-futures', 'source': 'CoinDesk'}
            ],
            'key_events': [
                {'title': 'Ondo Finance Tokenized Stocks on Solana', 'published_at': '2025-12-15T15:49:41', 'url': 'https://www.coindesk.com/business/2025/12/15/ondo-finance-to-offer-tokenized-u-s-stocks-etfs-on-solana-early-next-year', 'type': 'PARTNERSHIP', 'source_credibility': 'REPUTABLE', 'news_age_hours': 12, 'impact': 'BULLISH', 'reasoning': "Expanding Solana's real-world asset tokenization capabilities"},
                {'title': 'CME Group Solana Futures', 'published_at': '2025-12-15T16:07:00', 'url': 'https://www.coindesk.com/markets/2025/12/15/cme-group-expands-crypto-derivatives-with-spot-quoted-xrp-and-solana-futures', 'type': 'PARTNERSHIP', 'source_credibility': 'REPUTABLE', 'news_age_hours': 12, 'impact': 'BULLISH', 'reasoning': 'Institutional derivatives product increases SOL legitimacy'},
                {'title': 'Solana Liquidity Challenges', 'published_at': '2025-12-10T05:03:08', 'url': 'https://decrypt.co/351743/solana-liquidity-plummets-bear-level-500m-liquidation-overhang', 'type': 'ECOSYSTEM', 'source_credibility': 'REPUTABLE', 'news_age_hours': 120, 'impact': 'BEARISH', 'reasoning': 'Declining Total Value Locked and memecoin demand weakness'}
            ],
            'event_summary': {
                'actionable_catalysts': 2,
                'hype_noise': 1,
                'critical_risks': 1
            },
            'risk_flags': ['Declining Total Value Locked', 'Liquidity challenges in ecosystem'],
            'stance': "News is cautiously bullish. Visa partnership is a strong positive catalyst, but recent network issues create some concern. Overall, news SUPPORTS taking long positions but with reduced position size due to reliability questions.",
            'suggested_timeframe': '3-5 days',
            'recommendation_summary': "News presents a cautiously bullish 0.62 sentiment. CME futures and Ondo Finance partnerships provide strong institutional validation, offsetting recent liquidity concerns. Traders should maintain positions but with reduced size, watching for network stability and further institutional adoption signals.",
            'what_to_watch': ['Ondo Finance tokenization launch details', 'CME Solana futures trading volume', 'Total Value Locked trend'],
            'invalidation': "Sustained decline in TVL below current levels OR failure to generate meaningful institutional product adoption."
        }
    })

    result = agent.execute(test_state)
    print("\n===== REFLECTION AGENT OUTPUT =====")
    reflection = json.loads(result.get('reflection_analysis', '{}'))
    synthesis = reflection.get('synthesis', {})
    print(f"\n ---- reflection agent result: \n {synthesis}")
    print(f"Bull Strength: {synthesis.get('bull_strength')}")

