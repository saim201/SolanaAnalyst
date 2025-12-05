"""
Technical Agent - Analyzes market indicators with chain-of-thought reasoning.
Uses structured 6-step analysis framework 
"""
import json
import re
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.agents.formatter import LLMDataFormatter
from app.data.indicators import classify_volume_quality


SYSTEM_PROMPT = """You are a veteran swing trader with 15 years of experience trading cryptocurrencies, specializing in 3-7 day holds. You worked as a quantitative analyst at Renaissance Technologies focusing on mean-reversion and momentum strategies.

Your trading philosophy:
- Risk management is paramount: Never risk >2% per trade
- Volume confirms everything: Low volume signals are FALSE signals
- Multiple timeframe confluence: Daily trend + 4h momentum confirmation
- Contrarian at extremes: Sell greed, buy fear
- Support must be within 5% for valid swing trades

Your analysis style is data-driven, skeptical of hype, and always considers "what could go wrong."
"""


TECHNICAL_PROMPT = """
MARKET STATE:
Current Price: ${current_price}
24h Change: {change_24h:+.2f}%
4h Pattern: {pattern_4h}
7d Summary: {summary_7d}
30d Trend: {trend_30d}
90d Trend: {trend_90d}

INTERPRETED INDICATORS:

TREND INDICATORS:
- EMA20: ${ema20:.2f} (price {ema20_dist:+.1f}% {ema20_pos})
- EMA50: ${ema50:.2f} (price {ema50_dist:+.1f}% {ema50_pos})
- EMA200: ${ema200:.2f} (price {ema200_dist:+.1f}% {ema200_pos})
→ Structure: {trend_interpretation}
→ Major Trend: {major_trend_bias}

MARKET BIAS:
- Weekly Pivot: ${pivot_weekly:.2f}
→ Current price vs pivot: {pivot_bias}

MOMENTUM INDICATORS:
- RSI: {rsi:.1f} ({rsi_state})
→ Divergence: {divergence_type} (strength: {divergence_strength:.0%})
- MACD: {macd_state} (histogram {macd_hist:+.2f}, {macd_trend})
→ Analysis: {momentum_interpretation}

VOLUME ANALYSIS (CRITICAL):
- Current: {volume_ratio:.2f}x average ({volume_classification})
- Description: {volume_description}
- 24h Surge: {volume_surge:.2f}x
- Trading Status: {trading_status}
→ Confidence Impact: {confidence_multiplier:.0%}

VOLATILITY & LEVELS:
- ATR: ${atr:.2f} (daily volatility)
- Bollinger Bands: ${bb_lower:.2f} - ${bb_upper:.2f}
- Nearest Support: ${support1:.2f} ({support1_dist:.1f}% below)
- Nearest Resistance: ${resistance1:.2f} ({resistance1_dist:.1f}% above)
- Fibonacci: 38.2%=${fib_382:.2f}, 61.8%=${fib_618:.2f}
→ Risk/Reward: {rr_interpretation}

<analysis_framework>
You MUST analyse in this EXACT order:

<thinking>
STEP 1: TREND IDENTIFICATION
- What direction is price moving? (check EMA20 vs EMA50 vs current price)
- Is trend strong, weak, or range-bound?
- Are we in consolidation or breakout?
- Document your reasoning: [Write 2-3 sentences]

STEP 2: MOMENTUM ASSESSMENT
- Is RSI showing strength or weakness?
- Is MACD bullish or bearish? Is histogram expanding or contracting?
- Are momentum indicators CONFIRMING or CONTRADICTING the trend?
- Check RSI divergence - is it signaling reversal?
- Document your reasoning: [Write 2-3 sentences]

STEP 3: VOLUME VALIDATION (CRITICAL - MOST IMPORTANT STEP)
- What is the volume classification? (STRONG/ACCEPTABLE/WEAK/DEAD)
- Is volume sufficient for a real move? (>1.0x REQUIRED)
- Is this a low-liquidity trap? (<0.7x = RED FLAG - AUTO REJECT)
- Can we trust this signal given current participation?
- Document your reasoning: [Write 2-3 sentences]

STEP 4: RISK/REWARD SETUP
- Where are the nearest support/resistance levels?
- What's the risk (distance to stop loss) vs reward (distance to target)?
- Is R:R ratio at least 1.5:1? (REQUIRED for swing trades)
- Can we get stopped out by normal noise?
- Document your reasoning: [Write 2-3 sentences]

STEP 5: CONFLICTING SIGNALS CHECK
- Are ANY indicators contradicting your bias?
- What's the bear case if considering BUY? What's the bull case if considering SELL?
- What could invalidate this trade thesis in next 24-48 hours?
- Are we missing any red flags?
- Document your reasoning: [Write 2-3 sentences]

STEP 6: FINAL DECISION
- Given ALL analysis above, what's your recommendation?
- What's your confidence level (0.0 to 1.0)?
- If recommending HOLD, explain why no trade is better than forced trade
</thinking>

<answer>
Based on the above 6-step analysis, provide your trading recommendation in this EXACT JSON format:

{{
  "recommendation": "BUY|SELL|HOLD",
  "confidence": 0.75,
  "confidence_breakdown": {{
    "trend_strength": 0.8,
    "momentum_confirmation": 0.7,
    "volume_quality": 0.6,
    "risk_reward": 0.9,
    "final_adjusted": 0.75
  }},
  "timeframe": "3-7 days",
  "key_signals": [
    "price above EMA20 (bullish structure)",
    "MACD bullish crossover",
    "volume WEAK - reduces confidence"
  ],
  "entry_level": 185.50,
  "stop_loss": 178.00,
  "take_profit": 198.00,
  "reasoning": "Strong technical setup with bullish MACD and price above EMA20, but WEAK volume (0.85x) reduces conviction. Entry at current level with stop below support. Target resistance at $198."
}}
</answer>
</analysis_framework>

CRITICAL RULES (OVERRIDE EVERYTHING):
1. If volume_ratio < 0.7 (DEAD), you MUST recommend HOLD regardless of other signals
2. If no clear support within 5% below entry, you MUST recommend HOLD
3. If risk/reward ratio < 1.5, you MUST recommend HOLD
4. If you see conflicting signals (e.g., bullish MACD but bearish RSI divergence), state this explicitly and lower confidence
5. Never recommend entry without calculating exact stop_loss and take_profit levels
6. If recommending HOLD, set entry_level, stop_loss, take_profit to null
"""


class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.3
        )

    def execute(self, state: AgentState) -> AgentState:
        llm_data = LLMDataFormatter.format_for_technical_agent()

        snapshot = llm_data.get("current_snapshot", {})
        trends = llm_data.get("price_trends", {})
        indicators = llm_data.get("indicators", {})

        current_price = snapshot.get("lastPrice", 0)
        change_24h = snapshot.get("priceChangePercent", 0)
        pattern_4h = llm_data.get("intraday_4h_pattern", "no data")

        if "daily" in indicators:
            daily_ind = indicators.get("daily", {})
            trend_ind = daily_ind.get("trend", {})
            momentum_ind = daily_ind.get("momentum", {})
            vol_ind = daily_ind.get("volatility", {})
            sr_ind = daily_ind.get("support_resistance", {})
            volume_ind = daily_ind.get("volume", {})
        else:
            trend_ind = indicators.get("trend", {})
            momentum_ind = indicators.get("momentum", {})
            vol_ind = indicators.get("volatility", {})
            sr_ind = indicators.get("support_resistance", {})
            volume_ind = indicators.get("volume", {})

        ticker_24h = indicators.get("ticker_24h", {})

        # Calculate interpretations
        ema20 = trend_ind.get('ema20', 0)
        ema50 = trend_ind.get('ema50', 0)
        ema200 = trend_ind.get('ema200', 0)
        ema20_dist = ((current_price - ema20) / ema20 * 100) if ema20 > 0 else 0
        ema50_dist = ((current_price - ema50) / ema50 * 100) if ema50 > 0 else 0
        ema200_dist = ((current_price - ema200) / ema200 * 100) if ema200 > 0 else 0
        ema20_pos = "ABOVE ✅" if ema20_dist > 0 else "BELOW ❌"
        ema50_pos = "ABOVE ✅" if ema50_dist > 0 else "BELOW ❌"
        ema200_pos = "ABOVE ✅" if ema200_dist > 0 else "BELOW ❌"

        # Trend interpretation WITH EMA200 
        if current_price > ema20 > ema50:
            trend_interpretation = f"Strong bullish (price {ema50_dist:.1f}% above EMA50)"
        elif current_price > ema20 and ema20 < ema50:
            trend_interpretation = "Weak bullish (consolidation)"
        elif current_price < ema20 and ema20 > ema50:
            trend_interpretation = "Weak bearish (potential reversal)"
        elif current_price < ema20 < ema50:
            trend_interpretation = f"Strong bearish (price {abs(ema50_dist):.1f}% below EMA50)"
        else:
            trend_interpretation = "Range-bound"

        # Major trend bias 
        if ema200 > 0:
            if current_price > ema200:
                major_trend_bias = f"✅ BULL MARKET (price {ema200_dist:.1f}% above 200 EMA - favor longs)"
            else:
                major_trend_bias = f"❌ BEAR MARKET (price {abs(ema200_dist):.1f}% below 200 EMA - favor shorts)"
        else:
            major_trend_bias = "⚠️ Insufficient data for 200 EMA"

        # Weekly Pivot bias
        pivot_weekly = indicators.get('pivot', {}).get('weekly', 0) if 'pivot' in indicators else indicators.get('pivot_weekly', 0)
        if pivot_weekly and pivot_weekly > 0:
            if current_price > pivot_weekly:
                pivot_dist = ((current_price - pivot_weekly) / pivot_weekly * 100)
                pivot_bias = f"✅ BULLISH week (price {pivot_dist:.1f}% above weekly pivot)"
            else:
                pivot_dist = ((pivot_weekly - current_price) / pivot_weekly * 100)
                pivot_bias = f"❌ BEARISH week (price {pivot_dist:.1f}% below weekly pivot)"
        else:
            pivot_bias = "No pivot data"

        # Momentum
        rsi = momentum_ind.get('rsi14', 50)
        rsi_state = "OVERSOLD (<30)" if rsi < 30 else "OVERBOUGHT (>70)" if rsi > 70 else "NEUTRAL"
        divergence_type = momentum_ind.get('rsi_divergence_type', 'NONE')
        divergence_strength = momentum_ind.get('rsi_divergence_strength', 0.0)

        macd_hist = momentum_ind.get('macd_histogram', 0)
        macd_state = "BULLISH ✅" if macd_hist > 0 else "BEARISH ❌"
        macd_trend = "STRENGTHENING" if abs(macd_hist) > 2 else "WEAKENING" if abs(macd_hist) < 0.5 else "STABLE"

        if divergence_type == "BEARISH":
            momentum_interpretation = f"⚠️ BEARISH DIVERGENCE - reversal risk"
        elif divergence_type == "BULLISH":
            momentum_interpretation = f"✅ BULLISH DIVERGENCE - reversal signal"
        elif rsi < 30 and macd_hist > 0:
            momentum_interpretation = "Oversold bounce signal"
        elif rsi > 70 and macd_hist < 0:
            momentum_interpretation = "Overbought correction signal"
        else:
            momentum_interpretation = f"{'Building bullish' if macd_hist > 0 else 'Building bearish'} momentum"

        # Volume
        volume_ratio = volume_ind.get('volume_ratio', 1.0)
        volume_quality = classify_volume_quality(volume_ratio)
        volume_classification = volume_quality['classification']
        volume_description = volume_quality['description']
        trading_status = "✅ ALLOWED" if volume_quality['trading_allowed'] else "❌ BLOCKED - Wait for volume"
        confidence_multiplier = volume_quality['confidence_multiplier']
        volume_surge = ticker_24h.get('volume_surge_24h', 1.0)

        # Support/Resistance
        support_list = sr_ind.get('support', [{}])
        resistance_list = sr_ind.get('resistance', [{}])
        support1 = support_list[0].get('level', 0) if support_list else 0
        support1_dist = abs(support_list[0].get('distance_percent', 0)) if support_list else 0
        resistance1 = resistance_list[0].get('level', 0) if resistance_list else 0
        resistance1_dist = resistance_list[0].get('distance_percent', 0) if resistance_list else 0

        # Risk/Reward
        if support1_dist > 0 and resistance1_dist > 0:
            rr_ratio = resistance1_dist / support1_dist
            if rr_ratio >= 2.5:
                rr_interpretation = f"Excellent {rr_ratio:.1f}:1 ✅"
            elif rr_ratio >= 1.8:
                rr_interpretation = f"Good {rr_ratio:.1f}:1"
            elif rr_ratio >= 1.5:
                rr_interpretation = f"Acceptable {rr_ratio:.1f}:1"
            else:
                rr_interpretation = f"Poor {rr_ratio:.1f}:1 ❌"
        else:
            rr_interpretation = "Unable to calculate"

        # Volatility
        atr = vol_ind.get('atr', 0)
        bb_upper = vol_ind.get('bb_upper', 0)
        bb_lower = vol_ind.get('bb_lower', 0)

        # Fibonacci
        fib_382 = indicators.get('fibonacci', {}).get('fib_382', 0) if 'fibonacci' in indicators else indicators.get('fib_level_382', 0)
        fib_618 = indicators.get('fibonacci', {}).get('fib_618', 0) if 'fibonacci' in indicators else indicators.get('fib_level_618', 0)

        # Build complete prompt
        full_prompt = SYSTEM_PROMPT + "\n\n" + TECHNICAL_PROMPT.format(
            current_price=current_price,
            change_24h=change_24h,
            pattern_4h=pattern_4h,
            summary_7d=trends.get("last_7d", "no data"),
            trend_30d=trends.get("trend_30d", "no data"),
            trend_90d=trends.get("trend_90d", "no data"),
            ema20=ema20,
            ema20_dist=ema20_dist,
            ema20_pos=ema20_pos,
            ema50=ema50,
            ema50_dist=ema50_dist,
            ema50_pos=ema50_pos,
            ema200=ema200,
            ema200_dist=ema200_dist,
            ema200_pos=ema200_pos,
            trend_interpretation=trend_interpretation,
            major_trend_bias=major_trend_bias,
            pivot_weekly=pivot_weekly,
            pivot_bias=pivot_bias,
            rsi=rsi,
            rsi_state=rsi_state,
            divergence_type=divergence_type,
            divergence_strength=divergence_strength,
            macd_state=macd_state,
            macd_hist=macd_hist,
            macd_trend=macd_trend,
            momentum_interpretation=momentum_interpretation,
            volume_ratio=volume_ratio,
            volume_classification=volume_classification,
            volume_description=volume_description,
            volume_surge=volume_surge,
            trading_status=trading_status,
            confidence_multiplier=confidence_multiplier,
            atr=atr,
            bb_lower=bb_lower,
            bb_upper=bb_upper,
            support1=support1,
            support1_dist=support1_dist,
            resistance1=resistance1,
            resistance1_dist=resistance1_dist,
            fib_382=fib_382,
            fib_618=fib_618,
            rr_interpretation=rr_interpretation,
        )

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=1000
        )

        try:
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            thinking = thinking_match.group(1).strip() if thinking_match else ""

            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            if answer_match:
                answer_json = answer_match.group(1).strip()
            else:
                # Fallback: try to extract JSON without tags
                answer_json = response


            answer_json = re.sub(r'```json\s*|\s*```', '', answer_json).strip()

            analysis = json.loads(answer_json)

            state['recommendation'] = analysis.get('recommendation', 'HOLD')
            state['confidence'] = float(analysis.get('confidence', 0.5))
            state['timeframe'] = analysis.get('timeframe', '3-7 days')
            state['key_signals'] = analysis.get('key_signals', [])
            state['entry_level'] = analysis.get('entry_level')
            state['stop_loss'] = analysis.get('stop_loss')
            state['take_profit'] = analysis.get('take_profit')
            state['reasoning'] = analysis.get('reasoning', '')

            # Store thinking for debugging
            state['indicators_analysis'] = json.dumps({
                'thinking': thinking[:500],  
                'recommendation': state['recommendation'],
                'confidence': state['confidence'],
                'key_signals': state['key_signals']
            })

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Technical agent parsing error: {e}")
            print(f"Response: {response[:300]}")
            state['recommendation'] = 'HOLD'
            state['confidence'] = 0.0
            state['reasoning'] = f"Analysis parsing error: {str(e)[:100]}"
            state['indicators_analysis'] = response[:500]

        return state


if __name__ == "__main__":
    agent = TechnicalAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== TECHNICAL AGENT OUTPUT =====")
    print(f"\n TEchnical Analysis: \n {result}")
    print(f"Recommendation: {result.get('recommendation')}")
    print(f"Confidence: {result.get('confidence')}")
    print(f"Reasoning: {result.get('reasoning')}")
