# Trader.py


import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.database.data_manager import DataManager

SYSTEM_PROMPT = """You are the CHIEF TRADING OFFICER making final trading decisions on SOLANA (SOL/USDT) swing trades.

You have 20 years of experience synthesising multi-agent analysis into actionable trading decisions. Your specialty is translating complex analysis into clear, executable trading plans for beginner and intermediate traders.

YOUR ROLE:
- Review and synthesise all 3 expert analyses: Technical, Sentiment, Reflection
- Weight their inputs appropriately: Technical 40% (timing/chart), Sentiment 30% (catalysts/news), Reflection 30% (synthesis/blind spots)
- Make final trading decisions: BUY/SELL/HOLD/WAIT
- Provide clear execution guidance that works for both new entries and existing positions
- Explain complex analysis in simple, actionable terms

YOUR DECISION FRAMEWORK:
- Technical drives TIMING (when to enter/exit based on charts)
- Sentiment drives CONVICTION (news catalysts that justify the trade)
- Reflection catches BLIND SPOTS (what everyone missed) and resolves conflicts
- WAIT is valid - it's discipline when edge is unclear
- Position sizing reflects confidence (lower confidence = smaller size)
- Every trade needs specific entry, stop, target, and monitoring plan

YOUR COMMUNICATION STYLE:
- Clear and direct - no jargon unless necessary
- Actionable - traders should know exactly what to do
- Honest - admit when confidence is low or signals are mixed
- Educational - explain WHY not just WHAT
- Risk-focused - always highlight the main danger

CRITICAL RULES:
- Always cite specific agent scores when synthesizing (e.g., "Technical BUY 0.72, Sentiment BULLISH 0.65")
- Show your confidence calculation logic transparently
- Provide separate guidance for new traders vs existing holders
- Every price level needs a reason (don't just say "$184 entry" - explain WHY)
- If signals conflict, resolve it - don't just say "mixed signals"
- Dead volume (<0.7x) or lack of trade setup levels = automatic WAIT
"""



TRADER_PROMPT = """
<technical_analysis>
**Recommendation:** {tech_recommendation}
**Confidence:** {tech_confidence:.0%}
**Market Condition:** {tech_market_condition}

**Summary:** {tech_summary}

**Trade Setup:**
- Entry: ${tech_entry}
- Stop Loss: ${tech_stop}
- Take Profit: ${tech_target}
- Risk/Reward: {tech_risk_reward}
- Timeframe: {tech_timeframe}

**Key Factors:**
- Volume Ratio: {volume_ratio:.2f}x average
- Volume Quality: {volume_quality}

**Confidence Reasoning:** {tech_confidence_reasoning}
</technical_analysis>

<sentiment_analysis>
**Recommendation:** {sentiment_recommendation}
**Confidence:** {sentiment_confidence:.0%}
**Market Condition:** {sentiment_market_condition}

**Summary:** {sentiment_summary}

**Key Factors:**
- Fear & Greed Index: {cfgi_score}/100 ({cfgi_classification})
- Positive Catalysts: {positive_catalysts}
- Negative Risks: {negative_risks}

**Key Events:**
{sentiment_key_events_formatted}

**Risk Flags:**
{sentiment_risk_flags_formatted}

**Confidence Reasoning:** {sentiment_confidence_reasoning}
</sentiment_analysis>

<reflection_analysis>
**Recommendation:** {reflection_recommendation}
**Confidence:** {reflection_confidence:.0%}
**Market Condition:** {reflection_market_condition}

**Summary:** {reflection_summary}

**Agent Alignment:**
- Alignment Score: {alignment_score:.0%}
- Synthesis: {reflection_synthesis}

**Blind Spots:**
- Technical Missed: {reflection_technical_missed}
- Sentiment Missed: {reflection_sentiment_missed}
- Critical Insight: {reflection_critical_insight}

**Primary Risk:** {primary_risk}

**Confidence Reasoning:** {reflection_confidence_reasoning}
</reflection_analysis>

---

<instructions>
## YOUR TASK

Analyze all 3 agents and create a final trading decision using chain-of-thought reasoning.

You MUST:
1. First, write your detailed reasoning inside <thinking> tags
2. Then, provide your final decision as JSON inside <answer> tags

### THINKING PROCESS (inside <thinking> tags):

Work through these steps IN ORDER:

## STEP 1: AGENT CONSENSUS CHECK

Look at the three recommendations:
- Technical: {tech_recommendation} ({tech_confidence:.0%})
- Sentiment: {sentiment_recommendation} ({sentiment_confidence:.0%})
- Reflection: {reflection_recommendation} ({reflection_confidence:.0%})

Write 3-4 sentences analyzing:
- Do all 3 agree (same direction) = STRONG CONSENSUS?
- Do 2 out of 3 agree = MODERATE CONSENSUS?
- Do all disagree = NO CONSENSUS → likely WAIT?
- What's the CORE agreement or disagreement? Be specific (e.g., "Technical and Sentiment see bullish setup but Reflection flags volume risk")

## STEP 2: WEIGHTED CONFIDENCE CALCULATION

Calculate weighted confidence using these weights:
- Technical: 40% (timing is critical in swing trading)
- Sentiment: 30% (catalysts matter in crypto)
- Reflection: 30% (catches blind spots)

**Show your math step-by-step:**
```
Base = (0.40 × {tech_confidence}) + (0.30 × {sentiment_confidence}) + (0.30 × {reflection_confidence})
Base = (0.40 × [X]) + (0.30 × [Y]) + (0.30 × [Z])
Base = [calculation] = [base_score]
```

**Apply adjustments:**
- Volume dead (<0.7x): -0.08
- Volume weak (<1.0x): -0.05
- High risk flagged by Reflection: -0.05
- Strong consensus (all 3 agree): +0.05
- Conflict (all disagree): -0.10

**Show adjusted calculation:**
```
Adjusted = [base_score] + [list each adjustment]
Final confidence = [final_score]
```

Write 1-2 sentences explaining what this final confidence score means for the trade.

## STEP 3: ANALYZE EACH AGENT'S CONTRIBUTION

**A) TECHNICAL ANALYST:**
Write 2-3 sentences covering:
- What's their strongest signal? (chart pattern, momentum, volume?)
- Are the trade levels (entry/stop/target) valid and actionable?
- What did they miss that others caught?
- Trust level: HIGH/MEDIUM/LOW and why?

**B) SENTIMENT ANALYST:**
Write 2-3 sentences covering:
- Are the catalysts REAL (partnerships, ETFs) or just hype/speculation?
- Any critical risk flags? (regulatory, security, network issues)
- How fresh is the news? (<48h = high impact, >72h = fading impact)
- Does sentiment support or contradict Technical's setup?

**C) REFLECTION ANALYST:**
Write 2-3 sentences covering:
- What blind spots did they uncover?
- Is their risk assessment valid and actionable?
- Did they find something BOTH Technical and Sentiment missed?
- Should their caution override the bullish/bearish case?

## STEP 4: RESOLVE CONFLICTS & MAKE DECISION

If agents disagree, resolve it by answering:
- Which agent has stronger EVIDENCE for their view?
- Does Technical's chart setup override Sentiment concerns? Or vice versa?
- Is Reflection's caution justified by real, measurable risks?
- What's the path of LEAST REGRET if we're wrong?

**Apply decision rules:**
- Weighted confidence ≥0.65 AND 2+ agents agree → BUY/SELL (confident trade)
- Weighted confidence 0.50-0.64 AND moderate consensus → BUY/SELL with reduced position
- Weighted confidence <0.50 OR no consensus → HOLD/WAIT (no edge)
- Dead volume (<0.7x) → WAIT regardless of other signals
- No valid trade levels from Technical → WAIT (can't trade without levels)

Write 3-4 sentences explaining:
- Your final recommendation_signal (BUY/SELL/HOLD/WAIT)
- Why this decision makes sense given the analysis
- What would change your mind

## STEP 5: BUILD EXECUTION PLAN

Create specific trading guidance:

**FOR NEW TRADERS (wanting to enter):**
Write 2-3 sentences:
- Should they enter NOW or WAIT for better conditions?
- If wait, what specific conditions? (price level, volume, timeframe)
- Example: "Don't enter yet. Set alert at $184 and wait for volume >1.5x within 48h"

**FOR CURRENT HOLDERS:**
Write 2-3 sentences:
- Should they hold, take profits, or exit?
- Specific price levels for partial/full exits?
- Example: "Take 50% profit at $191, move stop to breakeven, let rest run to $198"

**ENTRY CONDITIONS (if applicable):**
List 2-3 specific conditions that must be met before entering:
- Example: "Volume spike >1.5x", "Price pullback to $184", "Must happen within 48h"

**EXIT CONDITIONS:**
List 2-4 specific exit scenarios:
- Profit targets: "Take 50% at $191, rest at $198"
- Time limit: "Exit all by day 5 regardless"
- Stop loss: "Hard stop at $176"

**MONITORING CHECKLIST:**
What should trader check and when?
- Critical next 24-48h: What needs to happen soon?
- Daily checks: What to monitor each day?
- Red flags: What triggers immediate exit?

Write everything in clear, actionable language.

---

### CONFIDENCE GUIDELINES:

<confidence_guidelines>
## Confidence Score (0.15-1.0)
How confident are you in this final recommendation after synthesizing all 3 agents?

- 0.80-1.00: Very high - Strong consensus, clear edge, minimal risks
- 0.65-0.79: High - Good alignment, manageable risks, solid setup
- 0.50-0.64: Moderate - Some conflicts but edge exists, watch closely
- 0.35-0.49: Low - Significant conflicts or unclear edge, be cautious
- 0.15-0.34: Very low - Major conflicts or no edge, avoid trading

## Confidence Reasoning (CRITICAL)
Write 3-4 sentences that tell the complete synthesis story:

**Must include:**
1. All 3 agents' views with scores: "Technical BUY (0.72), Sentiment BULLISH (0.65), Reflection WAIT (0.57)"
2. Weighted calculation result: "Weighted base 0.66, volume adjustment -0.08 = 0.58 final"
3. Key factor that tips decision: "Dead volume is dealbreaker despite bullish alignment"
4. Clear connection to recommendation: "Therefore WAIT until volume >1.5x confirms institutions buying"

**Write naturally** - connect the dots, tell the story
**Be specific** - cite actual numbers, price levels, timeframes
**No generic phrases** like "agents partially align" or "mixed signals"

**GOOD Example:**
"Technical screams BUY (0.72) on breakout with 3.2:1 R/R, Sentiment confirms BULLISH (0.65) with Morgan Stanley ETF catalyst, but Reflection urges WAIT (0.57) flagging dead volume. Weighted base 0.66 drops to 0.58 after volume penalty (-0.08). Despite strong bullish alignment, volume at 0.56x for 43 days means institutions aren't buying yet. Final call: WAIT with 58% confidence until volume >1.5x proves the rally has institutional backing."

**BAD Example:**
"Moderate confidence based on mixed agent signals and some concerns about market conditions."
</confidence_guidelines>

---

### OUTPUT FORMAT:

After your thinking, output the final JSON inside <answer> tags. The JSON must follow this EXACT structure:
```json
{{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",
  
  "market_condition": "BULLISH|BEARISH|NEUTRAL|BULLISH_BUT_CAUTIOUS|BEARISH_BUT_WATCHING",
  
  "confidence": {{
    "score": 0.58,
    "reasoning": "Write 3-4 sentences: [All 3 agents' views with scores] → [Weighted calculation with adjustments] → [Key factor that tips decision] → [Clear link to recommendation]. Be specific with numbers and tell the story naturally."
  }},
  
  "timestamp": "2026-01-06T12:34:56Z",
  
  "final_verdict": {{
    "summary": "Write 2-3 sentences giving the big picture: What's happening in the market? What's the main opportunity or concern? Why this recommendation makes sense now.",
    
    "technical_says": "BUY (72%) - Brief summary of their key point",
    "sentiment_says": "BULLISH (65%) - Brief summary of their key point",
    "reflection_says": "WAIT (57%) - Brief summary of their key point",
    
    "my_decision": "Write 2-3 sentences explaining YOUR final call: Why did you weight things this way? What's the deciding factor? What makes this the right decision?"
  }},
  
  "trade_setup": {{
    "status": "READY_TO_ENTER|WAIT_FOR_SETUP|HOLD_POSITION|EXIT_RECOMMENDED",
    "entry_price": 184.00,
    "stop_loss": 176.00,
    "take_profit": 198.00,
    "risk_reward": 1.75,
    "position_size": "50% of normal position",
    "timeframe": "3-5 days",
    "setup_explanation": "Write 2-3 sentences explaining the trade math: Entry at $X offers Y:1 reward with stop at $Z (N% risk). Target $A within B days. Position sizing logic based on confidence."
  }},
  
  "action_plan": {{
    "for_new_traders": "Write 2-4 sentences with specific guidance for someone wanting to ENTER: Should they buy now or wait? If wait, what conditions? What price levels? Be clear and actionable.",
    
    "for_current_holders": "Write 2-4 sentences for someone ALREADY IN THE TRADE: Should they hold, take profits, or exit? At what price levels? How to manage stops? Be specific.",
    
    "entry_conditions": [
      "Specific condition 1 that must be met (e.g., 'Volume spike >1.5x average')",
      "Specific condition 2 (e.g., 'Price pullback to $184 support')",
      "Timing constraint (e.g., 'Both must happen within 48 hours')"
    ],
    
    "exit_conditions": [
      "Profit target 1 (e.g., 'Take 50% profit at $191 resistance')",
      "Profit target 2 (e.g., 'Take remaining 50% at $198 OR day 5, whichever first')",
      "Stop loss (e.g., 'Hard stop at $176 - exit immediately if hit')",
      "Other exit scenarios (e.g., 'Exit if volume drops <0.7x for 24h')"
    ]
  }},
  
  "what_to_monitor": {{
    "critical_next_48h": [
      "Most urgent thing to watch 1 (e.g., 'Volume must surge >1.5x to validate entry')",
      "Most urgent thing to watch 2 (e.g., 'Price holding $184 support')",
      "Most urgent thing to watch 3 (e.g., 'Morgan Stanley ETF news updates')"
    ],
    
    "daily_checks": [
      "Daily monitoring item 1 (e.g., 'Is volume staying >1.0x? Below = consider exit')",
      "Daily monitoring item 2 (e.g., 'Price holding above $176 stop?')",
      "Daily monitoring item 3 (e.g., 'Any negative Solana news - outages, hacks?')"
    ],
    
    "exit_immediately_if": [
      "Red flag 1 (e.g., 'Price breaks below $176 stop loss')",
      "Red flag 2 (e.g., 'Volume drops to <0.7x for 24+ hours')",
      "Red flag 3 (e.g., 'Major negative news - SEC action, network failure')"
    ]
  }},
  
  "risk_assessment": {{
    "main_risk": "Write 2-3 sentences identifying the PRIMARY risk that could kill this trade: What's the biggest danger? Why does it matter? How likely is it?",
    
    "why_this_position_size": "Write 1-2 sentences explaining position sizing logic: Why 50% vs 100%? How does confidence level affect sizing? Link to risk management.",
    
    "what_kills_this_trade": [
      "Invalidation scenario 1 (e.g., 'Stop loss hit at $176 = 4.3% loss')",
      "Invalidation scenario 2 (e.g., 'Volume stays dead <1.0x for 48h = no edge')",
      "Invalidation scenario 3 (e.g., 'BTC crashes >5% = SOL follows down due to correlation')"
    ]
  }}
}}
```

IMPORTANT NOTES:
- Write your full reasoning in <thinking> tags FIRST
- Then output ONLY valid JSON in <answer> tags
- All numeric values should be numbers, not strings
- All text explanations should be clear, specific, and actionable
- Every recommendation needs a "why" - never just state what to do
- If recommendation is WAIT, set status to "WAIT_FOR_SETUP" and explain what you're waiting for
- market_condition can use modifiers like "BULLISH_BUT_CAUTIOUS" to show nuance
</instructions>

---

<critical_rules>
1. **NO CONSENSUS = WAIT**: If all 3 agents disagree, MUST return WAIT
2. **LOW CONFIDENCE = WAIT**: If weighted_confidence <0.50, MUST return HOLD or WAIT
3. **NO TRADE LEVELS = WAIT**: If Technical has no entry/stop/target, MUST return WAIT
4. **DEAD VOLUME = WAIT**: If volume <0.7x, MUST return WAIT regardless of other signals
5. **CRITICAL RISKS = WAIT**: If Sentiment flags major risks (delisting, hack, SEC), MUST return WAIT
6. **POSITION SIZING**: Must scale with confidence (>0.75 = 70-100%, 0.65-0.75 = 50-70%, 0.50-0.64 = 30-50%, <0.50 = 0%)
7. **SHOW MATH**: confidence.reasoning MUST include weighted calculation
8. **BE SPECIFIC**: Every price level, timeframe, condition must have a reason
9. **RESOLVE CONFLICTS**: Don't just say "mixed signals" - explain which agent wins and why
10. **ACTIONABLE LANGUAGE**: Write for traders who need to execute, not analysts who want theory
</critical_rules>

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
            model="claude-3-5-haiku-20241022",
            temperature=0.2  
        )

    def execute(self, state: AgentState) -> AgentState:
        tech = state.get('technical', {})
        sentiment = state.get('sentiment', {})
        reflection = state.get('reflection', {})

        # Technical data extraction
        tech_recommendation = tech.get('recommendation_signal', 'HOLD')
        tech_confidence_obj = tech.get('confidence', {})
        tech_confidence = float(tech_confidence_obj.get('score', 0.5)) if isinstance(tech_confidence_obj, dict) else 0.5
        tech_market_condition = tech.get('market_condition', 'QUIET')
        tech_summary = tech_confidence_obj.get('reasoning', 'No technical reasoning provided')
        tech_confidence_reasoning = tech_confidence_obj.get('reasoning', 'No reasoning provided')

        tech_entry = get_nested(tech, 'trade_setup.entry', 0.0)
        tech_stop = get_nested(tech, 'trade_setup.stop_loss', 0.0)
        tech_target = get_nested(tech, 'trade_setup.take_profit', 0.0)
        tech_risk_reward = get_nested(tech, 'trade_setup.risk_reward', 0.0)
        tech_timeframe = get_nested(tech, 'trade_setup.timeframe', 'N/A')
        volume_ratio = get_nested(tech, 'analysis.volume.ratio', 1.0)
        volume_quality = get_nested(tech, 'analysis.volume.quality', 'UNKNOWN')

        # Sentiment data extraction
        sentiment_recommendation = sentiment.get('recommendation_signal', 'HOLD')
        sentiment_confidence_obj = sentiment.get('confidence', {})
        sentiment_confidence = float(sentiment_confidence_obj.get('score', 0.5)) if isinstance(sentiment_confidence_obj, dict) else 0.5
        sentiment_market_condition = sentiment.get('market_condition', 'NEUTRAL')
        sentiment_summary = sentiment_confidence_obj.get('reasoning', 'No sentiment reasoning provided')
        sentiment_confidence_reasoning = sentiment_confidence_obj.get('reasoning', 'No reasoning provided')

        cfgi_data = sentiment.get('market_fear_greed', {})
        cfgi_score = cfgi_data.get('score', 50)
        cfgi_classification = cfgi_data.get('classification', 'Neutral')

        positive_catalysts = sentiment.get('positive_catalysts', 0)
        negative_risks = sentiment.get('negative_risks', 0)

        sentiment_key_events = sentiment.get('key_events', [])
        sentiment_key_events_formatted = "\n".join([f"- {e.get('title', 'Unknown')} ({e.get('source', 'Unknown')}, {e.get('date', 'Unknown')})" for e in sentiment_key_events]) if sentiment_key_events else "- None"

        sentiment_risk_flags = sentiment.get('risk_flags', [])
        sentiment_risk_flags_formatted = "\n".join([f"- {flag}" for flag in sentiment_risk_flags]) if sentiment_risk_flags else "- None"

        # Reflection data extraction
        reflection_recommendation = reflection.get('recommendation_signal', 'HOLD')
        reflection_confidence_obj = reflection.get('confidence', {})
        reflection_confidence = float(reflection_confidence_obj.get('score', 0.5)) if isinstance(reflection_confidence_obj, dict) else 0.5
        reflection_market_condition = reflection.get('market_condition', 'MIXED')
        reflection_summary = reflection_confidence_obj.get('reasoning', 'No reflection reasoning provided')
        reflection_confidence_reasoning = reflection_confidence_obj.get('reasoning', 'No reasoning provided')

        alignment_score = get_nested(reflection, 'agent_alignment.alignment_score', 0.5)
        reflection_synthesis = get_nested(reflection, 'agent_alignment.synthesis', 'No synthesis available')

        blind_spots = reflection.get('blind_spots', {})
        reflection_technical_missed = blind_spots.get('technical_missed', 'None identified')
        reflection_sentiment_missed = blind_spots.get('sentiment_missed', 'None identified')
        reflection_critical_insight = blind_spots.get('critical_insight', 'None identified')

        primary_risk = reflection.get('primary_risk', 'No primary risk identified')

        # Format prompt variables
        full_prompt = SYSTEM_PROMPT + "\n\n" + TRADER_PROMPT.format(
            tech_recommendation=tech_recommendation,
            tech_confidence=tech_confidence,
            tech_market_condition=tech_market_condition,
            tech_summary=tech_summary,
            tech_entry=tech_entry if tech_entry else "N/A",
            tech_stop=tech_stop if tech_stop else "N/A",
            tech_target=tech_target if tech_target else "N/A",
            tech_risk_reward=tech_risk_reward if tech_risk_reward else "N/A",
            tech_timeframe=tech_timeframe,
            volume_ratio=volume_ratio,
            volume_quality=volume_quality,
            tech_confidence_reasoning=tech_confidence_reasoning,
            sentiment_recommendation=sentiment_recommendation,
            sentiment_confidence=sentiment_confidence,
            sentiment_market_condition=sentiment_market_condition,
            sentiment_summary=sentiment_summary,
            cfgi_score=cfgi_score,
            cfgi_classification=cfgi_classification,
            positive_catalysts=positive_catalysts,
            negative_risks=negative_risks,
            sentiment_key_events_formatted=sentiment_key_events_formatted,
            sentiment_risk_flags_formatted=sentiment_risk_flags_formatted,
            sentiment_confidence_reasoning=sentiment_confidence_reasoning,
            reflection_recommendation=reflection_recommendation,
            reflection_confidence=reflection_confidence,
            reflection_market_condition=reflection_market_condition,
            reflection_summary=reflection_summary,
            alignment_score=alignment_score,
            reflection_synthesis=reflection_synthesis,
            reflection_technical_missed=reflection_technical_missed,
            reflection_sentiment_missed=reflection_sentiment_missed,
            reflection_critical_insight=reflection_critical_insight,
            primary_risk=primary_risk,
            reflection_confidence_reasoning=reflection_confidence_reasoning
        )

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=3000
        )

        try:
            # Extract thinking
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            thinking = thinking_match.group(1).strip() if thinking_match else ""

            # Extract JSON from answer tags
            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            answer_json = answer_match.group(1).strip() if answer_match else re.search(r'\{.*\}', response, re.DOTALL).group(0)

            # Minimal JSON cleaning
            answer_json = re.sub(r'^```json\s*|\s*```$', '', answer_json.strip())
            answer_json = answer_json[answer_json.find('{'):answer_json.rfind('}')+1]

            # Parse and save
            trader_data = json.loads(answer_json)
            trader_data['thinking'] = thinking
            state['trader'] = trader_data

            with DataManager() as dm:
                dm.save_trader_decision(data=trader_data)

        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            print(f"⚠️  Trader agent parsing error: {e}")
            print(f"Response preview: {response[:500]}")

            # Simplified fallback using Reflection as most reliable
            fallback_decision = reflection_recommendation if reflection_recommendation in ['BUY', 'SELL', 'HOLD', 'WAIT'] else 'WAIT'
            fallback_confidence = (0.4 * tech_confidence + 0.3 * sentiment_confidence + 0.3 * reflection_confidence) * 0.8

            state['trader'] = {
                'recommendation_signal': fallback_decision,
                'market_condition': 'NEUTRAL',
                'confidence': {
                    'score': fallback_confidence,
                    'reasoning': f'Trader synthesis failed - using Reflection ({fallback_decision}, {reflection_confidence:.0%}) as fallback. Technical {tech_recommendation} ({tech_confidence:.0%}), Sentiment {sentiment_recommendation} ({sentiment_confidence:.0%}). Weighted avg {fallback_confidence:.0%}. Error: {str(e)[:100]}'
                },
                'timestamp': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                'final_verdict': {
                    'summary': 'Parsing error - fallback mode active',
                    'technical_says': f'{tech_recommendation} ({tech_confidence:.0%})',
                    'sentiment_says': f'{sentiment_recommendation} ({sentiment_confidence:.0%})',
                    'reflection_says': f'{reflection_recommendation} ({reflection_confidence:.0%})',
                    'my_decision': 'Using Reflection as safest fallback'
                },
                'trade_setup': {
                    'status': 'WAIT_FOR_SETUP',
                    'entry_price': tech_entry or 0,
                    'stop_loss': tech_stop or 0,
                    'take_profit': tech_target or 0,
                    'risk_reward': tech_risk_reward or 0,
                    'position_size': '0%',
                    'timeframe': tech_timeframe or 'N/A',
                    'setup_explanation': 'Re-run trader analysis'
                },
                'action_plan': {
                    'for_new_traders': 'Re-run complete analysis before entering',
                    'for_current_holders': 'Hold until new analysis available',
                    'entry_conditions': ['Re-run complete analysis'],
                    'exit_conditions': ['Use current stop loss levels']
                },
                'what_to_monitor': {
                    'critical_next_48h': ['Re-run trader agent'],
                    'daily_checks': ['Monitor existing positions'],
                    'exit_immediately_if': ['Stop loss hit']
                },
                'risk_assessment': {
                    'main_risk': f'Analysis error: {str(e)[:100]}',
                    'why_this_position_size': 'Zero position due to parsing failure',
                    'what_kills_this_trade': ['Parsing failed - high uncertainty']
                },
                'thinking': f'Error: {str(e)}'
            }

            print(f"  FALLBACK DECISION: {fallback_decision} ({fallback_confidence:.0%})")

        return state


if __name__ == "__main__":
    agent = TraderAgent()
    test_state = AgentState()

    # Test state with NEW schema
    test_state['technical'] = {
        'timestamp': '2025-01-02T15:30:00Z',
        'recommendation_signal': 'BUY',
        'confidence': {
            'score': 0.72,
            'reasoning': 'High confidence (0.82) in this BUY - price broke above EMA50 at $145 with volume surging to 1.8x average, confirming institutional interest. RSI at 66 is healthy (not overbought), and the $142 support gives us a clean 3.2:1 risk/reward setup for a 3-5 day swing.'
        },
        'market_condition': 'TRENDING',
        'trade_setup': {
            'viability': 'VALID',
            'entry': 145.50,
            'stop_loss': 142.00,
            'take_profit': 155.00,
            'risk_reward': 3.2,
            'timeframe': '3-7 days'
        },
        'analysis': {
            'volume': {
                'quality': 'STRONG',
                'ratio': 1.8
            }
        }
    }

    test_state['sentiment'] = {
        'recommendation_signal': 'BUY',
        'market_condition': 'BULLISH',
        'confidence': {
            'score': 0.65,
            'reasoning': 'High confidence (0.65) - CFGI at 72 (Greed) but justified by genuine catalysts: Morgan Stanley ETF filing (Jan 6, CoinDesk) and Ondo Finance tokenization partnership (Dec 24, official).'
        },
        'market_fear_greed': {
            'score': 72,
            'classification': 'Greed'
        },
        'positive_catalysts': 2,
        'negative_risks': 0,
        'key_events': [
            {'title': 'Morgan Stanley ETF filing', 'source': 'CoinDesk', 'date': 'Jan 6'},
            {'title': 'Ondo Finance partnership', 'source': 'Official', 'date': 'Dec 24'}
        ],
        'risk_flags': []
    }

    test_state['reflection'] = {
        'recommendation_signal': 'WAIT',
        'market_condition': 'MIXED',
        'confidence': {
            'score': 0.57,
            'reasoning': 'Technical says BUY (0.72 setup) but flags dead volume at 0.56x for 43 days. Sentiment bullish (0.65) on Morgan Stanley ETF filing. They align on direction (0.85 score) but disagree on timing.'
        },
        'agent_alignment': {
            'alignment_score': 0.85,
            'synthesis': 'Both Technical and Sentiment see bullish setup but Technical cautions on dead volume timing'
        },
        'blind_spots': {
            'technical_missed': 'Did not account for positive sentiment catalysts impact',
            'sentiment_missed': 'Overlooked the dead volume warning from Technical',
            'critical_insight': 'Volume must confirm before trusting news-driven rallies'
        },
        'primary_risk': 'Dead volume (0.56x for 43 days) means bullish setup lacks institutional conviction.'
    }

    result = agent.execute(test_state)

    if result.get('trader'):
        trader = result['trader']
        print("\n" + "="*70)
        print("TRADER AGENT OUTPUT")
        print("="*70)
        print(json.dumps(trader, indent=2))
    else:
        print("\nTEST FAILED: No trader output")
