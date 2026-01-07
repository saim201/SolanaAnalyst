# technical.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional, Any

from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager


SYSTEM_PROMPT = """You are a veteran swing trader analysing SOLANA (SOL/USDT) with 15 years of crypto market experience, specializing in 1-14 day holds.

YOUR TRADING PHILOSOPHY:
- Risk management is paramount: Never risk more than you can define
- Volume confirms everything: Low volume moves are suspect
- Trend is your friend: Trade with the trend, not against it
- Patience pays: No trade is better than a bad trade
- Be honest about uncertainty: When the picture is unclear, say so

YOUR ANALYSIS STYLE:
- Tell the STORY of what's happening, not just data points
- Think like a detective: What are buyers/sellers doing? Who's winning?
- Always explain the "why" behind moves
- Forward-looking: What happens next? What are we watching for?
- Speak to intermediate traders: Clear, actionable, no unnecessary jargon

SOLANA CONTEXT:
- SOL is a high-volatility L1 blockchain cryptocurrency
- Typical 15-30% pullbacks even in strong uptrends - this is normal
- Usually 0.75-0.90 correlation with BTC - when BTC moves, SOL often follows with amplification
"""


TECHNICAL_PROMPT = """
<market_data>
## CURRENT MARKET STATE
**Analysis Timestamp:** {analysis_timestamp}
**Price:** ${current_price:.2f} | **24h Change:** {change_24h:+.2f}%
**24h Range:** ${low_24h:.2f} - ${high_24h:.2f} (currently at {range_position_24h:.0%} of range)

---

## CORE INDICATORS

<trend_indicators>
**TREND:**
- EMA20: ${ema20:.2f} ({ema20_distance:+.1f}% from price)
- EMA50: ${ema50:.2f} ({ema50_distance:+.1f}% from price)
- 14d High: ${high_14d:.2f} | 14d Low: ${low_14d:.2f}
- Price Position in 14d Range: {price_position_14d:.0%}
</trend_indicators>

<momentum_indicators>
**MOMENTUM:**
- RSI(14): {rsi14:.1f} {rsi_status}
- MACD Line: {macd_line:.4f} | Signal: {macd_signal:.4f}
- MACD Histogram: {macd_histogram:.4f} ({macd_trend})
- RSI Divergence: {rsi_divergence_type} (strength: {rsi_divergence_strength:.2f})
</momentum_indicators>

<volume_indicators>
**VOLUME (CRITICAL - This can invalidate all other signals):**
- Volume Ratio: {volume_ratio:.2f}x average ({volume_classification})
- Buy Pressure (7d weighted): {weighted_buy_pressure:.1f}% (>50% = buyers dominating)
- Days Since Volume Spike (>1.5x): {days_since_volume_spike}
- Volume Trend: {volume_trend}
</volume_indicators>

<key_levels>
**KEY LEVELS:**
- Support 1: ${support1:.2f} ({support1_distance:.1f}% below current price)
- Support 2: ${support2:.2f} ({support2_distance:.1f}% below current price)
- Resistance 1: ${resistance1:.2f} ({resistance1_distance:.1f}% above current price)
- Resistance 2: ${resistance2:.2f} ({resistance2_distance:.1f}% above current price)
</key_levels>

---

## SITUATIONAL INDICATORS (Use if relevant)

<volatility_indicators>
**VOLATILITY:**
- ATR(14): ${atr:.2f} ({atr_percent:.1f}% of price) - {atr_interpretation}
- Bollinger Squeeze: {bb_squeeze_status} (ratio: {bb_squeeze_ratio:.1f}%)
</volatility_indicators>

<btc_correlation>
**BTC CORRELATION:**
- SOL-BTC Correlation (30d): {sol_btc_correlation:.2f} ({correlation_strength})
- BTC Trend: {btc_trend}
- BTC 30d Change: {btc_price_change_30d:+.1f}%
- Interpretation: {btc_interpretation}
</btc_correlation>

---

## RECENT PRICE ACTION (Last 7 Days with Timestamps)

<price_history>
{recent_price_action}
</price_history>

</market_data>

---

<instructions>
## YOUR TASK

Analyse the market data above using chain-of-thought reasoning. You MUST:

1. First, write your detailed reasoning inside <thinking> tags
2. Then, provide your final analysis as JSON inside <answer> tags

### THINKING PROCESS (inside <thinking> tags):

Work through these steps IN ORDER:

**Step 1 - MARKET STORY:** What's the big picture? Where are we in the trend cycle? Is this an uptrend, downtrend, or range?

**Step 2 - VOLUME CHECK:** Is there conviction behind the current move? CRITICAL: If volume_ratio < 0.7, this invalidates most other signals. State this clearly.

**Step 3 - MOMENTUM READ:** Is the move accelerating, steady, or fading? What does RSI + MACD tell us together?

**Step 4 - BTC CONTEXT:** Given the correlation level, how much does BTC's trend matter right now?

**Step 5 - SETUP IDENTIFICATION:** Is there a tradeable opportunity? Calculate specific entry, stop loss, take profit, and risk/reward ratio. If no good setup exists, explain why.

**Step 6 - RISK ASSESSMENT:** What could go wrong? What would invalidate your thesis?

**Step 7 - CONFIDENCE CALIBRATION:** What factors support your view? What concerns do you have? Arrive at a final confidence score (0.0-1.0).

### CRITICAL RULES:

- If volume_ratio < 0.7 (DEAD): You MUST recommend HOLD or WAIT
- If no support within 5% below current price: HOLD or WAIT
- If risk/reward < 1.5:1: HOLD or WAIT
- Always provide specific price levels, not vague guidance
- Be honest when the picture is unclear

### CONFIDENCE GUIDELINES:

<confidence_guidelines>
## Analysis Confidence (0.70-0.95)
How confident are you in this ANALYSIS (not the trade)?

- 0.90-0.95: Crystal clear market state, all indicators align
- 0.80-0.89: Clear picture, minor ambiguities
- 0.70-0.79: Reasonable clarity, some conflicting signals

NOTE: Even a WAIT recommendation_signal should have HIGH analysis_confidence if you're sure it's time to wait!

## Setup Quality (0.0-1.0)
How good is the TRADE SETUP (if someone were to trade)?

- 0.80-1.00: Excellent setup, multiple confirmations
- 0.60-0.79: Good setup, some concerns
- 0.40-0.59: Moderate setup, significant concerns
- 0.20-0.39: Poor setup, major issues
- 0.00-0.19: Invalid setup, do not trade

CRITICAL RULES:
- If recommendation_signal is WAIT → setup_quality should be ≤ 0.35
- If volume_ratio < 0.7 → setup_quality should be ≤ 0.25
- If risk/reward < 1.5 → setup_quality should be ≤ 0.40
- If recommendation_signal is BUY/SELL → setup_quality should be ≥ 0.65

## Interpretation
Explain WHY these confidence levels with SPECIFIC data:
- "I'm 88% confident in WAIT because volume is dead (0.56x for 43 days) and we're at resistance with 0.88:1 risk/reward"
- "High confidence BUY (85%) - volume spike 2.1x with breakout above $140, RSI 58 (healthy), strong 1.8:1 R/R"
- "Moderate confidence (72%) - trend is bullish but BTC correlation (0.91) with bearish BTC creates uncertainty"

Include: volume ratio, key price levels, risk/reward, or BTC context. Be specific, not generic.
</confidence_guidelines>

### OUTPUT FORMAT:

After your thinking, output the final JSON inside <answer> tags. The JSON must follow this EXACT structure:

```json
{{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",

  "confidence": {{
    "analysis_confidence": 0.85,
    "setup_quality": 0.72,
    "interpretation": "High confidence in analysis, good trade setup"
  }},

  "market_condition": "TRENDING|RANGING|VOLATILE|QUIET",

  "summary": "2-3 sentences: What's happening and what to do. Be specific and actionable.",

  "thinking": "MARKET STORY
    [Write 2-4 sentences explaining price action, trend direction, where we are in the cycle. Include specific values like EMA levels, price ranges, key resistance/support.]

    VOLUME ASSESSMENT
    [Write 2-4 sentences analysing volume quality. State the ratio, days since spike, how volume behaves during moves. This is CRITICAL - be detailed if volume is weak.]

    MOMENTUM CHECK
    [Write 2-4 sentences on RSI, MACD, momentum direction. Reference actual values like 'RSI 66.9 approaching overbought' not just 'RSI high'.]

    BTC CONTEXT
    [Write 2-3 sentences on correlation strength, BTC trend, how this impacts SOL. Only include if correlation >0.75 or BTC trend is significant.]

    SETUP EVALUATION
    [Write 2-4 sentences on risk/reward, entry/exit levels, viability. Be specific: '0.88:1 R/R is below 1.5:1 minimum' not 'poor R/R'.]

    FINAL CALL
    [Write 2-3 sentences synthesising everything into your recommendation_signal. Be decisive and clear.]",



  "analysis": {{
    "trend": {{
      "direction": "BULLISH|BEARISH|NEUTRAL",
      "strength": "STRONG|MODERATE|WEAK",
      "detail": "2-3 sentences explaining WHY this direction/strength, referencing SPECIFIC indicator values (EMAs, price levels, volume ratio, RSI). Example: 'Uptrend confirmed by price above EMA20 ($133), rallied 9% from $123 to $134. However, testing EMA50 resistance with weak volume (0.56x) suggests fragility.'"
    }},
    "momentum": {{
      "direction": "BULLISH|BEARISH|NEUTRAL",
      "strength": "STRONG|MODERATE|WEAK",
      "detail": "2-3 sentences explaining WHY this direction/strength, referencing SPECIFIC indicator values (EMAs, price levels, volume ratio, RSI). Example: 'Uptrend confirmed by price above EMA20 ($133), rallied 9% from $123 to $134. However, testing EMA50 resistance with weak volume (0.56x) suggests fragility.'"
    }},
    "volume": {{
      "quality": "STRONG|ACCEPTABLE|WEAK|DEAD",
      "ratio": 0.82,
      "detail": "2-3 sentences explaining WHY this direction/strength, referencing SPECIFIC indicator values (EMAs, price levels, volume ratio, RSI). Example: 'Uptrend confirmed by price above EMA20 ($133), rallied 9% from $123 to $134. However, testing EMA50 resistance with weak volume (0.56x) suggests fragility.'"
    }}
  }},

  "trade_setup": {{
    "viability": "VALID|WAIT|INVALID",
    "entry": 184.00,
    "stop_loss": 176.50,
    "take_profit": 198.00,
    "risk_reward": 1.8,
    "support": 184.00,
    "resistance": 195.00,
    "current_price": 188.50,
    "timeframe": "3-5 days"
  }},

  "action_plan": {{
    "for_buyers": "Specific guidance for someone wanting to BUY (entry conditions, what to wait for)",
    "for_sellers": "Specific guidance for someone wanting to SELL/SHORT (exit conditions, when to act)",
    "if_holding": "Guidance for existing holders (take profit levels, stop placement)",
    "avoid": "What NOT to do (minimum 2-3 specific things to avoid)"
  }},

  "watch_list": {{
    "bullish_signals": [
    "Specific condition that would make setup bullish (e.g., 'Volume spike >1.5x + break above $135')",
    "Another bullish trigger"
    ],
    "bearish_signals": [
    "Specific condition that would invalidate setup (e.g., 'Break below $127 support')",
    "Another bearish trigger"
    ]
  }},

  "invalidation": [
    "Condition 1 that kills the thesis",
    "Condition 2 that kills the thesis"
  ],

  "confidence_reasoning": {{
    "supporting": "Write 2-5 sentences explaining what SUPPORTS your recommendation_signal. Be specific with numbers and logic. Example: 'The WAIT call is backed by clear dead volume (0.56x, no spike in 43 days), poor risk/reward at resistance (0.88:1 vs 1.5:1 minimum), and bearish BTC correlation (0.92 with BTC down 4.3%).'",
    "concerns": "Write 2-5 sentences on what COULD GO WRONG or arguments against your call. Be honest. Example: 'The bull case exists: short-term trend still up, MACD histogram positive, sudden volume could change everything. But current data says wait.'"
  }}
}}
```

IMPORTANT NOTES:
- Write your full reasoning in <thinking> tags FIRST
- Then output ONLY valid JSON in <answer> tags
- All price values should be numbers, not strings
- Confidence is now a nested object with analysis_confidence, setup_quality, and interpretation
- If recommending HOLD/WAIT, set entry/stop_loss/take_profit to null but still provide support/resistance/current_price. timeframe should NEVER be null. For WAIT: use "Wait 1-3 days for volume confirmation". For HOLD: use "Monitor next 2-4 days". For BUY/SELL: use any specific timeframe.
</instructions>
"""



def calculate_distance_percent(current: float, level: float) -> float:
    if current == 0:
        return 0.0
    return ((level - current) / current) * 100


def get_btc_interpretation(correlation: float, btc_trend: str) -> str:
    if correlation >= 0.75:
        if btc_trend == "BULLISH":
            return "High correlation + bullish BTC = supportive for SOL upside"
        elif btc_trend == "BEARISH":
            return "High correlation + bearish BTC = headwind for SOL"
        else:
            return "High correlation but BTC neutral - watch BTC for direction"
    elif correlation >= 0.5:
        return "Moderate correlation - SOL may diverge from BTC short-term"
    else:
        return "Low correlation - SOL trading independently of BTC"


def get_rsi_status(rsi: float) -> str:
    if rsi >= 70:
        return "(OVERBOUGHT - potential reversal)"
    elif rsi >= 60:
        return "(Bullish, approaching overbought)"
    elif rsi <= 30:
        return "(OVERSOLD - potential bounce)"
    elif rsi <= 40:
        return "(Bearish, approaching oversold)"
    else:
        return "(Neutral zone)"


def get_macd_trend(histogram: float, prev_histogram: float = None) -> str:
    if histogram > 0:
        return "Positive - bullish momentum"
    elif histogram < 0:
        return "Negative - bearish momentum"
    else:
        return "Neutral"


def get_atr_interpretation(atr_percent: float) -> str:
    if atr_percent >= 8:
        return "HIGH volatility - expect large swings"
    elif atr_percent >= 4:
        return "MODERATE volatility - normal for SOL"
    else:
        return "LOW volatility - potential breakout building"


def get_volume_trend(buy_pressure: float, volume_ratio: float) -> str:
    if volume_ratio < 0.7:
        return "DEAD - No conviction, signals unreliable"
    elif volume_ratio < 1.0:
        if buy_pressure > 55:
            return "Below average but buyers active"
        elif buy_pressure < 45:
            return "Below average with selling pressure"
        else:
            return "Below average, neutral pressure"
    else:
        if buy_pressure > 55:
            return "Above average with strong buying"
        elif buy_pressure < 45:
            return "Above average but sellers dominating"
        else:
            return "Above average, balanced"


def get_correlation_strength(correlation: float) -> str:
    if correlation >= 0.8:
        return "VERY STRONG"
    elif correlation >= 0.6:
        return "STRONG"
    elif correlation >= 0.4:
        return "MODERATE"
    else:
        return "WEAK"


def format_recent_price_action(candles: list, limit: int = 7) -> str:
    if not candles:
        return "No recent data available"

    lines = []
    for candle in candles[-limit:]:
        date_str = candle.get('open_time', 'N/A')
        if hasattr(date_str, 'strftime'):
            formatted_date = date_str.strftime('%Y-%m-%d (%a)')
        elif isinstance(date_str, str):
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%Y-%m-%d (%a)')
            except:
                formatted_date = date_str[:10] if len(date_str) >= 10 else date_str
        else:
            formatted_date = str(date_str)

        o = candle.get('open', 0)
        h = candle.get('high', 0)
        l = candle.get('low', 0)
        c = candle.get('close', 0)
        vol = candle.get('volume', 0)
        taker_buy = candle.get('taker_buy_base', 0)

        change = ((c - o) / o * 100) if o > 0 else 0
        buy_ratio = (taker_buy / vol * 100) if vol > 0 else 50
        candle_type = "🟢 BULLISH" if c >= o else "🔴 BEARISH"

        lines.append(
            f"  {formatted_date}: {candle_type} | "
            f"Open: ${o:.2f} → Close: ${c:.2f} ({change:+.1f}%) | "
            f"Range: ${l:.2f}-${h:.2f} | "
            f"Vol: {vol:,.0f} | Buy%: {buy_ratio:.0f}%"
        )

    return "\n".join(lines)


def calculate_price_position_in_range(current: float, high_14d: float, low_14d: float) -> float:
    range_size = high_14d - low_14d
    if range_size == 0:
        return 0.5
    return (current - low_14d) / range_size



class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-sonnet-4-20250514",
            temperature=0.3
        )

    def execute(self, state: AgentState) -> AgentState:
        with DataQuery() as dq:
            ticker = dq.get_ticker_data()
            if not ticker:
                raise ValueError("No ticker data available")

            indicators_data = dq.get_indicators_data()
            if not indicators_data:
                raise ValueError("No indicators data available")

            daily_candles = dq.get_candlestick_data(days=14)

        current_price = float(ticker.get('lastPrice', 0))
        change_24h = float(ticker.get('priceChangePercent', 0))
        high_24h = float(ticker.get('highPrice', 0))
        low_24h = float(ticker.get('lowPrice', 0))

        range_24h = high_24h - low_24h
        range_position_24h = (current_price - low_24h) / range_24h if range_24h > 0 else 0.5

        # Trend
        ema20 = float(indicators_data.get('ema20', 0))
        ema50 = float(indicators_data.get('ema50', 0))
        high_14d = float(indicators_data.get('high_14d', 0))
        low_14d = float(indicators_data.get('low_14d', 0))

        # Momentum
        rsi14 = float(indicators_data.get('rsi14', 50))
        macd_line = float(indicators_data.get('macd_line', 0))
        macd_signal = float(indicators_data.get('macd_signal', 0))
        macd_histogram = float(indicators_data.get('macd_histogram', 0))
        rsi_divergence_type = indicators_data.get('rsi_divergence_type', 'NONE')
        rsi_divergence_strength = float(indicators_data.get('rsi_divergence_strength', 0))

        # Volume
        volume_ratio = float(indicators_data.get('volume_ratio', 1.0))
        volume_classification = indicators_data.get('volume_classification', 'ACCEPTABLE')
        weighted_buy_pressure = float(indicators_data.get('weighted_buy_pressure', 50.0))
        days_since_volume_spike = int(indicators_data.get('days_since_volume_spike', 999))

        # Key levels
        support1 = float(indicators_data.get('support1') or current_price * 0.95)
        support2 = float(indicators_data.get('support2') or current_price * 0.90)
        resistance1 = float(indicators_data.get('resistance1') or current_price * 1.05)
        resistance2 = float(indicators_data.get('resistance2') or current_price * 1.10)

        # Volatility
        atr = float(indicators_data.get('atr', 0))
        atr_percent = float(indicators_data.get('atr_percent', 0))
        bb_squeeze_ratio = float(indicators_data.get('bb_squeeze_ratio', 0))
        bb_squeeze_active = indicators_data.get('bb_squeeze_active', False)

        sol_btc_correlation = float(indicators_data.get('sol_btc_correlation', 0.8))
        btc_trend = indicators_data.get('btc_trend', 'NEUTRAL')
        btc_price_change_30d = float(indicators_data.get('btc_price_change_30d', 0))

        ema20_distance = calculate_distance_percent(current_price, ema20)
        ema50_distance = calculate_distance_percent(current_price, ema50)
        support1_distance = abs(calculate_distance_percent(current_price, support1))
        support2_distance = abs(calculate_distance_percent(current_price, support2))
        resistance1_distance = calculate_distance_percent(current_price, resistance1)
        resistance2_distance = calculate_distance_percent(current_price, resistance2)
        price_position_14d = calculate_price_position_in_range(current_price, high_14d, low_14d)

        rsi_status = get_rsi_status(rsi14)
        macd_trend = get_macd_trend(macd_histogram)
        bb_squeeze_status = "ACTIVE (breakout imminent)" if bb_squeeze_active else "INACTIVE"
        btc_interpretation = get_btc_interpretation(sol_btc_correlation, btc_trend)
        atr_interpretation = get_atr_interpretation(atr_percent)
        volume_trend = get_volume_trend(weighted_buy_pressure, volume_ratio)
        correlation_strength = get_correlation_strength(sol_btc_correlation)

        recent_price_action = format_recent_price_action(daily_candles, limit=7)

        analysis_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

        full_prompt = SYSTEM_PROMPT + "\n\n" + TECHNICAL_PROMPT.format(
            analysis_timestamp=analysis_timestamp,
            current_price=current_price,
            change_24h=change_24h,
            high_24h=high_24h,
            low_24h=low_24h,
            range_position_24h=range_position_24h,
            ema20=ema20,
            ema50=ema50,
            ema20_distance=ema20_distance,
            ema50_distance=ema50_distance,
            high_14d=high_14d,
            low_14d=low_14d,
            price_position_14d=price_position_14d,
            rsi14=rsi14,
            rsi_status=rsi_status,
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            macd_trend=macd_trend,
            rsi_divergence_type=rsi_divergence_type,
            rsi_divergence_strength=rsi_divergence_strength,
            volume_ratio=volume_ratio,
            volume_classification=volume_classification,
            weighted_buy_pressure=weighted_buy_pressure,
            days_since_volume_spike=days_since_volume_spike,
            volume_trend=volume_trend,
            support1=support1,
            support2=support2,
            resistance1=resistance1,
            resistance2=resistance2,
            support1_distance=support1_distance,
            support2_distance=support2_distance,
            resistance1_distance=resistance1_distance,
            resistance2_distance=resistance2_distance,
            atr=atr,
            atr_percent=atr_percent,
            atr_interpretation=atr_interpretation,
            bb_squeeze_status=bb_squeeze_status,
            bb_squeeze_ratio=bb_squeeze_ratio,
            sol_btc_correlation=sol_btc_correlation,
            correlation_strength=correlation_strength,
            btc_trend=btc_trend,
            btc_price_change_30d=btc_price_change_30d,
            btc_interpretation=btc_interpretation,
            recent_price_action=recent_price_action,
        )

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=4096
        )

        try:
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            raw_thinking = thinking_match.group(1).strip() if thinking_match else ""

            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            if answer_match:
                json_str = answer_match.group(1).strip()
            else:
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")

            json_str = json_str.replace('\u201c', '"').replace('\u201d', '"')
            json_str = json_str.replace('\u2018', "'").replace('\u2019', "'")
            json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)

            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)

            first_brace = json_str.find('{')
            last_brace = json_str.rfind('}')
            if first_brace != -1 and last_brace != -1:
                json_str = json_str[first_brace:last_brace+1]

            analysis = json.loads(json_str)

            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            confidence = analysis.get('confidence', {})
            if isinstance(confidence, (int, float)):
                # Backward compatibility: convert old single float to nested object
                confidence = {
                    'analysis_confidence': 0.75,
                    'setup_quality': float(confidence),
                    'interpretation': f'Legacy format: {confidence:.0%} confidence'
                }
            elif not isinstance(confidence, dict):
                # Fallback for invalid format
                confidence = {
                    'analysis_confidence': 0.5,
                    'setup_quality': 0.5,
                    'interpretation': 'Default confidence'
                }

            state['technical'] = {
                'timestamp': analysis.get('timestamp', timestamp),
                'recommendation_signal': analysis.get('recommendation_signal', 'HOLD'),
                'confidence': confidence,
                'market_condition': analysis.get('market_condition', 'QUIET'),
                'summary': analysis.get('summary', ''),
                'thinking': analysis.get('thinking', []),
                'analysis': analysis.get('analysis', {}),
                'trade_setup': analysis.get('trade_setup', {}),
                'action_plan': analysis.get('action_plan', {}),
                'watch_list': analysis.get('watch_list', {}),
                'invalidation': analysis.get('invalidation', []),
                'confidence_reasoning': analysis.get('confidence_reasoning', {}),
            }

            with DataManager() as dm:
                dm.save_technical_analysis(data=state['technical'])


        except (json.JSONDecodeError, ValueError) as e:
            print(f"  Technical agent parsing error: {e}")
            print(f"Response preview: {response[:500]}")

            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            state['technical'] = {
                'timestamp': timestamp,
                'recommendation_signal': 'HOLD',
                'confidence': {
                    'analysis_confidence': 0.5,
                    'setup_quality': 0.0,
                    'interpretation': f'Analysis error: {str(e)[:50]}'
                },
                'market_condition': 'QUIET',
                'summary': f'Analysis error: {str(e)[:100]}',
                'thinking': [],
                'analysis': {},
                'trade_setup': {},
                'action_plan': {},
                'watch_list': {},
                'invalidation': [],
                'confidence_reasoning': {},
            }

            try:
                with DataManager() as dm:
                    dm.save_technical_analysis(data=state['technical'])
            except Exception as save_err:
                print(f"⚠️  Failed to save fallback: {save_err}")

        return state


if __name__ == "__main__":
    agent = TechnicalAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== TECHNICAL AGENT OUTPUT =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
