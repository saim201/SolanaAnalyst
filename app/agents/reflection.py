# reflection.py

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.database.data_manager import DataManager
from app.agents.reflection_helpers import (
    get_nested,
    calculate_alignment_score,
    calculate_bayesian_confidence,
    assess_risk_level,
    normalize_direction
)


SYSTEM_PROMPT = """You are a SENIOR TRADING STRATEGIST with 20 years experience in crypto markets, specialising in synthesising multi-agent analysis for Solana (SOL) swing trading.

YOUR ROLE:
- Review Technical and Sentiment analyst analyses
- Identify blind spots (what each analyst missed)
- Assess agreement/conflict between analysts
- Calculate risk-adjusted confidence
- Provide unified actionable recommendation_signal

YOUR EXPERTISE:
- Finding what analysts overlook (blind spot detection)
- Bayesian confidence fusion (combining probabilistic signals)
- Risk assessment (identifying primary threats)
- Synthesis (turning conflicting signals into clear decisions)

YOUR STYLE:
- Honest: If confidence is low, say so
- Risk-focused: Always identify the primary risk
- Decisive: Provide clear recommendations
- Transparent: Show your reasoning steps

YOUR OUTPUT REQUIREMENTS:
- market_condition: Agent alignment status (ALIGNED/CONFLICTED/MIXED)
- confidence.reasoning: Tell the story of how Technical + Sentiment combine. Cite their specific scores, disagreements, and why this leads to your recommendation. Paint a picture.
- synthesis: Don't just say "they agree/disagree" - explain WHAT they agree/disagree on with specifics
- blind_spots: Not just lists - explain WHY each blind spot matters and HOW it changes the analysis
- Connect everything: risk → confidence → recommendation in a natural flow
"""


REFLECTION_PROMPT = """
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

**Volume Analysis:**
- Volume Ratio: {volume_ratio:.2f}x average
- Volume Quality: {volume_quality}

**Analysis:**
{tech_analysis_formatted}

**Watch List:**
{tech_watch_list_formatted}

**Invalidation:**
{tech_invalidation_formatted}

**Confidence Reasoning:**
{tech_confidence_reasoning_formatted}
</technical_analysis>

<sentiment_analysis>
**Signal:** {sentiment_signal}
**Confidence:** {sentiment_confidence:.0%}

**CFGI Fear & Greed:**
- Score: {cfgi_score}/100 ({cfgi_classification})
- Interpretation: {cfgi_interpretation}

**News Sentiment:**
- Score: {news_sentiment_score:.0%}
- Label: {news_sentiment_label}

**Key Events:**
{sentiment_key_events_formatted}

**Risk Flags:**
{sentiment_risk_flags_formatted}

**Summary:** {sentiment_summary}

**What to Watch:**
{sentiment_what_to_watch_formatted}

**Invalidation:** {sentiment_invalidation}
</sentiment_analysis>

---

<instructions>
## YOUR TASK

Analyse the above data using **FOCUSED 4-PHASE FRAMEWORK**.

Your job is QUALITATIVE ANALYSIS ONLY. The code will handle all calculations (alignment scores, risk levels, confidence scores).

### CONFIDENCE GUIDELINES

<confidence_guidelines>
## Confidence Score (0.15-1.0)
After synthesising Technical + Sentiment, how confident are you in the final recommendation?

- 0.80-1.00: Very high - both agents strongly aligned, clear edge
- 0.65-0.79: High - good alignment, manageable risks
- 0.50-0.64: Moderate - some conflicts but edge exists
- 0.35-0.49: Low - significant conflicts or unclear edge
- 0.15-0.34: Very low - major conflicts, wait for clarity

## Confidence Reasoning (CRITICAL)
Write 2-3 sentences that tell the synthesis story:

**Must include**:
- Both agents' recommendations + scores (e.g., "Technical BUY 0.72, Sentiment BULLISH 0.65")
- Specific point of agreement or conflict (volume, timing, risk)
- Key data that tips the decision (volume ratio, news date, price level)
- WHY this leads to your recommendation + confidence

**Natural storytelling** - connect Technical + Sentiment into coherent picture
 **No generic statements** like "agents partially align"
 **No listing without context**

**GOOD Examples**:

"Technical screams BUY (0.72) on clean breakout with 3.2:1 R/R, and Sentiment confirms with Morgan Stanley ETF catalyst (0.65), creating 0.85 alignment. However, volume is dead at 0.56x for 43 days - institutions haven't shown up yet. Despite strong alignment, dead volume drops confidence to 58% for WAIT: need volume >1.5x to prove institutions are buying the story before risking capital."

"Strong conflict: Technical says WAIT (0.32) citing dead volume and overbought RSI, but Sentiment is bullish (0.68) on fresh Ondo Finance news. Alignment score 0.45 shows deep disagreement. Technical's volume data wins here - news can't move price without institutional buying pressure. Confidence 0.41 in WAIT: let volume confirm before trusting news-driven rallies."

"Perfect alignment (0.92): Technical BUY (0.78) and Sentiment BULLISH (0.75) both cite the same factors - volume surge to 1.8x, Morgan Stanley ETF, RSI healthy at 66. No blind spots found, primary risk is normal (BTC correlation). High confidence 0.82 in BUY with 3-5 day timeframe and tight stop at $142."

**BAD Examples** :

"Moderate confidence due to partial agent alignment"
→ No specifics, doesn't explain WHY moderate

"Technical and Sentiment show some agreement but also concerns"
→ Vague, no data, no story

"Confidence is 0.57 based on synthesis of both analyses"
→ Circular, doesn't explain reasoning
</confidence_guidelines>

### OUTPUT FORMAT

<thinking>

**PHASE 1: AGENT ALIGNMENT ANALYSIS**

Compare Technical ({tech_recommendation}, {tech_confidence:.0%}) vs Sentiment ({sentiment_signal}, {sentiment_confidence:.0%}):

Write 3-4 sentences explaining:
- Do they AGREE on direction (both bullish/bearish)?
- What SPECIFIC factors drive each recommendation? (cite prices, volume, news, dates)
- Where's the KEY DISAGREEMENT? (timing? risk tolerance? data interpretation?)
- What's the alignment_score telling us? (>0.80=strong, 0.60-0.80=moderate, <0.60=weak)

Example: "Technical sees BUY setup (0.72) on breakout above $145 with 3.2:1 R/R. Sentiment also bullish (0.65) citing Morgan Stanley ETF news (Jan 6). Both agree on direction (alignment 0.85) but disagree on timing: Technical demands volume >1.5x first, Sentiment thinks news is catalyst enough. The gap is whether to trust the chart pattern or the news headline."


**PHASE 2: TECHNICAL BLIND SPOTS**

What did Technical analysis MISS that Sentiment revealed?

Write 2-3 sentences for EACH blind spot:
- WHAT was missed? (specific news event, risk flag, market context)
- WHY does it matter? (how does it change Technical's thesis?)
- HOW should this affect the trade decision?

Example: "Technical focused purely on the chart breakout but completely missed the 2-hour Solana network outage on Dec 30 that Sentiment flagged from news sources. This reliability concern isn't visible in price action yet, but if another outage hits, it would trigger cascading stop-losses regardless of how bullish the chart looks. This hidden risk justifies reducing position size even with a good technical setup."


**PHASE 3: SENTIMENT BLIND SPOTS**

What did Sentiment analysis MISS that Technical revealed?

Write 2-3 sentences for EACH blind spot:
- WHAT was missed? (volume data, chart structure, momentum signals)
- WHY does it matter? (how does it change Sentiment's thesis?)
- HOW should this affect the trade decision?

Example: "Sentiment is excited about Morgan Stanley ETF filing (fresh news, reputable source) but didn't see that volume has been dead at 0.56x average for 43 straight days - institutions AREN'T buying yet. News creates POTENTIAL for a move, but Technical's volume data shows institutional money hasn't arrived. This timing gap means news-driven rallies could fail at resistance without volume follow-through."


**PHASE 4: SYNTHESIS & DECISION**

Combine everything into your recommendation:

Write 3-4 sentences covering:
- What's the OVERALL PICTURE? (both agents bullish? conflicted? one neutral?)
- What's the PRIMARY RISK that could derail this trade?
- Given alignment + blind spots + risks, what's the RIGHT MOVE? (BUY/SELL/HOLD/WAIT)
- What SPECIFIC CONDITIONS would change your mind?

Example: "Both agents lean bullish (0.85 alignment) on genuine institutional catalyst, but timing is the issue. Technical correctly demands volume proof (not seeing it at 0.56x for 43 days) before trusting the rally. Sentiment is early on the news but blind to volume reality. Smart move is WAIT with 57% confidence - if institutions start buying (volume >1.5x) within 48 hours of Morgan Stanley news, this becomes strong BUY. Without volume follow-through, it's retail hype that will dump at resistance."

</thinking>

<answer>
{{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",

  "market_condition": "ALIGNED|CONFLICTED|MIXED",

  "confidence": {{
    "score": 0.57,
    "reasoning": "Technical says [X with score], Sentiment says [Y with score]. They [agree/conflict] on [specific aspect]. Combined with [key factor like volume/risk], this gives us [recommendation] with [score]% confidence because [specific reason]."
  }},

  "timestamp": "2026-01-06T12:34:56Z",

  "agent_alignment": {{
    "technical_says": "BUY (0.72)",
    "sentiment_says": "BULLISH (0.65)",
    "alignment_score": 0.85,
    "synthesis": "Both agents lean bullish - Technical sees breakout setup above $145 (3.2:1 R/R), Sentiment confirms with Morgan Stanley ETF catalyst (Jan 6). Key gap: Technical needs volume >1.5x to confirm but Sentiment thinks fresh news is enough. Without institutional volume showing up in the data, even strong catalysts can fail at resistance."
  }},

  "blind_spots": {{
    "technical_missed": "Technical focused on chart breakout but didn't weight the 2-hour network outage (Dec 30) that Sentiment flagged. Even with bullish momentum, reliability issues can trigger cascading stop-losses and invalidate the setup overnight.",

    "sentiment_missed": "Sentiment is excited about Morgan Stanley news but missed that volume is dead at 0.56x average for 43 days - no institutional buying is showing up yet. News creates potential, but Technical's volume data shows institutions haven't arrived. This timing gap is critical.",

    "critical_insight": "The real trade decision hinges on volume: if institutions start buying (volume >1.5x) within 48 hours of the Morgan Stanley news, this becomes a strong BUY. Without volume follow-through, it's just retail hype that will fade at resistance. WAIT and watch volume."
  }},

  "primary_risk": "Dead volume (0.56x for 43 days) means bullish setup lacks institutional conviction. If price rallies on retail enthusiasm alone (CFGI Social 96) without institutions participating, it will dump at $144.93 resistance. This is why WAIT makes sense - we need volume proof before risking capital on news-driven hype.",

  "monitoring": {{
    "watch_next_24h": [
      "Volume spike above 1.5x average - THE signal to enter",
      "Price reaction at $144.93 resistance with volume analysis",
      "Any Morgan Stanley ETF filing updates or SEC commentary"
    ],
    "invalidation_triggers": [
      "Volume stays below 0.8x for 48 more hours - news failed to attract institutions",
      "Break below $135 support invalidates Technical's bullish structure"
    ]
  }},

  "final_reasoning": "Technical + Sentiment both lean bullish (alignment_score 0.85), but WAIT recommendation comes from their timing gap: Technical correctly demands volume proof (not seeing it at 0.56x), while Sentiment is early on the news catalyst. Smart play is wait for volume to confirm institutions are actually buying the story before committing capital."
}}
</answer>

</instructions>

<critical_rules>
1. Focus on QUALITATIVE insights - let code handle math
2. Be SPECIFIC in blind spots - name actual events, price levels, metrics
3. Make synthesis ACTIONABLE - traders need clear guidance
4. Keep reasoning CONCISE - 2-3 sentences max
5. NEVER output invalid JSON - check all brackets, commas, quotes
6. technical_view and sentiment_view will be auto-formatted
</critical_rules>
"""


class ReflectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-sonnet-4-20250514",
            temperature=0.3
        )

    def execute(self, state: AgentState) -> AgentState:
        # Extract technical data
        tech = state.get('technical', {})
        tech_recommendation = tech.get('recommendation_signal', 'HOLD')
        tech_confidence_obj = tech.get('confidence', {})
        tech_confidence = float(tech_confidence_obj.get('score', 0.5)) if isinstance(tech_confidence_obj, dict) else 0.5
        tech_market_condition = tech.get('market_condition', 'QUIET')
        tech_summary = tech_confidence_obj.get('reasoning', 'No summary')

        # Trade setup
        tech_entry = get_nested(tech, 'trade_setup.entry', 0.0)
        tech_stop = get_nested(tech, 'trade_setup.stop_loss', 0.0)
        tech_target = get_nested(tech, 'trade_setup.take_profit', 0.0)
        tech_risk_reward = get_nested(tech, 'trade_setup.risk_reward', 0.0)
        tech_timeframe = get_nested(tech, 'trade_setup.timeframe', 'N/A')
        volume_ratio = get_nested(tech, 'analysis.volume.ratio', 1.0)
        volume_quality = get_nested(tech, 'analysis.volume.quality', 'UNKNOWN')

        # Extract sentiment data
        sentiment = state.get('sentiment', {})
        sentiment_signal = sentiment.get('recommendation_signal', 'NEUTRAL')
        sentiment_confidence_obj = sentiment.get('confidence', {})
        sentiment_confidence = float(sentiment_confidence_obj.get('score', 0.5)) if isinstance(sentiment_confidence_obj, dict) else 0.5
        sentiment_summary = sentiment_confidence_obj.get('reasoning', 'No summary')

        # CFGI data
        cfgi_score = get_nested(sentiment, 'market_fear_greed.score', 50)
        cfgi_classification = get_nested(sentiment, 'market_fear_greed.classification', 'Neutral')
        cfgi_interpretation = get_nested(sentiment, 'market_fear_greed.interpretation', 'No interpretation')

        # News sentiment
        news_sentiment_score = get_nested(sentiment, 'news_sentiment.confidence', 0.5)
        news_sentiment_label = get_nested(sentiment, 'news_sentiment.sentiment', 'NEUTRAL')

        # Format lists for prompt (simple formatting)
        tech_analysis_formatted = json.dumps(tech.get('analysis', {}), indent=2) if tech.get('analysis') else "No analysis"
        tech_watch_list_formatted = json.dumps(tech.get('watch_list', {}), indent=2) if tech.get('watch_list') else "No watch list"
        tech_invalidation_formatted = '\n'.join([f"  - {item}" for item in tech.get('invalidation', [])]) if tech.get('invalidation') else "None"
        tech_confidence_reasoning_formatted = json.dumps(tech.get('confidence_reasoning', {}), indent=2) if tech.get('confidence_reasoning') else "No reasoning"

        key_events = sentiment.get('key_events', [])
        sentiment_key_events_formatted = '\n'.join([
            f"  - {e.get('title', 'Unknown')} ({e.get('type', 'Unknown')}) - {e.get('impact', 'Unknown')}"
            for e in key_events[:5]
        ]) if key_events else "No key events"

        sentiment_risk_flags_formatted = '\n'.join([f"  - {flag}" for flag in sentiment.get('risk_flags', [])]) if sentiment.get('risk_flags') else "No risk flags"
        sentiment_what_to_watch_formatted = '\n'.join([f"  - {item}" for item in sentiment.get('what_to_watch', [])]) if sentiment.get('what_to_watch') else "Nothing"
        sentiment_invalidation = sentiment.get('invalidation', 'Not specified')

        # Get data needed for calculations (only fetch once)
        from app.agents.db_fetcher import DataQuery
        with DataQuery() as dq:
            indicators_data = dq.get_indicators_data()

        btc_correlation = float(indicators_data.get('sol_btc_correlation', 0.0))
        btc_trend = indicators_data.get('btc_trend', 'NEUTRAL')
        high_14d = float(indicators_data.get('high_14d', 0.0))
        low_14d = float(indicators_data.get('low_14d', 0.0))
        current_price = get_nested(tech, 'trade_setup.current_price', 0.0)

        price_position_14d = ((current_price - low_14d) / (high_14d - low_14d)) if (high_14d > low_14d) else 0.5
        rsi_divergence_type = indicators_data.get('rsi_divergence_type', 'NONE')
        rsi_divergence_strength = float(indicators_data.get('rsi_divergence_strength', 0.0))
        cfgi_score_value = float(cfgi_score) if cfgi_score else 50.0

        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        full_prompt = SYSTEM_PROMPT + "\n\n" + REFLECTION_PROMPT.format(
            tech_recommendation=tech_recommendation,
            tech_confidence=tech_confidence,
            tech_market_condition=tech_market_condition,
            tech_summary=tech_summary,
            tech_entry=tech_entry,
            tech_stop=tech_stop,
            tech_target=tech_target,
            tech_risk_reward=tech_risk_reward,
            tech_timeframe=tech_timeframe,
            volume_ratio=volume_ratio,
            volume_quality=volume_quality,
            tech_analysis_formatted=tech_analysis_formatted,
            tech_watch_list_formatted=tech_watch_list_formatted,
            tech_invalidation_formatted=tech_invalidation_formatted,
            tech_confidence_reasoning_formatted=tech_confidence_reasoning_formatted,

            sentiment_signal=sentiment_signal,
            sentiment_confidence=sentiment_confidence,
            cfgi_score=cfgi_score,
            cfgi_classification=cfgi_classification,
            cfgi_interpretation=cfgi_interpretation,
            news_sentiment_score=news_sentiment_score,
            news_sentiment_label=news_sentiment_label,
            sentiment_key_events_formatted=sentiment_key_events_formatted,
            sentiment_risk_flags_formatted=sentiment_risk_flags_formatted,
            sentiment_summary=sentiment_summary,
            sentiment_what_to_watch_formatted=sentiment_what_to_watch_formatted,
            sentiment_invalidation=sentiment_invalidation,
            timestamp=timestamp
        )

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=3000
        )

        try:
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            thinking_text = thinking_match.group(1).strip() if thinking_match else ""

            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            json_str = answer_match.group(1).strip() if answer_match else re.search(r'\{[\s\S]*\}', response).group(0)

            json_str = re.sub(r'^```json\s*|\s*```$', '', json_str.strip())
            json_str = json_str[json_str.find('{'):json_str.rfind('}')+1]

            reflection_data = json.loads(json_str)

            # POST-PROCESS: Calculate objective scores
            print("  Calculating alignment score...")
            alignment_status, alignment_score = calculate_alignment_score(
                tech_recommendation=tech_recommendation,
                tech_confidence=tech_confidence,
                sentiment_signal=sentiment_signal,
                sentiment_confidence=sentiment_confidence
            )

            print("  Assessing risk level...")
            risk_level, secondary_risks = assess_risk_level(
                volume_ratio=volume_ratio,
                alignment_score=alignment_score,
                tech_analysis=tech,
                sentiment_data=sentiment,
                btc_correlation=btc_correlation,
                btc_trend=btc_trend,
                price_position_14d=price_position_14d,
                rsi_divergence_type=rsi_divergence_type,
                rsi_divergence_strength=rsi_divergence_strength
            )

            print("  Calculating Bayesian confidence (reference metric)...")
            bayesian_confidence = calculate_bayesian_confidence(
                tech_confidence=tech_confidence,
                sentiment_confidence=sentiment_confidence,
                alignment_score=alignment_score,
                risk_level=risk_level,
                volume_ratio=volume_ratio,
                btc_correlation=btc_correlation,
                btc_trend=btc_trend,
                cfgi_score=cfgi_score_value,
                price_position_14d=price_position_14d
            )

            # Inject calculated metrics (trust LLM for recommendation and confidence)
            if 'agent_alignment' not in reflection_data:
                reflection_data['agent_alignment'] = {}

            reflection_data['agent_alignment']['alignment_score'] = alignment_score
            reflection_data['agent_alignment']['technical_says'] = f"{tech_recommendation} ({tech_confidence:.0%})"
            reflection_data['agent_alignment']['sentiment_says'] = f"{sentiment_signal} ({sentiment_confidence:.0%})"

            # Store Bayesian confidence as reference (for validation and fallback)
            reflection_data['calculated_metrics'] = {
                'bayesian_confidence': bayesian_confidence['final_confidence'],
                'risk_level': risk_level,
                'confidence_deviation': abs(reflection_data.get('confidence', {}).get('score', 0.5) - bayesian_confidence['final_confidence'])
            }

            # Log if LLM and Bayesian confidence differ significantly
            llm_conf = reflection_data.get('confidence', {}).get('score', 0.5)
            if abs(llm_conf - bayesian_confidence['final_confidence']) > 0.15:
                print(f"  ⚠️  Confidence deviation: LLM={llm_conf:.0%} vs Bayesian={bayesian_confidence['final_confidence']:.0%}")

            # Add thinking and timestamp
            if thinking_text:
                reflection_data['thinking'] = thinking_text
            reflection_data['timestamp'] = timestamp

            # Save to state and database
            state['reflection'] = reflection_data

            with DataManager() as dm:
                dm.save_reflection_analysis(data=reflection_data)

            print("✅ Reflection agent completed successfully")

        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            print(f"⚠️  Reflection agent parsing error: {e}")
            print(f"Response preview: {response[:500]}")

            # Calculate metrics for fallback
            alignment_status, alignment_score = calculate_alignment_score(
                tech_recommendation, tech_confidence,
                sentiment_signal, sentiment_confidence
            )

            risk_level, secondary_risks = assess_risk_level(
                volume_ratio=volume_ratio,
                alignment_score=alignment_score,
                tech_analysis=tech,
                sentiment_data=sentiment,
                btc_correlation=btc_correlation,
                btc_trend=btc_trend,
                price_position_14d=price_position_14d,
                rsi_divergence_type=rsi_divergence_type,
                rsi_divergence_strength=rsi_divergence_strength
            )

            bayesian_conf = calculate_bayesian_confidence(
                tech_confidence=tech_confidence,
                sentiment_confidence=sentiment_confidence,
                alignment_score=alignment_score,
                risk_level=risk_level,
                volume_ratio=volume_ratio,
                btc_correlation=btc_correlation,
                btc_trend=btc_trend,
                cfgi_score=cfgi_score_value,
                price_position_14d=price_position_14d
            )

            # Derive market condition
            market_condition = 'ALIGNED' if alignment_score >= 0.80 else 'CONFLICTED' if alignment_score < 0.60 else 'MIXED'

            # Use Bayesian confidence in fallback
            state['reflection'] = {
                'recommendation_signal': tech_recommendation,
                'market_condition': market_condition,
                'confidence': {
                    'score': bayesian_conf['final_confidence'],
                    'reasoning': f'Reflection synthesis failed: {str(e)[:100]}. Using Technical ({tech_recommendation}, {tech_confidence:.0%}) with Bayesian confidence.'
                },
                'timestamp': timestamp,
                'agent_alignment': {
                    'alignment_score': alignment_score,
                    'technical_says': f"{tech_recommendation} ({tech_confidence:.0%})",
                    'sentiment_says': f"{sentiment_signal} ({sentiment_confidence:.0%})",
                    'synthesis': f'Error prevented synthesis. Alignment {alignment_score:.0%}.'
                },
                'blind_spots': {
                    'technical_missed': 'Unable to analyze due to error',
                    'sentiment_missed': 'Unable to analyze due to error',
                    'critical_insight': 'Re-run reflection analysis'
                },
                'primary_risk': f'Volume: {volume_ratio:.2f}x, Risk level: {risk_level}',
                'calculated_metrics': {
                    'bayesian_confidence': bayesian_conf['final_confidence'],
                    'risk_level': risk_level
                },
                'thinking': f'Error: {str(e)}'
            }

            with DataManager() as dm:
                dm.save_reflection_analysis(data=state['reflection'])

        return state


if __name__ == "__main__":
    test_state = AgentState()

    test_state['technical'] = {
        'timestamp': '2026-01-02T13:58:04.992663Z',
        'recommendation_signal': 'WAIT',
        'confidence': {
            'analysis_confidence': 0.85,
            'setup_quality': 0.25,
            'interpretation': 'High confidence in WAIT - dead volume makes setup poor'
        },
        'market_condition': 'QUIET',
        'summary': 'SOL is building a potential base around $126-128 with bullish momentum signals emerging, but critically low volume (0.65x average) makes any move unreliable. Combined with bearish BTC correlation, this is a clear WAIT situation until volume returns to confirm direction.',
        'thinking': ["Market story: SOL in consolidation/base-building phase, grinding higher from $122 lows but still below key EMA50 resistance", "Volume assessment: DEAD volume at 0.65x average invalidates all other signals - no conviction behind recent gains", "Momentum read: MACD showing bullish divergence and Bollinger Squeeze active, but compromised by lack of volume", "BTC context: Strong 0.91 correlation with bearish BTC (-4.3% 30d) creates significant headwind for any rally", "Setup evaluation: No valid trade setup due to dead volume and narrow range - risk/reward unfavorable", "Key conclusion: Wait for volume confirmation before taking any directional position"],

        'analysis': {
            "trend": 
            {
                "direction": "NEUTRAL", 
                "strength": "WEAK", 
                "detail": "Consolidating above recent lows but below key resistance, lacking conviction to establish clear direction."
            }, 
            "momentum": 
            {
                "direction": "BULLISH", 
                "strength": "WEAK", 
                "detail": "MACD histogram positive and Bollinger Squeeze building, but dead volume undermines reliability."
            }, 
            "volume": 
            {
                "quality": "DEAD", 
                "ratio": 0.65, 
                "detail": "Volume 35% below average with 41 days since last spike - no market participation or conviction."
            }
        },

        'trade_setup': {
            "viability": "INVALID",
            "entry": 0, 
            "stop_loss": 0, 
            "take_profit": 0, 
            "risk_reward": 0, 
            "support": 126.53, 
            "resistance": 130.61, 
            "current_price": 128.4, 
            "timeframe": 0
        },

        'action_plan': {
            "primary": "Wait on sidelines until volume returns above 1.0x average to confirm any directional move", 
            "alternative": "If already holding, consider reducing position size given lack of conviction", 
            "if_in_position": "Set tight stops near $126.50 support and avoid adding until volume confirms", 
            "avoid": "Do not chase any breakout above $130 without volume confirmation - likely false breakout"
        },

        'watch_list': {
            "next_24h": ["Volume spike above 1.0x average", "Break below $126.53 support", "BTC direction and correlation strength"], 
            "next_48h": ["Bollinger Squeeze resolution direction", "EMA20 hold or break", "Weekend volume patterns"]
        },

        'invalidation': ["Volume drops further below 0.6x average - indicates complete market disinterest", "Break below $126.53 on any volume - invalidates base-building thesis"],

        'confidence_reasoning': {
            "supporting": ["MACD bullish divergence", "Bollinger Squeeze building energy", "Holding above recent $122 lows"], 
            "concerns": ["Dead volume invalidates signals", "Strong BTC correlation with bearish BTC", "Narrow range limits profit potential"], 
            "assessment": "Dead volume is the overriding factor that makes any directional call unreliable regardless of other technical signals."
        }
    }

    # SENTIMENT ANALYSIS STATE
    test_state['sentiment'] = {
        'timestamp': '2026-01-02 13:58:23.692 +0000',
        'signal': 'SLIGHTLY_BULLISH',
        'confidence': {
            'analysis_confidence': 0.85,
            'signal_strength': 0.65,
            'interpretation': 'High confidence in bullish sentiment analysis'
        },     

        'market_fear_greed': {
            'score': 55, 
            'classification': 'Neutral',  
            'social': 98.5,  
            'whales': 26.5,  
            'trends': 88.5, 
            'interpretation': 'Retail excitement without strong institutional confirmation'
        },

        'news_sentiment': {
            'score': 0.68, 
            'label': 'CAUTIOUSLY_BULLISH', 
            'catalysts_count': 3, 
            'risks_count': 1 
        },

        'key_events': [
            {
                "title": "Solana RWA Momentum Entering 2026", 
                "type": "ECOSYSTEM", 
                "impact": "BULLISH", 
                "source": "CoinTelegraph", 
                "url": "https://cointelegraph.com/news/solana-institutional-momentum-heading-2026", 
                "published_at": "2026-01-02"
            }, 
            {
                "title": "SOL Whale Accumulation on New Year's Day", 
                "type": "MARKET_TREND", 
                "impact": "BULLISH", 
                "source": "Santiment", 
                "url": "https://cointelegraph.com/news/solana-whale-accumulation-santiment-crypto-trends-2026", 
                "published_at": "2026-01-01"
            }, 
            {
                "title": "Ondo Finance Tokenized US Stocks on Solana", 
                "type": "PARTNERSHIP", 
                "impact": "BULLISH", 
                "source": "CoinTelegraph", 
                "url": "https://cointelegraph.com/news/how-ondo-finance-plans-to-bring-tokenized-us-stocks-to-solana", 
                "published_at": "2025-12-24"
            }
        ],

        'risk_flags': ["Potential memecoin perception challenge", "Brief stablecoin depeg on DEXs"],

        'summary': 'Solana shows promising institutional momentum with Real World Asset expansion and whale accumulation. Retail excitement is high, but institutional backing remains measured. Potential for moderate upside with careful entry strategy.', 

        'what_to_watch': ["RWA momentum development", "Institutional capital inflows", "Ecosystem partnership announcements"],

        'invalidation': 'Significant regulatory action or prolonged network instability',  
        'suggested_timeframe': '3-5 days',  
        'thinking': 'Your sentiment thinking process here'  
    }

    print("=" * 80)
    print("TESTING REFLECTION AGENT")
    print("=" * 80)
    print("\n📋 Input State:")
    tech_conf = test_state['technical']['confidence']
    sent_conf = test_state['sentiment']['confidence']
    print(f"  Technical: {test_state['technical']['recommendation_signal']} @ {tech_conf['setup_quality']:.0%} setup quality")
    print(f"  Sentiment: {test_state['sentiment']['signal']} @ {sent_conf['signal_strength']:.0%} signal strength")
    print(f"  Volume Ratio: {test_state['technical']['analysis']['volume']['ratio']:.2f}x")
    print(f"  CFGI Score: {test_state['sentiment']['market_fear_greed']['score']}/100")

    print("\n🔄 Running Reflection Agent...")
    print("-" * 80)

    agent = ReflectionAgent()
    result_state = agent.execute(test_state)

  

    print("\n✅ Test complete!")
