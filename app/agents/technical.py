# technical.py - optimised for Sonnet 4.5

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from anthropic import Anthropic

from app.agents.base import BaseAgent, AgentState
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager


TECHNICAL_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation_signal": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD", "WAIT"],
            "description": "Primary trading recommendation"
        },
        "confidence": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": "Confidence level from 0.0 to 1.0"
                },
                "reasoning": {
                    "type": "string",
                    "description": "2-3 sentences explaining confidence with specific data points"
                }
            },
            "required": ["score", "reasoning"],
            "additionalProperties": False
        },
        "market_condition": {
            "type": "string",
            "enum": ["TRENDING", "RANGING", "VOLATILE", "QUIET"],
            "description": "Overall market state"
        },
        "thinking": {
            "type": "string",
            "description": "Detailed chain-of-thought reasoning process"
        },
        "analysis": {
            "type": "object",
            "properties": {
                "trend": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["BULLISH", "BEARISH", "NEUTRAL"]
                        },
                        "strength": {
                            "type": "string",
                            "enum": ["STRONG", "MODERATE", "WEAK"]
                        },
                        "detail": {
                            "type": "string",
                            "description": "2-3 sentences with specific indicator values"
                        }
                    },
                    "required": ["direction", "strength", "detail"],
                    "additionalProperties": False
                },
                "momentum": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["BULLISH", "BEARISH", "NEUTRAL"]
                        },
                        "strength": {
                            "type": "string",
                            "enum": ["STRONG", "MODERATE", "WEAK"]
                        },
                        "detail": {
                            "type": "string",
                            "description": "2-3 sentences with specific indicator values"
                        }
                    },
                    "required": ["direction", "strength", "detail"],
                    "additionalProperties": False
                },
                "volume": {
                    "type": "object",
                    "properties": {
                        "quality": {
                            "type": "string",
                            "enum": ["STRONG", "ACCEPTABLE", "WEAK", "DEAD"]
                        },
                        "ratio": {
                            "type": "number",
                            "description": "Volume ratio vs average"
                        },
                        "detail": {
                            "type": "string",
                            "description": "2-3 sentences with specific values"
                        }
                    },
                    "required": ["quality", "ratio", "detail"],
                    "additionalProperties": False
                }
            },
            "required": ["trend", "momentum", "volume"],
            "additionalProperties": False
        },
        "trade_setup": {
            "type": "object",
            "properties": {
                "viability": {
                    "type": "string",
                    "enum": ["VALID", "WAIT", "INVALID"]
                },
                "entry": {
                    "type": "number",
                    "description": "Entry price level"
                },
                "stop_loss": {
                    "type": "number",
                    "description": "Stop loss price level"
                },
                "take_profit": {
                    "type": "number",
                    "description": "Take profit target"
                },
                "risk_reward": {
                    "type": "number",
                    "description": "Risk to reward ratio"
                },
                "support": {
                    "type": "number",
                    "description": "Key support level"
                },
                "resistance": {
                    "type": "number",
                    "description": "Key resistance level"
                },
                "current_price": {
                    "type": "number",
                    "description": "Current market price"
                },
                "timeframe": {
                    "type": "string",
                    "description": "Expected trade duration"
                }
            },
            "required": ["viability", "entry", "stop_loss", "take_profit",
                        "risk_reward", "support", "resistance", "current_price", "timeframe"],
            "additionalProperties": False
        },
        "action_plan": {
            "type": "object",
            "properties": {
                "for_buyers": {
                    "type": "string",
                    "description": "Guidance for buyers"
                },
                "for_sellers": {
                    "type": "string",
                    "description": "Guidance for sellers"
                },
                "if_holding": {
                    "type": "string",
                    "description": "Guidance for current holders"
                },
                "avoid": {
                    "type": "string",
                    "description": "What NOT to do"
                }
            },
            "required": ["for_buyers", "for_sellers", "if_holding", "avoid"],
            "additionalProperties": False
        },
        "watch_list": {
            "type": "object",
            "properties": {
                "bullish_signals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Conditions that would make setup bullish"
                },
                "bearish_signals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Conditions that would invalidate setup"
                }
            },
            "required": ["bullish_signals", "bearish_signals"],
            "additionalProperties": False
        },
        "invalidation": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Conditions that kill the thesis"
        },
        "confidence_reasoning": {
            "type": "object",
            "properties": {
                "supporting": {
                    "type": "string",
                    "description": "2-5 sentences on what supports the recommendation"
                },
                "concerns": {
                    "type": "string",
                    "description": "2-5 sentences on what could go wrong"
                }
            },
            "required": ["supporting", "concerns"],
            "additionalProperties": False
        }
    },
    "required": [
        "recommendation_signal",
        "confidence",
        "market_condition",
        "thinking",
        "analysis",
        "trade_setup",
        "action_plan",
        "watch_list",
        "invalidation",
        "confidence_reasoning"
    ],
    "additionalProperties": False
}


SYSTEM_PROMPT = """You are a veteran swing trader analysing SOLANA (SOL/USDT) with 15 years of experience.

TRADING PHILOSOPHY:
- Risk management is paramount
- Volume confirms everything - low volume moves are suspect
- Trade with the trend, not against it
- Patience pays - no trade is better than a bad trade
- Be honest about uncertainty

ANALYSIS STYLE:
- Tell the story of what's happening with specific data
- Think like a detective - what are buyers/sellers doing?
- Always explain the "why" behind moves
- Forward-looking - what happens next?

SOLANA CONTEXT:
- High-volatility L1 blockchain cryptocurrency
- Typical 15-30% pullbacks even in strong uptrends are normal
- Usually 0.75-0.90 correlation with BTC

Your confidence.reasoning must paint a clear picture with specific data, not just list facts."""


TECHNICAL_PROMPT = """
<market_data>
## CURRENT STATE
Analysis Time: {analysis_timestamp}
Price: ${current_price:.2f} | 24h: {change_24h:+.2f}%
24h Range: ${low_24h:.2f} - ${high_24h:.2f} (at {range_position_24h:.0%})

## INDICATORS

TREND:
- EMA20: ${ema20:.2f} ({ema20_distance:+.1f}%)
- EMA50: ${ema50:.2f} ({ema50_distance:+.1f}%)
- 14d High: ${high_14d:.2f} | Low: ${low_14d:.2f}
- Position in 14d Range: {price_position_14d:.0%}

MOMENTUM:
- RSI(14): {rsi14:.1f}
- MACD: line={macd_line:.4f}, signal={macd_signal:.4f}, hist={macd_histogram:.4f}
- Divergence: {rsi_divergence_type} (strength: {rsi_divergence_strength:.2f})

VOLUME (CRITICAL):
- Volume Ratio: {volume_ratio:.2f}x average
- Classification: {volume_classification}
- Buy Pressure (7d weighted): {weighted_buy_pressure:.1f}%
- Days Since Spike (>1.5x): {days_since_volume_spike}

KEY LEVELS:
- Support: ${support1:.2f} ({support1_distance:.1f}% below), ${support2:.2f} ({support2_distance:.1f}% below)
- Resistance: ${resistance1:.2f} ({resistance1_distance:.1f}% above), ${resistance2:.2f} ({resistance2_distance:.1f}% above)

VOLATILITY:
- ATR(14): ${atr:.2f} ({atr_percent:.1f}% of price)
- Bollinger Squeeze: {bb_squeeze_active} (ratio: {bb_squeeze_ratio:.1f}%)

BTC CORRELATION:
- 30d Correlation: {sol_btc_correlation:.2f}
- BTC Trend: {btc_trend}
- BTC 30d Change: {btc_price_change_30d:+.1f}%

## RECENT PRICE ACTION (Last 7 Days)
{recent_price_action}
</market_data>

<instructions>
Analyse this market data using chain-of-thought reasoning.

First, write your detailed reasoning inside <thinking> tags.
Then, output your final analysis as valid JSON inside <answer> tags.

Consider deeply: trend direction/strength, volume quality and conviction, momentum direction, BTC correlation impact, risk/reward setup, and invalidation conditions.

CRITICAL RULES:
- If volume_ratio < 0.7: recommend HOLD or WAIT
- If no support within 5% below: HOLD or WAIT
- If risk/reward < 1.5:1: HOLD or WAIT
- Always provide specific price levels
- Be thorough and reference specific data points (prices, ratios, RSI values, support/resistance levels)

CONFIDENCE GUIDELINES:
Score (0.0-1.0):
- 0.80-1.00: Very high confidence
- 0.65-0.79: High confidence
- 0.50-0.64: Moderate confidence
- 0.35-0.49: Low confidence
- 0.00-0.34: Very low confidence

Reasoning (2-3 sentences): Explain why using specific data. Tell the story of what's happening.

Output the JSON structure matching the provided schema exactly.
</instructions>
"""


def calculate_distance_percent(current: float, level: float) -> float:
    if current == 0:
        return 0.0
    return ((level - current) / current) * 100


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
        candle_type = "BULLISH" if c >= o else "BEARISH"

        lines.append(
            f"{formatted_date}: {candle_type} | "
            f"O: ${o:.2f} → C: ${c:.2f} ({change:+.1f}%) | "
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
            model="claude-sonnet-4-5-20250929",
            temperature=0.3
        )
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def execute(self, state: AgentState) -> AgentState:
        with DataQuery() as dq:
            ticker = dq.get_ticker_data()
            if not ticker:
                raise ValueError("No ticker data available")

            indicators_data = dq.get_indicators_data()
            if not indicators_data:
                raise ValueError("No indicators data available")

            daily_candles = dq.get_candlestick_data(days=14)

        # Extract current market state
        current_price = float(ticker.get('lastPrice', 0))
        change_24h = float(ticker.get('priceChangePercent', 0))
        high_24h = float(ticker.get('highPrice', 0))
        low_24h = float(ticker.get('lowPrice', 0))

        range_24h = high_24h - low_24h
        range_position_24h = (current_price - low_24h) / range_24h if range_24h > 0 else 0.5

        # Extract indicators
        ema20 = float(indicators_data.get('ema20', 0))
        ema50 = float(indicators_data.get('ema50', 0))
        high_14d = float(indicators_data.get('high_14d', 0))
        low_14d = float(indicators_data.get('low_14d', 0))

        rsi14 = float(indicators_data.get('rsi14', 50))
        macd_line = float(indicators_data.get('macd_line', 0))
        macd_signal = float(indicators_data.get('macd_signal', 0))
        macd_histogram = float(indicators_data.get('macd_histogram', 0))
        rsi_divergence_type = indicators_data.get('rsi_divergence_type', 'NONE')
        rsi_divergence_strength = float(indicators_data.get('rsi_divergence_strength', 0))

        volume_ratio = float(indicators_data.get('volume_ratio', 1.0))
        volume_classification = indicators_data.get('volume_classification', 'ACCEPTABLE')
        weighted_buy_pressure = float(indicators_data.get('weighted_buy_pressure', 50.0))
        days_since_volume_spike = int(indicators_data.get('days_since_volume_spike', 999))

        support1 = float(indicators_data.get('support1') or current_price * 0.95)
        support2 = float(indicators_data.get('support2') or current_price * 0.90)
        resistance1 = float(indicators_data.get('resistance1') or current_price * 1.05)
        resistance2 = float(indicators_data.get('resistance2') or current_price * 1.10)

        atr = float(indicators_data.get('atr', 0))
        atr_percent = float(indicators_data.get('atr_percent', 0))
        bb_squeeze_ratio = float(indicators_data.get('bb_squeeze_ratio', 0))
        bb_squeeze_active = indicators_data.get('bb_squeeze_active', False)

        sol_btc_correlation = float(indicators_data.get('sol_btc_correlation', 0.8))
        btc_trend = indicators_data.get('btc_trend', 'NEUTRAL')
        btc_price_change_30d = float(indicators_data.get('btc_price_change_30d', 0))

        # Calculate distances
        ema20_distance = calculate_distance_percent(current_price, ema20)
        ema50_distance = calculate_distance_percent(current_price, ema50)
        support1_distance = abs(calculate_distance_percent(current_price, support1))
        support2_distance = abs(calculate_distance_percent(current_price, support2))
        resistance1_distance = calculate_distance_percent(current_price, resistance1)
        resistance2_distance = calculate_distance_percent(current_price, resistance2)
        price_position_14d = calculate_price_position_in_range(current_price, high_14d, low_14d)

        recent_price_action = format_recent_price_action(daily_candles, limit=7)
        analysis_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

        # Build prompt
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
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            rsi_divergence_type=rsi_divergence_type,
            rsi_divergence_strength=rsi_divergence_strength,
            volume_ratio=volume_ratio,
            volume_classification=volume_classification,
            weighted_buy_pressure=weighted_buy_pressure,
            days_since_volume_spike=days_since_volume_spike,
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
            bb_squeeze_active=bb_squeeze_active,
            bb_squeeze_ratio=bb_squeeze_ratio,
            sol_btc_correlation=sol_btc_correlation,
            btc_trend=btc_trend,
            btc_price_change_30d=btc_price_change_30d,
            recent_price_action=recent_price_action,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            messages=[{"role": "user", "content": full_prompt}],
            extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
            extra_body={
                "output_format": {
                    "type": "json_schema",
                    "schema": TECHNICAL_ANALYSIS_SCHEMA
                }
            }
        )

        response_text = response.content[0].text

        answer_match = re.search(r'<answer>(.*?)</answer>', response_text, re.DOTALL)
        if answer_match:
            json_text = answer_match.group(1).strip()
        else:
            # Fallback: structured outputs might return pure JSON without tags
            json_text = response_text

        json_text = re.sub(r'^```json\s*|\s*```$', '', json_text.strip())

        analysis = json.loads(json_text)

        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        analysis['timestamp'] = timestamp

        state['technical'] = analysis

        with DataManager() as dm:
            dm.save_technical_analysis(data=state['technical'])

        return state


if __name__ == "__main__":
    agent = TechnicalAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== TECHNICAL AGENT OUTPUT =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
