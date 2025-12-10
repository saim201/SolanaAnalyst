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
</synthesis_task>

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
            print(f"⚠️  Reflection agent parsing error: {e}")
            print(f"Response: {synthesis_response[:300]}")

            state['reflection'] = {
                'bull_case_summary': bull_response[:300],
                'bear_case_summary': bear_response[:300],
                'recommendation': tech_recommendation,
                'confidence': tech_confidence * 0.9,
                'primary_risk': 'Synthesis error - proceed with caution',
                'monitoring_trigger': 'None identified',
                'reasoning': f"Debate synthesis failed: {str(e)[:100]}",
                # Fixed: Added missing required fields
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
            'recommendation': 'HOLD',
            'confidence': 0.45,
            'confidence_breakdown': {"trend_strength": 0.4, "momentum_confirmation": 0.5, "volume_quality": 0.3, "risk_reward": 0.6, "final_adjusted": 0.45},
            'timeframe': '1-5 days',
            'key_signals': ["Price below key EMAs", "Weak volume at 0.88x", "Neutral momentum indicators"],
            'entry_level': 0.00,
            'stop_loss': 0.00,
            'take_profit': 0.00,
            'reasoning': 'Insufficient clear directional signals and weak volume suggest waiting for more definitive market structure. Current setup lacks the conviction required for a high-probability swing trade. Patience is recommended until volume confirms a clear trend.',
        },
        'news': {
            'overall_sentiment': 0.62,
            'recommendation': 'CAUTIOUSLY BULLISH',
            'confidence': 0.65,
            'reasoning': 'Positive ecosystem developments with cross-chain integration and mobile token launch offset by minor security concerns. Institutional interest remains steady.',
            'critical_events': ["Coinbase/Chainlink Base-Solana Bridge", "Solana Mobile SKR Token Upcoming Launch", "Solmate RockawayX Acquisition"]
        }
    })

    result = agent.execute(test_state)
    print("\n===== REFLECTION AGENT OUTPUT =====")
    reflection = json.loads(result.get('reflection_analysis', '{}'))
    synthesis = reflection.get('synthesis', {})
    print(f"\n ---- reflection agent result: \n {synthesis}")
    print(f"Bull Strength: {synthesis.get('bull_strength')}")

