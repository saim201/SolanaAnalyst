"""
Uses weighted consensus + confidence scoring for maximum accuracy.
Critical Rules Built In:
If no consensus (all disagree) → HOLD
If weighted confidence < 0.50 → HOLD
If news has critical risk flags → HOLD
If technical has no entry/stop/target but recommends BUY/SELL → HOLD

"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.database.data_manager import DataManager


SYSTEM_PROMPT = """You are the FINAL DECISION MAKER for SOLANA (SOL/USDT) swing trading with 20 years of experience aggregating expert analyses into executable trading decisions.

Your role is NOT to analyse markets yourself - you synthesize the expert opinions from:
1. Technical Analyst (chart patterns, indicators, momentum)
2. News Analyst (sentiment, catalysts, risk events)
3. Reflection Analyst (bull vs bear debate, blind spots)

Your expertise:
- Detecting when all experts align (STRONG CONSENSUS → high confidence)
- Identifying key disagreements and resolving conflicts
- Weighing confidence levels appropriately
- Recognizing when uncertainty is too high (→ HOLD)
- Understanding that HOLD is a valid position when signals conflict

Decision framework:
- ALL 3 AGREE (same direction + high confidence) → BUY/SELL with HIGH confidence
- 2 OUT OF 3 AGREE (strong signals) → BUY/SELL with MODERATE confidence
- MIXED SIGNALS or LOW confidence (<0.5 average) → HOLD
- ANY agent flags critical risk → Consider HOLD unless overwhelmingly bullish

Remember: HOLD is NOT failure - it's discipline. Only trade when edge is clear.
"""


TRADER_PROMPT = """
TECHNICAL ANALYSIS:
Recommendation: {tech_recommendation}
Confidence: {tech_confidence:.0%}
Timeframe: {tech_timeframe}
Key Signals: {tech_signals}
Entry: ${tech_entry} | Stop: ${tech_stop} | Target: ${tech_target}
Reasoning: {tech_reasoning}

NEWS SENTIMENT:
Recommendation: {news_recommendation}
Sentiment Score: {news_sentiment:.0%}
Sentiment Trend: {news_trend}
Confidence: {news_confidence:.0%}
Critical Events: {news_events}
Risk Flags: {news_risk_flags}
Reasoning: {news_reasoning}

REFLECTION (Bull vs Bear Debate):
Recommendation: {reflection_recommendation}
Confidence: {reflection_confidence:.0%}
Bull Strength: {bull_strength:.0%}
Bear Strength: {bear_strength:.0%}
Primary Risk: {primary_risk}
Monitoring Trigger: {monitoring_trigger}
Consensus Points: {consensus_points}
Conflict Points: {conflict_points}
Blind Spots: {blind_spots}
Reasoning: {reflection_reasoning}

<thinking>
Now analyse the above three expert opinions using this EXACT framework:

STEP 1: CONSENSUS DETECTION
- Do all 3 agents recommend the same direction? (BUY/SELL/HOLD)
- If YES → Strong consensus (confidence boost)
- If 2/3 agree → Moderate consensus
- If all disagree → No consensus (HOLD)

Document: [What's the consensus level?]

STEP 2: CONFIDENCE WEIGHTING
Calculate weighted average confidence:
- Technical confidence: {tech_confidence:.0%} (weight: 40% - most important for swing trades)
- News confidence: {news_confidence:.0%} (weight: 30% - catalysts matter)
- Reflection confidence: {reflection_confidence:.0%} (weight: 30% - synthesis quality)

Weighted average = (0.4 × tech) + (0.3 × news) + (0.3 × reflection)

Document: [Calculated weighted confidence]

STEP 3: RISK ASSESSMENT
- Did News analyst flag any critical risk_flags?
- Did Reflection identify serious blind_spots?
- Is primary_risk manageable or a dealbreaker?
- Is there a clear monitoring_trigger for exit?

Document: [Major risks identified]

STEP 4: CONFLICT RESOLUTION
If agents disagree:
- Which agent has higher confidence?
- Which agent has better reasoning quality?
- Are disagreements minor (timing) or major (direction)?
- Does Reflection agent resolve the conflict?

Document: [How to resolve conflicts]

STEP 5: FINAL DECISION
Given:
- Consensus level: [STRONG/MODERATE/WEAK/NONE]
- Weighted confidence: [calculated value]
- Critical risks: [identified risks]
- Conflict resolution: [if applicable]

What's your FINAL call? BUY, SELL, or HOLD?
</thinking>

<answer>
Based on the 5-step analysis above, provide your FINAL trading decision in this EXACT JSON format:

{{
  "decision": "BUY|SELL|HOLD",
  "confidence": 0.72,
  "consensus_level": "STRONG|MODERATE|WEAK|NONE",
  "agreeing_agents": ["technical", "news"],
  "disagreeing_agents": ["reflection"],
  "primary_concern": "Brief description of main risk or opportunity",
  "reasoning": "2-3 sentence synthesis explaining WHY this decision makes sense given all inputs"
}}
</answer>

CRITICAL RULES:
1. If consensus is NONE (all disagree) → MUST return HOLD
2. If weighted confidence < 0.50 → MUST return HOLD
3. If News has risk_flags=["critical_security_breach"] → MUST return HOLD
4. If NO ENTRY/STOP/TARGET from Technical and recommendation is BUY/SELL → MUST return HOLD
5. confidence must be 0.0 to 1.0
6. decision must be exactly "BUY", "SELL", or "HOLD"
7. Do NOT invent new information - only synthesize what's provided
"""


class TraderAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.2  # Low temp for consistent decision-making
        )

    def execute(self, state: AgentState) -> AgentState:

        # === EXTRACT TECHNICAL ANALYSIS ===
        technical = state.get('technical', {})
        tech_recommendation = technical.get('recommendation', 'HOLD')
        tech_confidence = float(technical.get('confidence', 0.5))
        tech_timeframe = technical.get('timeframe', 'N/A')
        tech_signals = ', '.join(technical.get('key_signals', [])[:3])
        tech_entry = technical.get('entry_level') or 0.0
        tech_stop = technical.get('stop_loss') or 0.0
        tech_target = technical.get('take_profit') or 0.0
        tech_reasoning = technical.get('reasoning', 'No technical analysis available')

        # === EXTRACT NEWS ANALYSIS ===
        news = state.get('news', {})
        news_recommendation = news.get('recommendation', 'NEUTRAL')
        news_sentiment = float(news.get('overall_sentiment', 0.5))
        news_trend = news.get('sentiment_trend', 'stable')
        news_confidence = float(news.get('confidence', 0.5))
        news_events = ', '.join(news.get('critical_events', [])[:2]) or 'None'
        news_risk_flags = ', '.join(news.get('risk_flags', [])) or 'None'
        news_reasoning = news.get('reasoning', 'No news analysis available')

        # === EXTRACT REFLECTION ANALYSIS ===
        reflection = state.get('reflection', {})
        reflection_recommendation = reflection.get('recommendation', 'HOLD')
        reflection_confidence = float(reflection.get('confidence', 0.5))
        bull_strength = float(reflection.get('bull_strength', 0.5))
        bear_strength = float(reflection.get('bear_strength', 0.5))
        primary_risk = reflection.get('primary_risk', 'Unknown')
        monitoring_trigger = reflection.get('monitoring_trigger', 'None identified')
        consensus_points = ', '.join(reflection.get('consensus_points', [])) or 'None'
        conflict_points = ', '.join(reflection.get('conflict_points', [])) or 'None'

        blind_spots_raw = reflection.get('blind_spots', [])
        if isinstance(blind_spots_raw, list):
            blind_spots = ', '.join(blind_spots_raw)
        else:
            blind_spots = str(blind_spots_raw)[:100]

        reflection_reasoning = reflection.get('reasoning', 'No reflection analysis available')


        full_prompt = SYSTEM_PROMPT + "\n\n" + TRADER_PROMPT.format(
            tech_recommendation=tech_recommendation,
            tech_confidence=tech_confidence,
            tech_timeframe=tech_timeframe,
            tech_signals=tech_signals or 'None',
            tech_entry=tech_entry,
            tech_stop=tech_stop,
            tech_target=tech_target,
            tech_reasoning=tech_reasoning,
            news_recommendation=news_recommendation,
            news_sentiment=news_sentiment,
            news_trend=news_trend,
            news_confidence=news_confidence,
            news_events=news_events,
            news_risk_flags=news_risk_flags,
            news_reasoning=news_reasoning,
            reflection_recommendation=reflection_recommendation,
            reflection_confidence=reflection_confidence,
            bull_strength=bull_strength,
            bear_strength=bear_strength,
            primary_risk=primary_risk,
            monitoring_trigger=monitoring_trigger,
            consensus_points=consensus_points,
            conflict_points=conflict_points,
            blind_spots=blind_spots,
            reflection_reasoning=reflection_reasoning
        )

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=600
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

            json_match = re.search(r'\{.*\}', answer_json, re.DOTALL)
            if json_match:
                answer_json = json_match.group(0)

            decision_data = json.loads(answer_json)

            # === VALIDATE AND EXTRACT FIELDS ===
            final_decision = decision_data.get('decision', 'HOLD').upper()
            final_confidence = float(decision_data.get('confidence', 0.5))
            consensus_level = decision_data.get('consensus_level', 'UNKNOWN')
            agreeing_agents = decision_data.get('agreeing_agents', [])
            disagreeing_agents = decision_data.get('disagreeing_agents', [])
            primary_concern = decision_data.get('primary_concern', primary_risk)
            reasoning = decision_data.get('reasoning', '')

            if final_decision not in ['BUY', 'SELL', 'HOLD']:
                print(f"⚠️  Invalid decision '{final_decision}', defaulting to HOLD")
                final_decision = 'HOLD'

            # Clamp confidence
            final_confidence = max(0.0, min(1.0, final_confidence))

            # === SAVE TO STATE ===
            state['trader'] = {
                'decision': final_decision,
                'confidence': final_confidence,
                'consensus_level': consensus_level,
                'agreeing_agents': agreeing_agents,
                'disagreeing_agents': disagreeing_agents,
                'primary_concern': primary_concern,
                'reasoning': reasoning,
                'thinking': thinking[:500] if thinking else ''
            }

            # === SAVE TO DATABASE ===
            try:
                dm = DataManager()
                dm.save_trader_decision(
                    timestamp=datetime.now(),
                    data=state['trader']
                )
                dm.close()
            except Exception as e:
                print(f"⚠️  Failed to save trader decision to DB: {e}")

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Trader agent parsing error: {e}")
            print(f"Response preview: {response[:300]}")

            # === FALLBACK DECISION ===
            fallback_decision = reflection_recommendation
            fallback_confidence = reflection_confidence * 0.85  # Reduce confidence due to error
            fallback_reasoning = f"Synthesis failed, defaulting to Reflection agent: {reflection_reasoning[:150]}"

            state['trader'] = {
                'decision': fallback_decision,
                'confidence': fallback_confidence,
                'consensus_level': 'UNKNOWN',
                'agreeing_agents': [],
                'disagreeing_agents': [],
                'primary_concern': 'Synthesis error - low confidence',
                'reasoning': fallback_reasoning,
                'thinking': ''
            }

            print(f"\n⚠️  FALLBACK DECISION: {fallback_decision} ({fallback_confidence:.0%})")

        print("="*70 + "\n")
        return state


if __name__ == "__main__":


    agent = TraderAgent()
    # === TEST CASE: STRONG BULLISH CONSENSUS ===
    test_state = AgentState()

    test_state['technical'] = {
        'recommendation': 'BUY',
        'confidence': 0.78,
        'confidence_breakdown': {
            'trend_strength': 0.85,
            'momentum_confirmation': 0.75,
            'volume_quality': 0.80,
            'risk_reward': 0.90,
            'final_adjusted': 0.78
        },
        'timeframe': '1-5 days',
        'key_signals': [
            'Price broke above EMA20 with strong volume',
            'MACD histogram expanding (bullish momentum)',
            'RSI 58 (healthy, not overbought)'
        ],
        'entry_level': 187.50,
        'stop_loss': 181.00,
        'take_profit': 199.00,
        'reasoning': 'Clean breakout above EMA20 with volume confirmation. MACD showing bullish divergence. Risk/reward 1.77:1 with clear support at $181.',
        'thinking': 'Analyzed 14 days of price action. Volume spike confirms institutional interest.'
    }

    test_state['news'] = {
        'overall_sentiment': 0.72,
        'sentiment_trend': 'improving',
        'sentiment_breakdown': {
            'regulatory': 0.7,
            'partnership': 0.85,
            'upgrade': 0.6,
            'security': 0.9,
            'macro': 0.55
        },
        'critical_events': [
            'Solana DeFi TVL surpasses $6B (bullish - ecosystem growth)',
            'Major CEX listing announcement incoming (bullish - liquidity boost)'
        ],
        'event_classification': {
            'actionable_catalysts': 2,
            'noise_hype': 1,
            'risk_flags': 0
        },
        'recommendation': 'BULLISH',
        'confidence': 0.74,
        'hold_duration': '3-5 days',
        'reasoning': 'Strong ecosystem fundamentals with DeFi TVL growth and upcoming CEX listing. No major regulatory headwinds. Positive macro environment.',
        'risk_flags': [],
        'time_sensitive_events': ['CEX listing expected within 48h'],
        'thinking': 'Analyzed 15 news articles. Sentiment across all categories is positive.'
    }

    test_state['reflection'] = {
        'bull_case_summary': 'Technical breakout + strong fundamentals + positive catalysts align for upside move',
        'bear_case_summary': 'Potential short-term overbought after 8% rally. Resistance at $195 could cap gains',
        'bull_strength': 0.76,
        'bear_strength': 0.52,
        'recommendation': 'BUY',
        'confidence': 0.70,
        'primary_risk': 'Resistance at $195 could trigger profit-taking',
        'monitoring_trigger': 'Watch for volume decline below 1.0x average or breakdown below $181',
        'consensus_points': [
            'Technical structure is bullish',
            'Volume confirms the breakout',
            'Fundamentals support higher prices'
        ],
        'conflict_points': [
            'Bears warn of short-term overbought conditions',
            'Bulls see breakout, bears see resistance ahead'
        ],
        'blind_spots': [
            'Bull missing: Potential macro headwinds from Fed policy',
            'Bear missing: Strong institutional accumulation pattern'
        ],
        'reasoning': 'Bull case is clearly stronger. All three signals (technical, news, fundamentals) align for 3-5 day swing trade. Risk is manageable with stop at $181.'
    }

    result = agent.execute(test_state)

    if result.get('trader'):
        trader = result['trader']
        print(f"\n✅ TEST RESULT:")
        print(f"   Decision: {trader['decision']}")
        print(f"   Confidence: {trader['confidence']:.0%}")
        print(f"   Consensus: {trader['consensus_level']}")
        print(f"   Reasoning: {trader['reasoning']}")
    else:
        print(f"\n❌ TEST FAILED: No trader output")

