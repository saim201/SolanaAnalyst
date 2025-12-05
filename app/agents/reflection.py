"""
Reflection Agent - Bull vs Bear debate system.
Forces consideration of opposing viewpoints to detect blind spots.
Uses structured 4-step analysis framework 
"""
import json
import re
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm


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
  "bull_strength": 0.65,
  "bear_strength": 0.55,
  "consensus_points": ["point1", "point2"],
  "conflict_points": ["conflict1", "conflict2"],
  "blind_spots": {{
    "bull_missing": ["risk1", "risk2"],
    "bear_missing": ["opportunity1", "opportunity2"]
  }},
  "final_recommendation": "BUY|SELL|HOLD",
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
        # Extract prior analyses
        tech_recommendation = state.get('recommendation', 'HOLD')
        tech_confidence = state.get('confidence', 0.5)
        tech_reasoning = state.get('reasoning', 'No technical analysis')
        news_analysis_str = state.get('news_analysis', '{}')
        try:
            news_analysis = json.loads(news_analysis_str)
        except:
            news_analysis = {}

        news_recommendation = news_analysis.get('recommendation', 'NEUTRAL')
        news_confidence = news_analysis.get('confidence', 0.5)
        news_reasoning = news_analysis.get('reasoning', 'No news analysis')

        # summaries for debate
        technical_summary = f"""
Recommendation: {tech_recommendation}
Confidence: {tech_confidence:.0%}
Key Signals: {', '.join(state.get('key_signals', [])[:3])}
Reasoning: {tech_reasoning}
"""

        news_summary = f"""
Sentiment: {news_analysis.get('overall_sentiment', 0.5):.0%}
Recommendation: {news_recommendation}
Critical Events: {', '.join(news_analysis.get('critical_events', [])[:2])}
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

            state['reflection_analysis'] = json.dumps({
                'bull_case_summary': bull_response[:300],
                'bear_case_summary': bear_response[:300],
                'synthesis': synthesis_data
            })

            state['reflection_recommendation'] = synthesis_data.get('final_recommendation', tech_recommendation)
            state['reflection_confidence'] = synthesis_data.get('confidence', tech_confidence)
            state['primary_risk'] = synthesis_data.get('primary_risk', 'Unknown')
            state['monitoring_trigger'] = synthesis_data.get('monitoring_trigger', 'None identified')

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Reflection agent parsing error: {e}")
            print(f"Response: {synthesis_response[:300]}")

            # Fallback: store raw debate
            state['reflection_analysis'] = json.dumps({
                'bull_case_summary': bull_response[:300],
                'bear_case_summary': bear_response[:300],
                'synthesis': {
                    'final_recommendation': tech_recommendation,
                    'confidence': tech_confidence * 0.9,  # Reduce confidence due to synthesis failure
                    'reasoning': f"Debate synthesis failed: {str(e)[:100]}",
                    'primary_risk': 'Synthesis error - proceed with caution'
                }
            })

            state['reflection_recommendation'] = tech_recommendation
            state['reflection_confidence'] = tech_confidence * 0.9

        return state


if __name__ == "__main__":
    agent = ReflectionAgent()
    test_state = AgentState({
        'recommendation': 'BUY',
        'confidence': 0.75,
        'reasoning': 'Strong bullish MACD with price above EMA20',
        'key_signals': ['price above EMA20', 'MACD bullish', 'volume acceptable'],
        'news_analysis': json.dumps({
            'overall_sentiment': 0.65,
            'recommendation': 'BULLISH',
            'confidence': 0.70,
            'reasoning': 'Positive ecosystem growth with new partnerships',
            'critical_events': ['DeFi TVL growth', 'New partnership announced']
        })
    })

    result = agent.execute(test_state)
    print("\n===== REFLECTION AGENT OUTPUT =====")
    reflection = json.loads(result.get('reflection_analysis', '{}'))
    synthesis = reflection.get('synthesis', {})
    print(f"\n ---- reflection agent result: \n {synthesis}")
    print(f"Bull Strength: {synthesis.get('bull_strength')}")

