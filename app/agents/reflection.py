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


SYSTEM_PROMPT = """You are a SENIOR TRADING STRATEGIST with 20 years experience in crypto markets, specializing in synthesizing multi-agent analysis for Solana (SOL) swing trading.

YOUR ROLE:
- Review Technical and Sentiment agent analyses
- Identify blind spots (what each agent missed)
- Assess agreement/conflict between agents
- Calculate risk-adjusted confidence
- Provide unified actionable recommendation

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

Analyze the above data using **FOCUSED 4-PHASE FRAMEWORK**.

Your job is QUALITATIVE ANALYSIS ONLY. The code will handle all calculations (alignment scores, risk levels, confidence scores).

### CONFIDENCE GUIDELINES

<confidence_guidelines>
## Analysis Confidence (0.75-0.95)
How confident are you in this SYNTHESIS of Technical + Sentiment?

- 0.90-0.95: Both agents strongly aligned, clear picture
- 0.80-0.89: Good alignment, minor conflicts resolved
- 0.75-0.79: Reasonable synthesis despite some conflicts

## Final Confidence (0.15-1.0)
What is the OVERALL trade confidence after synthesis?

Start with the AVERAGE of technical and sentiment confidences:
- If they have setup_quality 0.25 and signal_strength 0.65 → base = (0.25 + 0.65) / 2 = 0.45

Then adjust based on:
- Alignment: +0.05 if strong agreement, -0.10 if conflict
- Risk: -0.05 for MEDIUM, -0.10 for HIGH risk
- Volume: -0.12 if < 0.7x (DEAD), -0.05 if < 1.0x
- BTC: -0.08 if bearish BTC + high correlation

CRITICAL RULES:
- Never go below 0.15 (even worst case has some edge)
- If recommendation is WAIT → final_confidence should be ≤ 0.35
- If recommendation is BUY/SELL → final_confidence should be ≥ 0.55
- Adjustments should be modest (±0.05 to ±0.12 per factor)

## Interpretation
Combine both into a clear sentence:
- "High confidence in synthesis, moderate trade opportunity"
- "Very confident both agree on WAIT, poor setup quality"
- "Good synthesis despite conflicts, acceptable trade setup"
</confidence_guidelines>

### OUTPUT FORMAT

<thinking>

**PHASE 1: AGREEMENT SYNTHESIS**
Compare Technical vs Sentiment direction:
- Does Technical ({tech_recommendation}) align with Sentiment ({sentiment_signal})?
- Write 2-3 sentence synthesis explaining how they fit together
- Don't calculate alignment_score - just describe agreement/disagreement

**PHASE 2: TECHNICAL BLIND SPOTS**
What did Technical analysis miss that Sentiment revealed?
- Look at: risk_flags, key_events, CFGI extremes, news catalysts
- List 2-3 SPECIFIC items Technical couldn't see
- How does this impact the technical thesis?

**PHASE 3: SENTIMENT BLIND SPOTS**
What did Sentiment analysis miss that Technical revealed?
- Look at: volume ratio, price action, support/resistance, chart patterns
- List 2-3 SPECIFIC items Sentiment couldn't see
- How does this impact the sentiment thesis?

**PHASE 4: RISK & MONITORING**
Describe the BIGGEST THREAT (narrative, not level):
- What's the primary risk combining both analyses?
- What should traders watch in next 24 hours?
- What conditions would invalidate this thesis?
- What's the critical insight that ties everything together?

</thinking>

<answer>
{{
  "recommendation": "BUY|SELL|HOLD|WAIT",

  "confidence": {{
    "analysis_confidence": 0.85,
    "final_confidence": 0.45,
    "interpretation": "High confidence in synthesis, moderate trade opportunity"
  }},

  "agreement_analysis": {{
    "synthesis": "Write your 2-3 sentence synthesis explaining how technical and sentiment fit together"
  }},

  "blind_spots": {{
    "technical_missed": [
      "Specific item 1 that technical couldn't see",
      "Specific item 2 that technical couldn't see"
    ],
    "sentiment_missed": [
      "Specific item 1 that sentiment couldn't see",
      "Specific item 2 that sentiment couldn't see"
    ],
    "critical_insight": "The ONE key takeaway that combines both perspectives"
  }},

  "risk_assessment": {{
    "primary_risk": "Narrative description of the biggest threat"
  }},

  "monitoring": {{
    "watch_next_24h": [
      "Specific metric 1 to monitor",
      "Specific metric 2 to monitor",
      "Specific metric 3 to monitor"
    ],
    "invalidation_triggers": [
      "Condition 1 that kills the thesis",
      "Condition 2 that kills the thesis"
    ]
  }},

  "reasoning": "Write 2-3 sentence final synthesis combining everything"
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
        tech = state.get('technical', {})
        tech_recommendation = tech.get('recommendation', 'HOLD')

        # Handle nested confidence object from Technical agent
        tech_confidence_obj = tech.get('confidence', {})
        if isinstance(tech_confidence_obj, dict):
            tech_confidence = tech_confidence_obj.get('setup_quality', 0.5)
        else:
            tech_confidence = float(tech_confidence_obj) if tech_confidence_obj else 0.5

        tech_market_condition = tech.get('market_condition', 'QUIET')
        tech_summary = tech.get('summary', 'No summary')

        tech_entry = get_nested(tech, 'trade_setup.entry', 0.0)
        tech_stop = get_nested(tech, 'trade_setup.stop_loss', 0.0)
        tech_target = get_nested(tech, 'trade_setup.take_profit', 0.0)
        tech_risk_reward = get_nested(tech, 'trade_setup.risk_reward', 0.0)
        tech_timeframe = get_nested(tech, 'trade_setup.timeframe', 'N/A')

        tech_analysis = tech.get('analysis', {})
        tech_watch_list = tech.get('watch_list', {})
        tech_invalidation = tech.get('invalidation', [])
        tech_confidence_reasoning = tech.get('confidence_reasoning', {})

        volume_ratio = get_nested(tech, 'analysis.volume.ratio', 1.0)
        volume_quality = get_nested(tech, 'analysis.volume.quality', 'UNKNOWN')

        from app.agents.db_fetcher import DataQuery
        with DataQuery() as dq:
            indicators_data = dq.get_indicators_data()

        btc_correlation = float(indicators_data.get('sol_btc_correlation', 0.0))
        btc_trend = indicators_data.get('btc_trend', 'NEUTRAL')
        btc_price_change_30d = float(indicators_data.get('btc_price_change_30d', 0.0))

        # Extract price position data (for risk assessment)
        high_14d = float(indicators_data.get('high_14d', 0.0))
        low_14d = float(indicators_data.get('low_14d', 0.0))
        current_price = get_nested(tech, 'trade_setup.current_price', 0.0)

        # Calculate price position in 14d range (0 = at low, 1 = at high)
        if high_14d > 0 and low_14d > 0 and high_14d != low_14d:
            price_position_14d = (current_price - low_14d) / (high_14d - low_14d)
        else:
            price_position_14d = 0.5  # Default to middle if can't calculate

        # Extract RSI divergence (risk factor)
        rsi_divergence_type = indicators_data.get('rsi_divergence_type', 'NONE')
        rsi_divergence_strength = float(indicators_data.get('rsi_divergence_strength', 0.0))

        # Extract sentiment analysis
        sentiment = state.get('sentiment', {})
        sentiment_signal = sentiment.get('signal', 'NEUTRAL')

        # Handle nested confidence object from Sentiment agent
        sentiment_confidence_obj = sentiment.get('confidence', {})
        if isinstance(sentiment_confidence_obj, dict):
            sentiment_confidence = sentiment_confidence_obj.get('signal_strength', 0.5)
        else:
            sentiment_confidence = float(sentiment_confidence_obj) if sentiment_confidence_obj else 0.5

        # Extract CFGI data using helper
        cfgi_score = get_nested(sentiment, 'market_fear_greed.score', 50)

        # Extract CFGI extreme signals (AFTER cfgi_score is defined)
        cfgi_score_value = float(cfgi_score) if cfgi_score else 50.0
        is_extreme_fear = cfgi_score_value < 20  # Contrarian buy signal
        is_extreme_greed = cfgi_score_value > 80  # Contrarian sell signal
        cfgi_classification = get_nested(sentiment, 'market_fear_greed.classification', 'Neutral')
        cfgi_interpretation = get_nested(sentiment, 'market_fear_greed.interpretation', 'No interpretation')

        # Extract news sentiment data using helper
        news_sentiment_score = get_nested(sentiment, 'news_sentiment.score', 0.5)
        news_sentiment_label = get_nested(sentiment, 'news_sentiment.label', 'NEUTRAL')

        # Extract other sentiment fields
        key_events = sentiment.get('key_events', [])
        risk_flags = sentiment.get('risk_flags', [])
        sentiment_summary = sentiment.get('summary', 'No summary')
        what_to_watch = sentiment.get('what_to_watch', [])
        sentiment_invalidation = sentiment.get('invalidation', 'Not specified')

        # Format technical analysis for prompt
        tech_analysis_formatted = json.dumps(tech_analysis, indent=2) if tech_analysis else "No analysis data"
        tech_watch_list_formatted = json.dumps(tech_watch_list, indent=2) if tech_watch_list else "No watch list"
        tech_invalidation_formatted = '\n'.join([f"  - {item}" for item in tech_invalidation]) if tech_invalidation else "No invalidation conditions"
        tech_confidence_reasoning_formatted = json.dumps(tech_confidence_reasoning, indent=2) if tech_confidence_reasoning else "No reasoning"

        # Format sentiment data for prompt
        sentiment_key_events_formatted = '\n'.join([
            f"  - {event.get('title', 'Unknown')} ({event.get('type', 'Unknown')}) - {event.get('impact', 'Unknown')}"
            for event in key_events[:5]
        ]) if key_events else "No key events"

        sentiment_risk_flags_formatted = '\n'.join([f"  - {flag}" for flag in risk_flags]) if risk_flags else "No risk flags"
        sentiment_what_to_watch_formatted = '\n'.join([f"  - {item}" for item in what_to_watch]) if what_to_watch else "Nothing specified"

        # Current timestamp
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Build full prompt
        full_prompt = SYSTEM_PROMPT + "\n\n" + REFLECTION_PROMPT.format(
            # Technical fields
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

            # Sentiment fields
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

            # Timestamp
            timestamp=timestamp
        )

        # Call LLM
        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=3000
        )

        # Parse response
        try:
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            thinking_text = thinking_match.group(1).strip() if thinking_match else ""

            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            if answer_match:
                json_str = answer_match.group(1).strip()
            else:
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")

            # Clean JSON string
            json_str = json_str.replace('\u201c', '"').replace('\u201d', '"')
            json_str = json_str.replace('\u2018', "'").replace('\u2019', "'")
            json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)

            first_brace = json_str.find('{')
            last_brace = json_str.rfind('}')
            if first_brace != -1 and last_brace != -1:
                json_str = json_str[first_brace:last_brace+1]

            reflection_data = json.loads(json_str)

            # POST-PROCESS: Calculate scores
            print(" Calculating alignment score...")
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

            print(" Calculating Bayesian confidence...")
            confidence_calc = calculate_bayesian_confidence(
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

            # ONLY override alignment and risk (objective), NOT confidence (qualitative)
            reflection_data['agreement_analysis']['alignment_status'] = alignment_status
            reflection_data['agreement_analysis']['alignment_score'] = alignment_score

            reflection_data['risk_assessment']['risk_level'] = risk_level
            reflection_data['risk_assessment']['secondary_risks'] = secondary_risks

            # Keep LLM's confidence calculation, just validate it
            llm_confidence = reflection_data.get('confidence', {})
            if not isinstance(llm_confidence, dict):
                # Fallback if LLM output is wrong format
                reflection_data['confidence'] = {
                    'analysis_confidence': 0.75,
                    'final_confidence': max(0.15, confidence_calc['final_confidence']),
                    'interpretation': 'Fallback confidence due to parsing error'
                }
            else:
                # Ensure confidence has a floor of 0.15
                if llm_confidence.get('final_confidence', 0) < 0.15:
                    llm_confidence['final_confidence'] = 0.15
                    llm_confidence['interpretation'] += " [Floor applied: min 0.15]"

            print(f"✅ Final confidence: {reflection_data['confidence']['final_confidence']:.2%} ({reflection_data['confidence'].get('interpretation', 'N/A')})")

            # VALIDATE AND OVERRIDE RECOMMENDATION IF NECESSARY
            llm_recommendation = reflection_data.get('recommendation', 'HOLD')
            final_recommendation = llm_recommendation

            # Critical validation rules (in order of priority)
            validation_overrides = []

            # Get final confidence for validation
            final_conf = reflection_data['confidence'].get('final_confidence', 0.5)

            # Rule 1: DEAD volume = WAIT (absolute rule)
            if volume_ratio < 0.7:
                final_recommendation = 'WAIT'
                # Update confidence object
                reflection_data['confidence']['final_confidence'] = max(0.20, final_conf)
                reflection_data['confidence']['interpretation'] += " [Override: DEAD volume]"
                validation_overrides.append(f"DEAD volume ({volume_ratio:.2f}x) - forced WAIT")

            # Rule 2: Very low confidence = WAIT
            elif final_conf < 0.35:
                final_recommendation = 'WAIT'
                validation_overrides.append(f"Low confidence ({final_conf:.0%}) - forced WAIT")

            # Rule 3: High risk + directional bet = HOLD
            elif risk_level == 'HIGH' and llm_recommendation in ['BUY', 'SELL']:
                final_recommendation = 'HOLD'
                validation_overrides.append(f"HIGH risk with {llm_recommendation} - changed to HOLD")

            # Rule 4: BUY near 14d high = questionable
            elif llm_recommendation == 'BUY' and price_position_14d > 0.90:
                final_recommendation = 'HOLD'
                validation_overrides.append(f"BUY near 14d high ({price_position_14d:.0%}) - changed to HOLD")

            # Rule 5: SELL near 14d low = questionable
            elif llm_recommendation == 'SELL' and price_position_14d < 0.10:
                final_recommendation = 'HOLD'
                validation_overrides.append(f"SELL near 14d low ({price_position_14d:.0%}) - changed to HOLD")

            # Rule 6: BUY when BTC bearish + high correlation
            elif llm_recommendation == 'BUY' and btc_correlation > 0.85 and btc_trend == 'BEARISH':
                final_recommendation = 'WAIT'
                validation_overrides.append(f"BUY with bearish BTC (corr={btc_correlation:.2f}) - forced WAIT")

            # Apply override if any rule triggered
            if validation_overrides:
                print(f"⚠️  Recommendation override: {llm_recommendation} → {final_recommendation}")
                for override in validation_overrides:
                    print(f"    - {override}")
                reflection_data['recommendation'] = final_recommendation

                # Add override explanation to reasoning
                override_text = " | ".join(validation_overrides)
                original_reasoning = reflection_data.get('reasoning', '')
                reflection_data['reasoning'] = f"{original_reasoning} [AUTO-OVERRIDE: {override_text}]"

            # Auto-generate view fields (after removing from LLM prompt)
            reflection_data['agreement_analysis']['technical_view'] = f"{tech_recommendation} ({tech_confidence:.0%})"
            reflection_data['agreement_analysis']['sentiment_view'] = f"{sentiment_signal} ({sentiment_confidence:.0%})"

            # Reconcile timeframes
            tech_timeframe_str = tech_timeframe
            sentiment_timeframe_str = sentiment.get('suggested_timeframe', 'N/A')

            # Parse timeframes (extract max days)
            def extract_max_days(timeframe_str: str) -> int:
                """Extract maximum days from timeframe string like '3-5 days' or '5-7 days'"""
                if not timeframe_str or timeframe_str == 'N/A':
                    return 5  # Default
                # Look for pattern like "X-Y days" or "X days"
                import re
                match = re.search(r'(\d+)-(\d+)\s*days?', timeframe_str)
                if match:
                    return int(match.group(2))  # Return max
                match = re.search(r'(\d+)\s*days?', timeframe_str)
                if match:
                    return int(match.group(1))
                return 5  # Default

            tech_days = extract_max_days(tech_timeframe_str)
            sentiment_days = extract_max_days(sentiment_timeframe_str)

            # Use the longer timeframe (more conservative)
            reconciled_days = max(tech_days, sentiment_days)
            reconciled_timeframe = f"{reconciled_days-2}-{reconciled_days} days"

            # Add to reflection data
            reflection_data['timeframe_reconciliation'] = {
                'technical_timeframe': tech_timeframe_str,
                'sentiment_timeframe': sentiment_timeframe_str,
                'reconciled_timeframe': reconciled_timeframe,
                'reasoning': f"Using longer timeframe ({reconciled_timeframe}) to accommodate both analyses"
            }

            print(f"📅 Timeframe: Technical={tech_timeframe_str}, Sentiment={sentiment_timeframe_str} → Reconciled={reconciled_timeframe}")

            # Override thinking field with concatenated phases
            if thinking_text:
                reflection_data['thinking'] = thinking_text

            # Ensure timestamp is set
            if 'timestamp' not in reflection_data:
                reflection_data['timestamp'] = timestamp

            state['reflection'] = reflection_data

            with DataManager() as dm:
                dm.save_reflection_analysis(data=reflection_data)

            print("✅ Reflection agent completed successfully")

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Reflection agent parsing error: {e}")
            print(f"Response preview: {response[:500]}")

            # Calculate using helpers even in fallback
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

            confidence_calc = calculate_bayesian_confidence(
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

            # Fallback with calculated values
            state['reflection'] = {
                'recommendation': tech_recommendation,
                'confidence': {
                    'analysis_confidence': 0.5,
                    'final_confidence': max(0.20, confidence_calc['final_confidence']),
                    'interpretation': f'Fallback due to error: {str(e)[:50]}'
                },
                'timestamp': timestamp,
                'agreement_analysis': {
                    'alignment_status': alignment_status,
                    'alignment_score': alignment_score,
                    'technical_view': f"{tech_recommendation} ({tech_confidence:.2f})",
                    'sentiment_view': f"{sentiment_signal} ({sentiment_confidence:.2f})",
                    'synthesis': 'Parsing error - using fallback analysis with calculated scores'
                },
                'blind_spots': {
                    'technical_missed': ['Unable to analyze due to parsing error'],
                    'sentiment_missed': ['Unable to analyze due to parsing error'],
                    'critical_insight': f'Analysis error: {str(e)[:100]}'
                },
                'risk_assessment': {
                    'primary_risk': f'Reflection analysis failed: {str(e)[:100]}',
                    'risk_level': risk_level,
                    'secondary_risks': secondary_risks
                },
                'monitoring': {
                    'watch_next_24h': ['Re-run reflection analysis'],
                    'invalidation_triggers': ['N/A']
                },
                'reasoning': f'Reflection analysis failed. Using fallback confidence. Error: {str(e)[:100]}',
                'thinking': f'Parsing error occurred: {str(e)}'
            }

            # Still try to save fallback to DB
            try:
                with DataManager() as dm:
                    dm.save_reflection_analysis(data=state['reflection'])
            except Exception as save_err:
                print(f"⚠️  Failed to save fallback: {save_err}")

        return state


if __name__ == "__main__":
    test_state = AgentState()

    test_state['technical'] = {
        'timestamp': '2026-01-02T13:58:04.992663Z',
        'recommendation': 'WAIT',
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
    print(f"  Technical: {test_state['technical']['recommendation']} @ {tech_conf['setup_quality']:.0%} setup quality")
    print(f"  Sentiment: {test_state['sentiment']['signal']} @ {sent_conf['signal_strength']:.0%} signal strength")
    print(f"  Volume Ratio: {test_state['technical']['analysis']['volume']['ratio']:.2f}x")
    print(f"  CFGI Score: {test_state['sentiment']['market_fear_greed']['score']}/100")

    # Run the reflection agent
    print("\n🔄 Running Reflection Agent...")
    print("-" * 80)

    agent = ReflectionAgent()
    result_state = agent.execute(test_state)

    print("\n" + "=" * 80)
    print("REFLECTION AGENT OUTPUT")
    print("=" * 80)

    if 'reflection' in result_state:
        reflection = result_state['reflection']
        
        print(json.dumps(reflection, indent=2, ensure_ascii=False))
    else:
        print("❌ No reflection output generated!")
        print(json.dumps(result_state, indent=2, ensure_ascii=False))

    print("\n✅ Test complete!")
