# trader.py 

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from typing import Dict

from anthropic import Anthropic

from app.agents.base import BaseAgent, AgentState
from app.database.data_manager import DataManager



TRADER_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation_signal": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD", "WAIT"],
            "description": "Final trading decision"
        },
        "market_condition": {
            "type": "string",
            "enum": ["BULLISH", "BEARISH", "NEUTRAL", "BULLISH_BUT_CAUTIOUS", "BEARISH_BUT_WATCHING"],
            "description": "Overall market assessment"
        },
        "confidence": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": "Final confidence 0.15-1.0"
                },
                "reasoning": {
                    "type": "string",
                    "description": "3-4 sentences: All 3 agents views with scores, weighted calculation with adjustments, key factor that tips decision, clear link to recommendation"
                }
            },
            "required": ["score", "reasoning"],
            "additionalProperties": False
        },
        "thinking": {
            "type": "string",
            "description": "Full chain-of-thought reasoning process"
        },
        "final_verdict": {
            "type": "object",
            "properties": {
                "technical_says": {
                    "type": "string",
                    "description": "Technical recommendation with confidence and brief key point"
                },
                "sentiment_says": {
                    "type": "string",
                    "description": "Sentiment recommendation with confidence and brief key point"
                },
                "reflection_says": {
                    "type": "string",
                    "description": "Reflection recommendation with confidence and brief key point"
                },
                "my_decision": {
                    "type": "string",
                    "description": "2-3 sentences: YOUR final call, why weighted this way, deciding factor, why right decision"
                }
            },
            "required": ["technical_says", "sentiment_says", "reflection_says", "my_decision"],
            "additionalProperties": False
        },
        "trade_setup": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["READY_TO_ENTER", "WAIT_FOR_SETUP", "HOLD_POSITION", "EXIT_RECOMMENDED"],
                    "description": "Current trade status"
                },
                "entry_price": {
                    "type": "number",
                    "description": "Entry price level"
                },
                "stop_loss": {
                    "type": "number",
                    "description": "Stop loss level"
                },
                "take_profit": {
                    "type": "number",
                    "description": "Take profit target"
                },
                "risk_reward": {
                    "type": "number",
                    "description": "Risk to reward ratio"
                },
                "position_size": {
                    "type": "string",
                    "description": "Position sizing guidance"
                },
                "timeframe": {
                    "type": "string",
                    "description": "Expected trade duration"
                },
                "setup_explanation": {
                    "type": "string",
                    "description": "2-3 sentences explaining trade math: entry/stop/target levels with reasoning"
                }
            },
            "required": ["status", "entry_price", "stop_loss", "take_profit", "risk_reward", "position_size", "timeframe", "setup_explanation"],
            "additionalProperties": False
        },
        "action_plan": {
            "type": "object",
            "properties": {
                "for_new_traders": {
                    "type": "string",
                    "description": "2-4 sentences: specific guidance for entering - buy now or wait, conditions, price levels"
                },
                "for_current_holders": {
                    "type": "string",
                    "description": "2-4 sentences: guidance for existing positions - hold/exit, price levels, stop management"
                },
                "entry_conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific conditions that must be met to enter"
                },
                "exit_conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific exit scenarios with price levels"
                }
            },
            "required": ["for_new_traders", "for_current_holders", "entry_conditions", "exit_conditions"],
            "additionalProperties": False
        },
        "what_to_monitor": {
            "type": "object",
            "properties": {
                "critical_next_48h": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Most urgent things to watch in next 48 hours"
                },
                "daily_checks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Daily monitoring items"
                },
                "exit_immediately_if": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Red flags that trigger immediate exit"
                }
            },
            "required": ["critical_next_48h", "daily_checks", "exit_immediately_if"],
            "additionalProperties": False
        },
        "risk_assessment": {
            "type": "object",
            "properties": {
                "main_risk": {
                    "type": "string",
                    "description": "2-3 sentences: PRIMARY risk that could kill trade, why it matters, likelihood"
                },
                "why_this_position_size": {
                    "type": "string",
                    "description": "1-2 sentences: position sizing logic based on confidence"
                },
                "what_kills_this_trade": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Invalidation scenarios with specifics"
                }
            },
            "required": ["main_risk", "why_this_position_size", "what_kills_this_trade"],
            "additionalProperties": False
        }
    },
    "required": [
        "recommendation_signal",
        "market_condition",
        "confidence",
        "thinking",
        "final_verdict",
        "trade_setup",
        "action_plan",
        "what_to_monitor",
        "risk_assessment"
    ],
    "additionalProperties": False
}



SYSTEM_PROMPT = """You are the CHIEF TRADING OFFICER making final trading decisions on SOLANA (SOL/USDT) swing trades.

20 years experience synthesising multi-agent analysis into actionable trading decisions. Your specialty: translating complex analysis into clear, executable trading plans.

YOUR ROLE:
- Review and synthesise 3 expert analyses: Technical, Sentiment, Reflection
- Weight appropriately: Technical 40% (timing/chart), Sentiment 30% (catalysts), Reflection 30% (synthesis/blind spots)
- Make final decision: BUY/SELL/HOLD/WAIT
- Provide clear execution guidance for new entries and existing positions

YOUR DECISION FRAMEWORK:
- Technical drives TIMING (when to enter/exit)
- Sentiment drives CONVICTION (catalysts that justify trade)
- Reflection catches BLIND SPOTS and resolves conflicts
- WAIT is valid when edge is unclear
- Position sizing reflects confidence
- Every trade needs entry, stop, target, and monitoring plan

YOUR COMMUNICATION:
- Clear and direct - no jargon unless necessary
- Actionable - traders know exactly what to do
- Honest - admit when confidence is low or signals mixed
- Educational - explain WHY not just WHAT
- Risk-focused - always highlight main danger

CRITICAL RULES:
1. Always cite specific agent scores when synthesizing
2. Show confidence calculation transparently
3. Provide separate guidance for new traders vs holders
4. Every price level needs reasoning
5. Resolve conflicts - don't just say "mixed signals"
6. Dead volume (<0.7x) or no trade levels = automatic WAIT
"""



TRADER_PROMPT = """
<technical_analysis>
**Recommendation:** {tech_recommendation}
**Confidence:** {tech_confidence:.0%}
**Market Condition:** {tech_market_condition}

**Confidence Reasoning:** {tech_confidence_reasoning}

**Trade Setup:**
- Entry: ${tech_entry}
- Stop Loss: ${tech_stop}
- Take Profit: ${tech_target}
- Risk/Reward: {tech_risk_reward}
- Timeframe: {tech_timeframe}

**Key Factors:**
- Volume: {volume_ratio:.2f}x ({volume_quality})
</technical_analysis>

<sentiment_analysis>
**Recommendation:** {sentiment_recommendation}
**Confidence:** {sentiment_confidence:.0%}
**Market Condition:** {sentiment_market_condition}

**Confidence Reasoning:** {sentiment_confidence_reasoning}

**Key Factors:**
- CFGI: {cfgi_score}/100 ({cfgi_classification})

**Key Events:**
{sentiment_key_events_formatted}

**Risk Flags:**
{sentiment_risk_flags_formatted}
</sentiment_analysis>

<reflection_analysis>
**Recommendation:** {reflection_recommendation}
**Confidence:** {reflection_confidence:.0%}
**Market Condition:** {reflection_market_condition}

**Confidence Reasoning:** {reflection_confidence_reasoning}

**Agent Alignment:**
- Alignment Score: {alignment_score:.0%}
- Synthesis: {reflection_synthesis}

**Blind Spots:**
- Technical Missed: {reflection_technical_missed}
- Sentiment Missed: {reflection_sentiment_missed}
- Critical Insight: {reflection_critical_insight}

**Primary Risk:** {primary_risk}
</reflection_analysis>

---

<instructions>
Analyse all 3 agents and create final trading decision using chain-of-thought reasoning.

Write detailed reasoning inside <thinking> tags, then output JSON inside <answer> tags.

## THINKING PROCESS (5 steps):

**STEP 1: AGENT CONSENSUS**
Compare recommendations:
- Technical: {tech_recommendation} ({tech_confidence:.0%})
- Sentiment: {sentiment_recommendation} ({sentiment_confidence:.0%})
- Reflection: {reflection_recommendation} ({reflection_confidence:.0%})

Analyse (3-4 sentences):
- All 3 agree = STRONG CONSENSUS?
- 2 of 3 agree = MODERATE CONSENSUS?
- All disagree = NO CONSENSUS (likely WAIT)?
- What's core agreement/disagreement? Be specific.

**STEP 2: WEIGHTED CONFIDENCE**
Calculate weighted confidence:
- Technical: 40%
- Sentiment: 30%
- Reflection: 30%

Show math:
```
Base = (0.40 × {tech_confidence}) + (0.30 × {sentiment_confidence}) + (0.30 × {reflection_confidence})
Base = [calculation] = [result]

Adjustments:
- Volume dead (<0.7x): -0.08
- Volume weak (<1.0x): -0.05
- High risk flagged: -0.05
- Strong consensus (all agree): +0.05
- Conflict (all disagree): -0.10

Final = [base] + [adjustments] = [final]
```

Explain what final confidence means (1-2 sentences).

**STEP 3: AGENT CONTRIBUTIONS**

**Technical** (2-3 sentences):
- Strongest signal?
- Trade levels valid and actionable?
- What did they miss?
- Trust level: HIGH/MEDIUM/LOW and why?

**Sentiment** (2-3 sentences):
- Catalysts REAL or just hype?
- Critical risk flags?
- News freshness (<48h = high impact, >72h = fading)?
- Support or contradict Technical?

**Reflection** (2-3 sentences):
- What blind spots uncovered?
- Risk assessment valid and actionable?
- Found something BOTH others missed?
- Should caution override bullish/bearish case?

**STEP 4: RESOLVE CONFLICTS & DECIDE**

If disagreement, answer:
- Which agent has stronger EVIDENCE?
- Does Technical override Sentiment or vice versa?
- Is Reflection's caution justified by measurable risks?
- Path of LEAST REGRET if wrong?

**Decision rules:**
- Confidence ≥0.65 AND 2+ agree → BUY/SELL (confident)
- Confidence 0.50-0.64 AND moderate consensus → BUY/SELL with reduced size
- Confidence <0.50 OR no consensus → HOLD/WAIT (no edge)
- Dead volume (<0.7x) → WAIT regardless
- No valid trade levels → WAIT

Explain (3-4 sentences):
- Final recommendation_signal (BUY/SELL/HOLD/WAIT)
- Why this makes sense
- What would change your mind

**STEP 5: EXECUTION PLAN**

**For New Traders** (2-3 sentences):
- Enter NOW or WAIT?
- If wait, what conditions? (price, volume, timeframe)

**For Current Holders** (2-3 sentences):
- Hold, take profits, or exit?
- Specific price levels?

**Entry Conditions** (2-3 items):
- Specific conditions before entering

**Exit Conditions** (2-4 items):
- Profit targets with levels
- Time limits
- Stop loss

**Monitoring** (what to check and when):
- Critical next 24-48h
- Daily checks
- Red flags for immediate exit

Write in clear, actionable language.

## CONFIDENCE GUIDELINES:

**Score (0.15-1.0):**
- 0.80-1.00: Very high - strong consensus, clear edge, minimal risks
- 0.65-0.79: High - good alignment, manageable risks, solid setup
- 0.50-0.64: Moderate - some conflicts but edge exists
- 0.35-0.49: Low - significant conflicts or unclear edge
- 0.15-0.34: Very low - major conflicts or no edge

**Reasoning (CRITICAL - 3-4 sentences):**
Must include:
1. All 3 agents with scores: "Technical BUY (0.72), Sentiment BULLISH (0.65), Reflection WAIT (0.57)"
2. Weighted calculation: "Weighted base 0.66, volume adjustment -0.08 = 0.58 final"
3. Key factor: "Dead volume is dealbreaker despite bullish alignment"
4. Link to recommendation: "Therefore WAIT until volume >1.5x confirms institutions buying"

Write naturally, be specific, cite actual numbers.

## OUTPUT:

Output valid JSON matching schema exactly inside <answer> tags.

**CRITICAL NOTES:**
- NO CONSENSUS = WAIT
- LOW CONFIDENCE (<0.50) = WAIT or HOLD
- NO TRADE LEVELS = WAIT
- DEAD VOLUME (<0.7x) = WAIT
- CRITICAL RISKS = WAIT
- Position sizing scales with confidence
- Show math for confidence
- Be specific with every price/timeframe
- Resolve conflicts explicitly
- Write for traders who execute, not analysts
</instructions>
"""




def get_nested(d, path, default=None):
    keys = path.split('.')
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
            if d is None:
                return default
        else:
            return default
    return d if d is not None else default



class TraderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-sonnet-4-5-20250929",
            temperature=0.2
        )
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def execute(self, state: AgentState) -> AgentState:
        tech = state.get('technical', {})
        sentiment = state.get('sentiment', {})
        reflection = state.get('reflection', {})

        tech_recommendation = tech.get('recommendation_signal', 'HOLD')
        tech_confidence_obj = tech.get('confidence', {})
        tech_confidence = float(tech_confidence_obj.get('score', 0.5)) if isinstance(tech_confidence_obj, dict) else 0.5
        tech_market_condition = tech.get('market_condition', 'QUIET')
        tech_confidence_reasoning = tech_confidence_obj.get('reasoning', 'No reasoning provided') if isinstance(tech_confidence_obj, dict) else 'No reasoning provided'

        tech_entry = get_nested(tech, 'trade_setup.entry', 0.0)
        tech_stop = get_nested(tech, 'trade_setup.stop_loss', 0.0)
        tech_target = get_nested(tech, 'trade_setup.take_profit', 0.0)
        tech_risk_reward = get_nested(tech, 'trade_setup.risk_reward', 0.0)
        tech_timeframe = get_nested(tech, 'trade_setup.timeframe', 'N/A')
        volume_ratio = get_nested(tech, 'analysis.volume.ratio', 1.0)
        volume_quality = get_nested(tech, 'analysis.volume.quality', 'UNKNOWN')

        sentiment_recommendation = sentiment.get('recommendation_signal', 'HOLD')
        sentiment_confidence_obj = sentiment.get('confidence', {})
        sentiment_confidence = float(sentiment_confidence_obj.get('score', 0.5)) if isinstance(sentiment_confidence_obj, dict) else 0.5
        sentiment_market_condition = sentiment.get('market_condition', 'NEUTRAL')
        sentiment_confidence_reasoning = sentiment_confidence_obj.get('reasoning', 'No reasoning provided') if isinstance(sentiment_confidence_obj, dict) else 'No reasoning provided'

        cfgi_data = sentiment.get('market_fear_greed', {})
        cfgi_score = cfgi_data.get('score', 50)
        cfgi_classification = cfgi_data.get('classification', 'Neutral')

        sentiment_key_events = sentiment.get('key_events', [])
        sentiment_key_events_formatted = "\n".join([
            f"- {e.get('title', 'Unknown')} ({e.get('source', 'Unknown')}, {e.get('published_at', 'Unknown')})"
            for e in sentiment_key_events[:3]
        ]) if sentiment_key_events else "- None"

        sentiment_risk_flags = sentiment.get('risk_flags', [])
        sentiment_risk_flags_formatted = "\n".join([f"- {flag}" for flag in sentiment_risk_flags]) if sentiment_risk_flags else "- None"

        reflection_recommendation = reflection.get('recommendation_signal', 'HOLD')
        reflection_confidence_obj = reflection.get('confidence', {})
        reflection_confidence = float(reflection_confidence_obj.get('score', 0.5)) if isinstance(reflection_confidence_obj, dict) else 0.5
        reflection_market_condition = reflection.get('market_condition', 'MIXED')
        reflection_confidence_reasoning = reflection_confidence_obj.get('reasoning', 'No reasoning provided') if isinstance(reflection_confidence_obj, dict) else 'No reasoning provided'

        alignment_score = get_nested(reflection, 'agent_alignment.alignment_score', 0.5)
        reflection_synthesis = get_nested(reflection, 'agent_alignment.synthesis', 'No synthesis available')

        blind_spots = reflection.get('blind_spots', {})
        reflection_technical_missed = blind_spots.get('technical_missed', 'None identified')
        reflection_sentiment_missed = blind_spots.get('sentiment_missed', 'None identified')
        reflection_critical_insight = blind_spots.get('critical_insight', 'None identified')

        primary_risk = reflection.get('primary_risk', 'No primary risk identified')

        full_prompt = SYSTEM_PROMPT + "\n\n" + TRADER_PROMPT.format(
            tech_recommendation=tech_recommendation,
            tech_confidence=tech_confidence,
            tech_market_condition=tech_market_condition,
            tech_confidence_reasoning=tech_confidence_reasoning,
            tech_entry=tech_entry if tech_entry else "N/A",
            tech_stop=tech_stop if tech_stop else "N/A",
            tech_target=tech_target if tech_target else "N/A",
            tech_risk_reward=tech_risk_reward if tech_risk_reward else "N/A",
            tech_timeframe=tech_timeframe,
            volume_ratio=volume_ratio,
            volume_quality=volume_quality,
            sentiment_recommendation=sentiment_recommendation,
            sentiment_confidence=sentiment_confidence,
            sentiment_market_condition=sentiment_market_condition,
            sentiment_confidence_reasoning=sentiment_confidence_reasoning,
            cfgi_score=cfgi_score,
            cfgi_classification=cfgi_classification,
            sentiment_key_events_formatted=sentiment_key_events_formatted,
            sentiment_risk_flags_formatted=sentiment_risk_flags_formatted,
            reflection_recommendation=reflection_recommendation,
            reflection_confidence=reflection_confidence,
            reflection_market_condition=reflection_market_condition,
            reflection_confidence_reasoning=reflection_confidence_reasoning,
            alignment_score=alignment_score,
            reflection_synthesis=reflection_synthesis,
            reflection_technical_missed=reflection_technical_missed,
            reflection_sentiment_missed=reflection_sentiment_missed,
            reflection_critical_insight=reflection_critical_insight,
            primary_risk=primary_risk
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=6000,
                temperature=self.temperature,
                messages=[{"role": "user", "content": full_prompt}],
                extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
                extra_body={
                    "output_format": {
                        "type": "json_schema",
                        "schema": TRADER_DECISION_SCHEMA
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
            
            trader_data = json.loads(json_text)

            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            trader_data['timestamp'] = timestamp
            state['trader'] = trader_data

            with DataManager() as dm:
                dm.save_trader_decision(data=trader_data)

            print("✅ Trader agent completed successfully")

        except Exception as e:
            print(f"⚠️  Trader agent error: {e}")
            print(f"Response preview: {response_text[:500] if 'response_text' in locals() else 'No response'}")

            fallback_decision = reflection_recommendation if reflection_recommendation in ['BUY', 'SELL', 'HOLD', 'WAIT'] else 'WAIT'
            fallback_confidence = (0.4 * tech_confidence + 0.3 * sentiment_confidence + 0.3 * reflection_confidence) * 0.8

            state['trader'] = {
                'recommendation_signal': fallback_decision,
                'market_condition': 'NEUTRAL',
                'confidence': {
                    'score': round(fallback_confidence, 2),
                    'reasoning': f'Trader synthesis failed - using Reflection ({fallback_decision}, {reflection_confidence:.0%}) as fallback. Technical {tech_recommendation} ({tech_confidence:.0%}), Sentiment {sentiment_recommendation} ({sentiment_confidence:.0%}). Weighted avg {fallback_confidence:.0%}. Error: {str(e)[:100]}'
                },
                'timestamp': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                'thinking': f'Error occurred: {str(e)}',
                'final_verdict': {
                    'summary': 'Parsing error - fallback mode active',
                    'technical_says': f'{tech_recommendation} ({tech_confidence:.0%})',
                    'sentiment_says': f'{sentiment_recommendation} ({sentiment_confidence:.0%})',
                    'reflection_says': f'{reflection_recommendation} ({reflection_confidence:.0%})',
                    'my_decision': 'Using Reflection as safest fallback due to analysis error'
                },
                'trade_setup': {
                    'status': 'WAIT_FOR_SETUP',
                    'entry_price': tech_entry or 0,
                    'stop_loss': tech_stop or 0,
                    'take_profit': tech_target or 0,
                    'risk_reward': tech_risk_reward or 0,
                    'position_size': '0% - Analysis error',
                    'timeframe': tech_timeframe or 'N/A',
                    'setup_explanation': 'Re-run trader analysis before entering any position'
                },
                'action_plan': {
                    'for_new_traders': 'Do not enter. Re-run complete analysis before trading.',
                    'for_current_holders': 'Hold existing positions. Monitor stop loss levels. Re-run analysis.',
                    'entry_conditions': ['Re-run complete analysis successfully'],
                    'exit_conditions': ['Use existing stop loss levels', 'Exit on any major adverse price movement']
                },
                'what_to_monitor': {
                    'critical_next_48h': ['Re-run trader agent', 'Monitor existing stop losses'],
                    'daily_checks': ['System status', 'Existing position stop losses'],
                    'exit_immediately_if': ['Stop loss hit', 'Major negative news']
                },
                'risk_assessment': {
                    'main_risk': f'Analysis error occurred: {str(e)[:150]}. High uncertainty until successful re-run.',
                    'why_this_position_size': 'Zero position due to parsing failure and high uncertainty',
                    'what_kills_this_trade': ['Analysis failed - cannot assess trade validity', 'Re-run required before any trading decisions']
                }
            }

            print(f"  FALLBACK DECISION: {fallback_decision} ({fallback_confidence:.0%})")

        return state


if __name__ == "__main__":
    test_state = AgentState()

    test_state['technical'] = {
        'timestamp': '2026-01-13T14:00:00Z',
        'recommendation_signal': 'WAIT',
        'confidence': {
            'score': 0.57,
            'reasoning': 'Moderate confidence in WAIT - dead volume (0.65x for 41 days) invalidates bullish setup despite MACD divergence. Need volume >1.0x to confirm any move.'
        },
        'market_condition': 'QUIET',
        'thinking': 'Market consolidating but dead volume undermines all signals',
        'analysis': {
            'trend': {
                'direction': 'NEUTRAL',
                'strength': 'WEAK'
            },
            'momentum': {
                'direction': 'BULLISH',
                'strength': 'WEAK'
            },
            'volume': {
                'quality': 'DEAD',
                'ratio': 0.65
            }
        },
        'trade_setup': {
            'viability': 'INVALID',
            'entry': 0,
            'stop_loss': 0,
            'take_profit': 0,
            'risk_reward': 0,
            'current_price': 128.4,
            'timeframe': 'N/A'
        }
    }

    test_state['sentiment'] = {
        'recommendation_signal': 'HOLD',
        'market_condition': 'NEUTRAL',
        'confidence': {
            'score': 0.65,
            'reasoning': 'Moderate confidence (0.65) - CFGI at 55 (Neutral) with high retail excitement but weak whale support. RWA momentum positive but news aging.'
        },
        'market_fear_greed': {
            'score': 55,
            'classification': 'Neutral'
        },
        'key_events': [
            {'title': 'Solana RWA Momentum', 'source': 'CoinTelegraph', 'published_at': '2026-01-02'},
            {'title': 'Whale Accumulation', 'source': 'Santiment', 'published_at': '2026-01-01'}
        ],
        'risk_flags': ['Brief stablecoin depeg', 'Memecoin perception challenge']
    }

    test_state['reflection'] = {
        'recommendation_signal': 'WAIT',
        'market_condition': 'MIXED',
        'confidence': {
            'score': 0.58,
            'reasoning': 'Technical and Sentiment both cautious due to volume. Alignment score 0.75 but dead volume (0.65x) is dealbreaker. WAIT until volume >1.0x confirms institutional interest.'
        },
        'agent_alignment': {
            'alignment_score': 0.75,
            'synthesis': 'Both agents cautious - Technical flags dead volume, Sentiment sees aging news'
        },
        'blind_spots': {
            'technical_missed': 'Positive RWA momentum in ecosystem',
            'sentiment_missed': 'Volume warning from Technical analysis',
            'critical_insight': 'Volume must confirm before trusting any setup'
        },
        'primary_risk': 'Dead volume (0.65x for 41 days) means no institutional conviction backing any move'
    }


    agent = TraderAgent()
    result_state = agent.execute(test_state)

    print("\n📊 Trader Output:")
    trader = result_state.get('trader', {})
    print(f"  Final Decision: {trader.get('recommendation_signal', 'N/A')}")
    print(f"  Market Condition: {trader.get('market_condition', 'N/A')}")
    print(f"  Final Confidence: {trader.get('confidence', {}).get('score', 0):.0%}")
    print(f"  Trade Status: {trader.get('trade_setup', {}).get('status', 'N/A')}")
    print(f"\n  Confidence Reasoning:")
    print(f"  {trader.get('confidence', {}).get('reasoning', 'N/A')}")
    print(f"\n  My Decision:")
    print(f"  {trader.get('final_verdict', {}).get('my_decision', 'N/A')}")

    print("\n✅ Test complete!")
