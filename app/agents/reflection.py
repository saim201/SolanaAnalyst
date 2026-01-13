# reflection.py

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from typing import Dict

from anthropic import Anthropic

from app.agents.base import BaseAgent, AgentState
from app.database.data_manager import DataManager
from app.agents.reflection_helpers import (
    get_nested,
    calculate_alignment_score,
    assess_risk_level
    )


REFLECTION_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation_signal": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD", "WAIT"],
            "description": "Final unified recommendation"
        },
        "market_condition": {
            "type": "string",
            "enum": ["ALIGNED", "CONFLICTED", "MIXED"],
            "description": "Agent alignment status"
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
                    "description": "2-3 sentences: both agents' scores, agreement/conflict, key factor, why this leads to recommendation"
                }
            },
            "required": ["score", "reasoning"],
            "additionalProperties": False
        },
        "thinking": {
            "type": "string",
            "description": "Full chain-of-thought reasoning process"
        },
        "agent_alignment": {
            "type": "object",
            "properties": {
                "technical_says": {
                    "type": "string",
                    "description": "Technical recommendation with confidence"
                },
                "sentiment_says": {
                    "type": "string",
                    "description": "Sentiment recommendation with confidence"
                },
                "alignment_score": {
                    "type": "number",
                    "description": "Calculated alignment score 0.0-1.0"
                },
                "synthesis": {
                    "type": "string",
                    "description": "How Technical + Sentiment combine with specifics"
                }
            },
            "required": ["technical_says", "sentiment_says", "alignment_score", "synthesis"],
            "additionalProperties": False
        },
        "blind_spots": {
            "type": "object",
            "properties": {
                "technical_missed": {
                    "type": "string",
                    "description": "What Technical missed that Sentiment revealed"
                },
                "sentiment_missed": {
                    "type": "string",
                    "description": "What Sentiment missed that Technical revealed"
                },
                "critical_insight": {
                    "type": "string",
                    "description": "The key insight from combining both analyses"
                }
            },
            "required": ["technical_missed", "sentiment_missed", "critical_insight"],
            "additionalProperties": False
        },
        "primary_risk": {
            "type": "string",
            "description": "The main risk that could derail this trade"
        },
        "monitoring": {
            "type": "object",
            "properties": {
                "watch_next_24h": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Critical factors to monitor in next 24 hours"
                },
                "invalidation_triggers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific conditions that would invalidate the thesis"
                }
            },
            "required": ["watch_next_24h", "invalidation_triggers"],
            "additionalProperties": False
        },
        "final_reasoning": {
            "type": "string",
            "description": "3-4 sentences: overall picture, why this recommendation, what would change your mind"
        }
    },
    "required": [
        "recommendation_signal",
        "market_condition",
        "confidence",
        "thinking",
        "agent_alignment",
        "blind_spots",
        "primary_risk",
        "monitoring",
        "final_reasoning"
    ],
    "additionalProperties": False
}




SYSTEM_PROMPT = """You are a SENIOR TRADING STRATEGIST with 20 years experience in crypto markets, specialising in synthesising multi-agent analysis for Solana (SOL) swing trading.

YOUR ROLE:
- Review Technical and Sentiment analyses
- Identify blind spots (what each analyst missed)
- Assess agreement/conflict between analysts
- Calculate risk-adjusted confidence
- Provide unified actionable recommendation

YOUR EXPERTISE:
- Blind spot detection (finding what analysts overlook)
- Confidence fusion (combining probabilistic signals)
- Risk assessment (identifying primary threats)
- Synthesis (turning conflicting signals into clear decisions)

YOUR STYLE:
- Honest: If confidence is low, say so
- Risk-focused: Always identify the primary risk
- Decisive: Provide clear recommendations
- Transparent: Show your reasoning

CRITICAL: Your confidence.reasoning must tell the story of how Technical + Sentiment combine. Cite specific scores, disagreements, and key data points. Paint a clear picture.
"""



REFLECTION_PROMPT = """
<technical_analysis>
**Recommendation:** {tech_recommendation}
**Confidence:** {tech_confidence:.0%}
**Market Condition:** {tech_market_condition}

**Confidence Reasoning:** {tech_confidence_reasoning}

**Trade Setup:**
- Entry: ${tech_entry:.2f}
- Stop Loss: ${tech_stop:.2f}
- Take Profit: ${tech_target:.2f}
- Risk/Reward: {tech_risk_reward:.2f}
- Timeframe: {tech_timeframe}

**Volume Analysis:**
- Ratio: {volume_ratio:.2f}x average
- Quality: {volume_quality}

**Trend:** {tech_trend_direction} ({tech_trend_strength})
{tech_trend_detail}

**Momentum:** {tech_momentum_direction} ({tech_momentum_strength})
{tech_momentum_detail}

**Volume Detail:**
{tech_volume_detail}

**Watch List:**
Bullish Signals: {tech_bullish_signals}
Bearish Signals: {tech_bearish_signals}

**Invalidation:** {tech_invalidation}

</technical_analysis>

<sentiment_analysis>
**Signal:** {sentiment_signal}
**Confidence:** {sentiment_confidence:.0%}

**Confidence Reasoning:** {sentiment_confidence_reasoning}

**CFGI Fear & Greed:**
- Score: {cfgi_score}/100 ({cfgi_classification})
- Social: {cfgi_social} | Whales: {cfgi_whales} | Trends: {cfgi_trends}
- Interpretation: {cfgi_interpretation}

**News Sentiment:** {news_sentiment_label} ({news_sentiment_score:.0%})

**Key Events:**
{sentiment_key_events}

**Risk Flags:** {sentiment_risk_flags}

**What to Watch:** {sentiment_what_to_watch}

**Invalidation:** {sentiment_invalidation}

</sentiment_analysis>

---

<instructions>
Analyse using **FOCUSED 4-PHASE FRAMEWORK**.

Write your reasoning inside <thinking> tags, then output JSON inside <answer> tags.

## PHASE 1: AGENT ALIGNMENT ANALYSIS
Compare Technical ({tech_recommendation}, {tech_confidence:.0%}) vs Sentiment ({sentiment_signal}, {sentiment_confidence:.0%}):

Write 3-4 sentences:
- Do they AGREE on direction?
- What SPECIFIC factors drive each? (cite prices, volume, news, dates)
- Where's the KEY DISAGREEMENT?
- What's the alignment telling us?

## PHASE 2: TECHNICAL BLIND SPOTS
What did Technical MISS that Sentiment revealed?

For EACH blind spot (2-3 sentences):
- WHAT was missed? (specific event, risk, context)
- WHY does it matter?
- HOW should this affect the trade?

## PHASE 3: SENTIMENT BLIND SPOTS
What did Sentiment MISS that Technical revealed?

For EACH blind spot (2-3 sentences):
- WHAT was missed? (volume, chart structure, momentum)
- WHY does it matter?
- HOW should this affect the trade?

## PHASE 4: SYNTHESIS & DECISION
Combine everything:

Write 3-4 sentences:
- What's the OVERALL PICTURE?
- What's the PRIMARY RISK?
- Given alignment + blind spots + risks, what's the RIGHT MOVE?
- What SPECIFIC CONDITIONS would change your mind?

## CONFIDENCE SCALE
- 0.80-1.00: Very high - both agents strongly aligned, clear edge
- 0.65-0.79: High - good alignment, manageable risks
- 0.50-0.64: Moderate - some conflicts but edge exists
- 0.35-0.49: Low - significant conflicts or unclear edge
- 0.15-0.34: Very low - major conflicts, wait for clarity

## CONFIDENCE REASONING (CRITICAL)
Must include:
- Both agents' recommendations + scores
- Specific point of agreement/conflict
- Key data that tips the decision
- WHY this leads to your recommendation

Output valid JSON matching the schema exactly.
</instructions>
"""



class ReflectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-sonnet-4-5-20250929",
            temperature=0.3
        )
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def execute(self, state: AgentState) -> AgentState:
        try:
            return self._execute_internal(state)
        except Exception as e:
            import traceback
            print(f"\n REFLECTION AGENT ERROR:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"\nFull traceback:")
            print(traceback.format_exc())
            raise

    def _execute_internal(self, state: AgentState) -> AgentState:

        tech = state.get('technical', {})
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
        tech_volume_detail = get_nested(tech, 'analysis.volume.detail', 'No volume detail')
        tech_trend_direction = get_nested(tech, 'analysis.trend.direction', 'NEUTRAL')
        tech_trend_strength = get_nested(tech, 'analysis.trend.strength', 'WEAK')
        tech_trend_detail = get_nested(tech, 'analysis.trend.detail', 'No trend detail')
        tech_momentum_direction = get_nested(tech, 'analysis.momentum.direction', 'NEUTRAL')
        tech_momentum_strength = get_nested(tech, 'analysis.momentum.strength', 'WEAK')
        tech_momentum_detail = get_nested(tech, 'analysis.momentum.detail', 'No momentum detail')
        tech_bullish_signals = ', '.join(tech.get('watch_list', {}).get('bullish_signals', [])) or 'None'
        tech_bearish_signals = ', '.join(tech.get('watch_list', {}).get('bearish_signals', [])) or 'None'
        tech_invalidation = ', '.join(tech.get('invalidation', [])) or 'None'

        sentiment = state.get('sentiment', {})
        sentiment_signal = sentiment.get('recommendation_signal', 'HOLD')
        sentiment_confidence_obj = sentiment.get('confidence', {})
        sentiment_confidence = float(sentiment_confidence_obj.get('score', 0.5)) if isinstance(sentiment_confidence_obj, dict) else 0.5
        sentiment_confidence_reasoning = sentiment_confidence_obj.get('reasoning', 'No reasoning provided') if isinstance(sentiment_confidence_obj, dict) else 'No reasoning provided'

        cfgi_score = get_nested(sentiment, 'market_fear_greed.score', 50)
        cfgi_classification = get_nested(sentiment, 'market_fear_greed.classification', 'Neutral')
        cfgi_social = get_nested(sentiment, 'market_fear_greed.social', 'N/A')
        cfgi_whales = get_nested(sentiment, 'market_fear_greed.whales', 'N/A')
        cfgi_trends = get_nested(sentiment, 'market_fear_greed.trends', 'N/A')
        cfgi_interpretation = get_nested(sentiment, 'market_fear_greed.interpretation', 'No interpretation')

        news_sentiment_score = get_nested(sentiment, 'news_sentiment.confidence', 0.5)
        news_sentiment_label = get_nested(sentiment, 'news_sentiment.sentiment', 'NEUTRAL')

        key_events = sentiment.get('key_events', [])
        if key_events:
            sentiment_key_events = '\n'.join([
                f"  - {e.get('title', 'Unknown')} ({e.get('type', 'Unknown')}, {e.get('impact', 'Unknown')}, {e.get('published_at', 'Unknown date')})"
                for e in key_events[:5]
            ])
        else:
            sentiment_key_events = "No key events"

        sentiment_risk_flags = ', '.join(sentiment.get('risk_flags', [])) or 'No risk flags'
        sentiment_what_to_watch = ', '.join(sentiment.get('what_to_watch', [])) or 'Nothing specific'
        sentiment_invalidation = sentiment.get('invalidation', 'Not specified')

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
            tech_confidence_reasoning=tech_confidence_reasoning,
            tech_entry=tech_entry,
            tech_stop=tech_stop,
            tech_target=tech_target,
            tech_risk_reward=tech_risk_reward,
            tech_timeframe=tech_timeframe,
            volume_ratio=volume_ratio,
            volume_quality=volume_quality,
            tech_volume_detail=tech_volume_detail,
            tech_trend_direction=tech_trend_direction,
            tech_trend_strength=tech_trend_strength,
            tech_trend_detail=tech_trend_detail,
            tech_momentum_direction=tech_momentum_direction,
            tech_momentum_strength=tech_momentum_strength,
            tech_momentum_detail=tech_momentum_detail,
            tech_bullish_signals=tech_bullish_signals,
            tech_bearish_signals=tech_bearish_signals,
            tech_invalidation=tech_invalidation,
            sentiment_signal=sentiment_signal,
            sentiment_confidence=sentiment_confidence,
            sentiment_confidence_reasoning=sentiment_confidence_reasoning,
            cfgi_score=cfgi_score,
            cfgi_classification=cfgi_classification,
            cfgi_social=cfgi_social,
            cfgi_whales=cfgi_whales,
            cfgi_trends=cfgi_trends,
            cfgi_interpretation=cfgi_interpretation,
            news_sentiment_score=news_sentiment_score,
            news_sentiment_label=news_sentiment_label,
            sentiment_key_events=sentiment_key_events,
            sentiment_risk_flags=sentiment_risk_flags,
            sentiment_what_to_watch=sentiment_what_to_watch,
            sentiment_invalidation=sentiment_invalidation
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=self.temperature,
            messages=[{"role": "user", "content": full_prompt}],
            extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
            extra_body={
                "output_format": {
                    "type": "json_schema",
                    "schema": REFLECTION_ANALYSIS_SCHEMA
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
        
        reflection_data = json.loads(json_text)

        print(" Calculating alignment score...")
        alignment_status, alignment_score = calculate_alignment_score(
            tech_recommendation=tech_recommendation,
            tech_confidence=tech_confidence,
            sentiment_signal=sentiment_signal,
            sentiment_confidence=sentiment_confidence
        )

        print(" Assessing risk level...")
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


        if 'agent_alignment' not in reflection_data:
            reflection_data['agent_alignment'] = {}

        reflection_data['agent_alignment']['alignment_score'] = alignment_score
        reflection_data['agent_alignment']['technical_says'] = f"{tech_recommendation} ({tech_confidence:.0%})"
        reflection_data['agent_alignment']['sentiment_says'] = f"{sentiment_signal} ({sentiment_confidence:.0%})"

        reflection_data['calculated_metrics'] = {
            'risk_level': risk_level,
            'secondary_risks': secondary_risks
        }

       
        reflection_data['timestamp'] = timestamp

        state['reflection'] = reflection_data

        with DataManager() as dm:
            dm.save_reflection_analysis(data=reflection_data)

        print("✅ Reflection agent completed successfully")

        return state


if __name__ == "__main__":
    test_state = AgentState()

    test_state['technical'] = {
        'timestamp': '2026-01-13T13:58:04Z',
        'recommendation_signal': 'WAIT',
        'confidence': {
            'score': 0.57,
            'reasoning': 'Moderate confidence in WAIT - dead volume (0.65x for 41 days) invalidates bullish setup despite MACD divergence. Need volume >1.0x to confirm any move.'
        },
        'market_condition': 'QUIET',
        'thinking': 'Market consolidating above $126 lows but below EMA50 resistance. MACD showing bullish divergence and Bollinger Squeeze building, but dead volume (0.65x) undermines reliability. Strong BTC correlation (0.91) with bearish BTC creates headwind. No valid setup due to volume.',
        'analysis': {
            'trend': {
                'direction': 'NEUTRAL',
                'strength': 'WEAK',
                'detail': 'Consolidating above recent lows but below key resistance at $130, lacking conviction to establish clear direction.'
            },
            'momentum': {
                'direction': 'BULLISH',
                'strength': 'WEAK',
                'detail': 'MACD histogram positive and Bollinger Squeeze active, but dead volume undermines reliability of momentum signals.'
            },
            'volume': {
                'quality': 'DEAD',
                'ratio': 0.65,
                'detail': 'Volume 35% below average with 41 days since last spike - no market participation or conviction behind any moves.'
            }
        },
        'trade_setup': {
            'viability': 'INVALID',
            'entry': 0,
            'stop_loss': 0,
            'take_profit': 0,
            'risk_reward': 0,
            'support': 126.53,
            'resistance': 130.61,
            'current_price': 128.4,
            'timeframe': 'N/A'
        },
        'action_plan': {
            'for_buyers': 'Wait on sidelines until volume returns above 1.0x average',
            'for_sellers': 'No clear sell signal, avoid shorting in low volume',
            'if_holding': 'Set tight stops near $126.50, avoid adding',
            'avoid': 'Do not chase breakouts above $130 without volume confirmation'
        },
        'watch_list': {
            'bullish_signals': ['Volume spike above 1.0x average', 'Break above $130.61 with volume'],
            'bearish_signals': ['Break below $126.53 support', 'Volume drops below 0.6x']
        },
        'invalidation': ['Volume drops below 0.6x - complete market disinterest', 'Break below $126.53 invalidates base-building'],
        'confidence_reasoning': {
            'supporting': 'MACD bullish divergence, Bollinger Squeeze building, holding above $122 lows',
            'concerns': 'Dead volume invalidates signals, bearish BTC correlation, narrow range limits profit potential'
        }
    }

    test_state['sentiment'] = {
        'timestamp': '2026-01-13T13:58:23Z',
        'recommendation_signal': 'HOLD',
        'confidence': {
            'score': 0.65,
            'reasoning': 'Moderate confidence (0.65) - CFGI at 55 (Neutral) with high retail excitement (Social 98.5) but weak whale support (26.5). RWA momentum and Ondo partnership are bullish catalysts, but news is 10+ days old. Fresh institutional confirmation needed.'
        },
        'market_condition': 'NEUTRAL',
        'thinking': 'CFGI shows neutral market at 55 with disconnect: retail very excited (Social 98.5) but institutions cautious (Whales 26.5). News is bullish (RWA momentum, Ondo partnership) but aging. Whale accumulation on Jan 1 is positive but needs volume confirmation from technicals.',
        'market_fear_greed': {
            'score': 55,
            'classification': 'Neutral',
            'social': 98.5,
            'whales': 26.5,
            'trends': 88.5,
            'sentiment': 'NEUTRAL',
            'confidence': 0.70,
            'interpretation': 'Retail excitement (Social 98.5, Trends 88.5) not matched by institutional conviction (Whales 26.5) - suggests potential top if institutions dont follow'
        },
        'news_sentiment': {
            'sentiment': 'BULLISH',
            'confidence': 0.68
        },
        'combined_sentiment': {
            'sentiment': 'NEUTRAL',
            'confidence': 0.65
        },
        'key_events': [
            {
                'title': 'Solana RWA Momentum Entering 2026',
                'type': 'ECOSYSTEM',
                'impact': 'BULLISH',
                'source': 'CoinTelegraph',
                'url': 'https://cointelegraph.com/news/solana-institutional-momentum-heading-2026',
                'published_at': '2026-01-02'
            },
            {
                'title': 'SOL Whale Accumulation on New Years Day',
                'type': 'ECOSYSTEM',
                'impact': 'BULLISH',
                'source': 'Santiment',
                'url': 'https://cointelegraph.com/news/solana-whale-accumulation',
                'published_at': '2026-01-01'
            },
            {
                'title': 'Ondo Finance Tokenized US Stocks on Solana',
                'type': 'PARTNERSHIP',
                'impact': 'BULLISH',
                'source': 'CoinTelegraph',
                'url': 'https://cointelegraph.com/news/ondo-finance-solana',
                'published_at': '2025-12-24'
            }
        ],
        'risk_flags': ['Brief stablecoin depeg on DEXs', 'Memecoin perception challenge'],
        'what_to_watch': ['RWA momentum development', 'Institutional capital inflows', 'Fresh partnership announcements'],
        'invalidation': 'Significant regulatory action or prolonged network instability',
        'suggested_timeframe': '3-5 days'
    }

    print("=" * 80)
    print("TESTING REFLECTION AGENT")
    print("=" * 80)
    print("\n📋 Input State:")
    print(f"  Technical: {test_state['technical']['recommendation_signal']} @ {test_state['technical']['confidence']['score']:.0%}")
    print(f"  Sentiment: {test_state['sentiment']['recommendation_signal']} @ {test_state['sentiment']['confidence']['score']:.0%}")
    print(f"  Volume Ratio: {test_state['technical']['analysis']['volume']['ratio']:.2f}x")
    print(f"  CFGI Score: {test_state['sentiment']['market_fear_greed']['score']}/100")

    print("\n🔄 Running Reflection Agent...")
    print("-" * 80)

    agent = ReflectionAgent()
    result_state = agent.execute(test_state)

    print("\n📊 Reflection Output:")
    reflection = result_state.get('reflection', {})
    print(f"  Final Recommendation: {reflection.get('recommendation_signal', 'N/A')}")
    print(f"  Market Condition: {reflection.get('market_condition', 'N/A')}")
    print(f"  Final Confidence: {reflection.get('confidence', {}).get('score', 0):.0%}")
    print(f"  Alignment Score: {reflection.get('agent_alignment', {}).get('alignment_score', 0):.2f}")
    print(f"\n  Confidence Reasoning:")
    print(f"  {reflection.get('confidence', {}).get('reasoning', 'N/A')}")
    print(f"\n  Primary Risk:")
    print(f"  {reflection.get('primary_risk', 'N/A')}")

    print("\n✅ Test complete!")
