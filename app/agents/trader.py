"""
Trader Agent - Final decision aggregator (Haiku model for speed/cost).
Simply synthesizes prior analyses into executable decision.
"""
import json
import re
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm


SYSTEM_PROMPT = """You are a trade execution coordinator. Your job is simple: take the analyses from the technical team, news team, and risk team, then make a FINAL call.

You are NOT analyzing markets yourself - you're aggregating expert opinions.

Your decision framework:
- If technical + news + reflection all agree → HIGH confidence
- If 2 out of 3 agree → MODERATE confidence
- If all disagree → HOLD (wait for clarity)
- ALWAYS defer to reflection agent if it identified blind spots
"""


TRADER_PROMPT = """
TECHNICAL ANALYSIS:
Recommendation: {tech_recommendation}
Confidence: {tech_confidence:.0%}
Key Signals: {tech_signals}
Reasoning: {tech_reasoning}

NEWS SENTIMENT:
Recommendation: {news_recommendation}
Confidence: {news_confidence:.0%}
Reasoning: {news_reasoning}

REFLECTION (Bull vs Bear Debate):
Final Recommendation: {reflection_recommendation}
Confidence: {reflection_confidence:.0%}
Primary Risk: {primary_risk}
Monitoring Trigger: {monitoring_trigger}

PORTFOLIO CONTEXT:
Current Balance: ${portfolio_balance:,.2f}
Open Positions: {open_positions}

<decision_task>
Synthesize the above analyses into a FINAL trading decision.

STEP 1: CHECK CONSENSUS
Do all 3 analyses agree? If yes, confidence is HIGH.
If 2 agree, confidence is MODERATE.
If all disagree, recommend HOLD.

STEP 2: ASSESS CONVICTION
- Technical confidence: {tech_confidence:.0%}
- News confidence: {news_confidence:.0%}
- Reflection confidence: {reflection_confidence:.0%}
Average confidence = ?

STEP 3: IDENTIFY PRIMARY CONCERN
What's the biggest risk mentioned by reflection agent?
Is this risk manageable or a dealbreaker?

STEP 4: FINAL CALL
Given all analyses, what's your decision?
BUY, SELL, or HOLD?
</decision_task>

Provide your final decision in EXACT JSON format:

{{
  "decision": "BUY|SELL|HOLD",
  "confidence": 0.75,
  "consensus_level": "STRONG|MODERATE|WEAK|NONE",
  "agreeing_agents": ["technical", "news", "reflection"],
  "disagreeing_agents": [],
  "primary_concern": "Description of main risk or opportunity",
  "reasoning": "Final synthesis in 2-3 sentences explaining your decision"
}}

CRITICAL RULES:
1. If consensus is NONE (all disagree), you MUST return HOLD
2. If any agent has confidence < 0.5, reduce final confidence
3. If reflection identified critical blind spots, address them in reasoning
4. confidence must be between 0.0 and 1.0
"""


class TraderAgent(BaseAgent):
    """
    Agent that aggregates analyses into final decision.

    NOTE: Downgraded to Haiku for cost efficiency.
    This agent doesn't do deep analysis - just synthesizes prior work.
    """

    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",  # DOWNGRADED from Sonnet
            temperature=0.2
        )

    def execute(self, state: AgentState) -> AgentState:
        """
        Aggregate all analyses into final trading decision.

        Args:
            state: Current trading state with all analyses

        Returns:
            State with final decision, confidence, and reasoning
        """
        print("\n" + "="*60)
        print("🎯 TRADER AGENT - FINAL DECISION SYNTHESIS")
        print("="*60)

        # Extract prior analyses
        tech_recommendation = state.get('recommendation', 'HOLD')
        tech_confidence = state.get('confidence', 0.5)
        tech_reasoning = state.get('reasoning', 'No technical analysis')
        tech_signals = ', '.join(state.get('key_signals', [])[:3])

        # Parse news analysis
        news_analysis_str = state.get('news_analysis', '{}')
        try:
            news_analysis = json.loads(news_analysis_str)
        except:
            news_analysis = {}

        news_recommendation = news_analysis.get('recommendation', 'NEUTRAL')
        news_confidence = news_analysis.get('confidence', 0.5)
        news_reasoning = news_analysis.get('reasoning', 'No news analysis')

        # Parse reflection analysis
        reflection_analysis_str = state.get('reflection_analysis', '{}')
        try:
            reflection_analysis = json.loads(reflection_analysis_str)
            synthesis = reflection_analysis.get('synthesis', {})
        except:
            synthesis = {}

        reflection_recommendation = state.get('reflection_recommendation', tech_recommendation)
        reflection_confidence = state.get('reflection_confidence', tech_confidence)
        primary_risk = state.get('primary_risk', 'Unknown')
        monitoring_trigger = state.get('monitoring_trigger', 'None identified')

        # Get portfolio context
        from app.database.config import get_db_session
        from app.database.models import PortfolioState, Position

        try:
            db = get_db_session()
            portfolio = db.query(PortfolioState).order_by(PortfolioState.timestamp.desc()).first()
            open_positions = db.query(Position).filter(OpenPosition.status == 'open').count()
            db.close()

            portfolio_balance = portfolio.net_worth if portfolio else 10000.0
        except:
            portfolio_balance = 10000.0
            open_positions = 0

        # Display analysis summary
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   Technical: {tech_recommendation} ({tech_confidence:.0%})")
        print(f"   News: {news_recommendation} ({news_confidence:.0%})")
        print(f"   Reflection: {reflection_recommendation} ({reflection_confidence:.0%})")
        print(f"   Primary Risk: {primary_risk}")

        # Build prompt
        full_prompt = SYSTEM_PROMPT + "\n\n" + TRADER_PROMPT.format(
            tech_recommendation=tech_recommendation,
            tech_confidence=tech_confidence,
            tech_signals=tech_signals,
            tech_reasoning=tech_reasoning,
            news_recommendation=news_recommendation,
            news_confidence=news_confidence,
            news_reasoning=news_reasoning,
            reflection_recommendation=reflection_recommendation,
            reflection_confidence=reflection_confidence,
            primary_risk=primary_risk,
            monitoring_trigger=monitoring_trigger,
            portfolio_balance=portfolio_balance,
            open_positions=open_positions
        )

        # Call LLM
        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=400
        )

        # Parse response
        try:
            # Clean JSON
            response_json = re.sub(r'```json\s*|\s*```', '', response).strip()

            # Try to extract JSON
            json_match = re.search(r'\{.*\}', response_json, re.DOTALL)
            if json_match:
                response_json = json_match.group(0)

            decision_data = json.loads(response_json)

            # Extract fields
            decision = decision_data.get('decision', 'HOLD').upper()
            confidence = float(decision_data.get('confidence', 0.5))
            consensus_level = decision_data.get('consensus_level', 'UNKNOWN')
            reasoning = decision_data.get('reasoning', '')
            primary_concern = decision_data.get('primary_concern', '')

            # Validate
            if decision not in ['BUY', 'SELL', 'HOLD']:
                decision = 'HOLD'
            confidence = max(0.0, min(1.0, confidence))

            # Update state
            state['recommendation'] = decision
            state['confidence'] = confidence
            state['reasoning'] = reasoning
            state['consensus_level'] = consensus_level
            state['primary_concern'] = primary_concern

            # Display decision
            print(f"\n✅ FINAL DECISION: {decision}")
            print(f"   Confidence: {confidence:.0%}")
            print(f"   Consensus: {consensus_level}")
            print(f"   Reasoning: {reasoning}")

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Trader agent parsing error: {e}")
            print(f"Response: {response[:300]}")

            # Fallback: use reflection recommendation (most reliable)
            state['recommendation'] = reflection_recommendation
            state['confidence'] = reflection_confidence * 0.9  # Reduce confidence
            state['reasoning'] = f"Synthesis failed, defaulting to reflection: {synthesis.get('reasoning', 'N/A')}"
            state['consensus_level'] = 'UNKNOWN'

            print(f"\n⚠️  FALLBACK DECISION: {state['recommendation']} ({state['confidence']:.0%})")

        print("="*60 + "\n")

        return state


if __name__ == "__main__":
    agent = TraderAgent()
    test_state = AgentState({
        'recommendation': 'BUY',
        'confidence': 0.75,
        'reasoning': 'Strong bullish setup',
        'key_signals': ['MACD bullish', 'RSI oversold', 'volume strong'],
        'news_analysis': json.dumps({
            'recommendation': 'BULLISH',
            'confidence': 0.70,
            'reasoning': 'Positive ecosystem growth'
        }),
        'reflection_analysis': json.dumps({
            'synthesis': {
                'final_recommendation': 'BUY',
                'confidence': 0.72,
                'reasoning': 'Bull case stronger than bear case'
            }
        }),
        'reflection_recommendation': 'BUY',
        'reflection_confidence': 0.72,
        'primary_risk': 'Potential resistance at $200',
        'monitoring_trigger': 'Watch for volume decline'
    })

    result = agent.execute(test_state)
    print(f"\nFinal: {result.get('recommendation')} @ {result.get('confidence'):.0%}")
    print(f"Reasoning: {result.get('reasoning')}")
