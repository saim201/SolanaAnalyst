
# Technical Analysis Agent - Swing Trading (1-5 day holds)
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager


SYSTEM_PROMPT = """You are a veteran swing trader analyzing SOLANA (SOL/USDT) cryptocurrency with 15 years of experience trading cryptocurrencies, specializing in 1-5 day holds. You worked as a quantitative analyst at Renaissance Technologies focusing on mean-reversion and momentum strategies.

Your trading philosophy:
- Risk management is paramount: Never risk >2% per trade
- Volume confirms everything: Low volume signals are FALSE signals
- Multiple timeframe confluence: Daily trend + 4h momentum confirmation
- Contrarian at extremes: Sell greed, buy fear
- Support must be within 5% for valid swing trades

CRITICAL: You are analyzing SOLANA (SOL) - a high-volatility L1 blockchain cryptocurrency.
Your analysis style is data-driven, skeptical of hype, and always considers "what could go wrong."
"""


TECHNICAL_PROMPT = """
MARKET STATE:
Current Price: ${current_price:.2f}
24h Change: {change_24h:+.2f}%
24h High: ${high_24h:.2f}
24h Low: ${low_24h:.2f}
24h Range Position: {range_position_24h:.1%}

PRICE ACTION (Last 14 Days):
{daily_ohlc}

4H INTRADAY MOMENTUM (Last 48h):
{intraday_4h}

VOLUME PROGRESSION (Last 14 Days):
{volume_progression}

CANDLE PATTERNS DETECTED:
{candle_patterns}

RAW INDICATORS (You must interpret these yourself):

TREND INDICATORS:
- EMA20: ${ema20:.2f}
- EMA50: ${ema50:.2f}
- EMA200: ${ema200:.2f}
- Kijun-Sen (26d base): ${kijun_sen:.2f}
- 14d High: ${high_14d:.2f}
- 14d Low: ${low_14d:.2f}

MOMENTUM INDICATORS:
- RSI(14): {rsi14:.1f}
- RSI Divergence: {rsi_divergence_type} (strength: {rsi_divergence_strength:.2f})
- Stochastic RSI: {stoch_rsi:.2f}
- MACD Line: {macd_line:.4f}
- MACD Signal: {macd_signal:.4f}
- MACD Histogram: {macd_histogram:.4f}

VOLUME ANALYSIS (CRITICAL):
- Volume Ratio (current/MA20): {volume_ratio:.2f}x
- Volume Classification: {volume_classification}
- Trading Allowed: {volume_trading_allowed}
- Confidence Multiplier: {volume_confidence_multiplier:.0%}
- Days Since Volume Spike (>1.5x): {days_since_volume_spike}d
- 24h Volume Surge: {volume_surge_24h:.2f}x

VOLATILITY:
- ATR (14d): ${atr:.2f}
- ATR % of Price: {atr_percent:.2f}%
- Bollinger Upper: ${bb_upper:.2f}
- Bollinger Lower: ${bb_lower:.2f}

SUPPORT/RESISTANCE:
- Support 1: ${support1:.2f} ({support1_percent:.2f}% below)
- Support 2: ${support2:.2f} ({support2_percent:.2f}% below)
- Resistance 1: ${resistance1:.2f} ({resistance1_percent:.2f}% above)
- Resistance 2: ${resistance2:.2f} ({resistance2_percent:.2f}% above)

KEY LEVELS:
- Weekly Pivot: ${pivot_weekly:.2f}
- Fibonacci 38.2%: ${fib_382:.2f}
- Fibonacci 61.8%: ${fib_618:.2f}

<analysis_framework>
You MUST analyse in this EXACT order:

<thinking>
STEP 1: TREND IDENTIFICATION
- Calculate EMA relationships: Where is price vs EMA20/50/200?
- Is price above/below Kijun-Sen? (equilibrium indicator)
- Compare current price to 14d high/low - are we at extremes?
- What's the trend structure? (strong/weak/range-bound)
- Document your reasoning: [Write 2-3 sentences]

STEP 2: MOMENTUM ASSESSMENT
- Interpret RSI level: oversold (<30), neutral (30-70), overbought (>70)?
- Check Stochastic RSI for more sensitive signals
- MACD: Is histogram positive/negative? Expanding/contracting?
- RSI Divergence: Any reversal warnings?
- Are momentum indicators confirming or contradicting trend?
- Document your reasoning: [Write 2-3 sentences]

STEP 3: VOLUME VALIDATION (CRITICAL - MOST IMPORTANT STEP)
- Analyze volume ratio: Is it STRONG (>1.4x), ACCEPTABLE (1.0-1.4x), WEAK (0.7-1.0x), or DEAD (<0.7x)?
- Check volume_trading_allowed: Can we trade this signal?
- Days since volume spike: Is interest fading? (>14d = concern)
- Apply confidence_multiplier to your final confidence
- Document your reasoning: [Write 2-3 sentences]

STEP 4: RISK/REWARD SETUP
- Calculate distance to nearest support (for stop loss)
- Calculate distance to nearest resistance (for target)
- Compute R:R ratio: Is it at least 1.5:1? (REQUIRED for swing trades)
- Check ATR % - is volatility acceptable? (1-3% ideal for swings)
- Can we get stopped out by normal noise?
- Document your reasoning: [Write 2-3 sentences]

STEP 5: CONFLICTING SIGNALS CHECK
- List ANY contradicting indicators
- What's the bear case if considering BUY?
- What's the bull case if considering SELL?
- Check Bollinger Bands - are we at extremes?
- What could invalidate this trade in 24-48 hours?
- Document your reasoning: [Write 2-3 sentences]

STEP 6: FINAL DECISION
- Given ALL analysis above, what's your recommendation?
- Calculate confidence (0.0 to 1.0)
- Apply volume confidence_multiplier to reduce confidence if needed
- If HOLD, explain why no trade beats forced trade
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
  "timeframe": "1-5 days",
  "key_signals": [
    "price 5.2% above EMA20 (bullish structure)",
    "MACD histogram positive and expanding",
    "volume WEAK at 0.85x - reduces confidence to 0.64"
  ],
  "entry_level": 185.50,
  "stop_loss": 178.00,
  "take_profit": 198.00,
  "reasoning": "Strong technical setup with bullish MACD and price above all EMAs. However, WEAK volume (0.85x) significantly reduces conviction. Risk/reward at 1.8:1 is acceptable. Entry at current level with stop at S1 support. Target R1 resistance."
}}
</answer>
</analysis_framework>

CRITICAL RULES (OVERRIDE EVERYTHING):
1. If volume_trading_allowed is False (DEAD volume <0.7x), you MUST recommend HOLD
2. If no clear support within 5% below entry, you MUST recommend HOLD
3. If risk/reward ratio < 1.5, you MUST recommend HOLD
4. Apply volume_confidence_multiplier to your final confidence score
5. Never recommend entry without calculating exact stop_loss and take_profit
6. If recommending HOLD, set entry_level, stop_loss, take_profit to null
"""




class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.3
        )

    @staticmethod
    def detect_candle_pattern(candle: dict) -> str:
        open_p = candle['open']
        close_p = candle['close']
        high_p = candle['high']
        low_p = candle['low']

        body = abs(close_p - open_p)
        range_total = high_p - low_p

        if range_total == 0:
            return "NONE"

        body_ratio = body / range_total

        # Doji: small body (<10% of range)
        if body_ratio < 0.1:
            return "DOJI"

        # Hammer/Inverted Hammer: small body, long wick
        upper_wick = high_p - max(open_p, close_p)
        lower_wick = min(open_p, close_p) - low_p

        if lower_wick > body * 2 and upper_wick < body:
            return "HAMMER" if close_p > open_p else "HANGING_MAN"

        if upper_wick > body * 2 and lower_wick < body:
            return "INVERTED_HAMMER" if close_p > open_p else "SHOOTING_STAR"

        # Engulfing
        # Would need previous candle for this

        return "NONE"

    @staticmethod
    def format_daily_ohlc(candles: list) -> str:
        # Format last 14 days of OHLC data with volume and buying pressure
        if not candles or len(candles) == 0:
            return "No data available"

        lines = []
        for candle in candles[-14:]:
            date = candle.get('open_time', 'N/A')
            o = candle.get('open', 0)
            h = candle.get('high', 0)
            l = candle.get('low', 0)
            c = candle.get('close', 0)
            volume = candle.get('volume', 0)
            num_trades = candle.get('num_trades', 0)
            taker_buy_base = candle.get('taker_buy_base', 0)

            change = ((c - o) / o * 100) if o > 0 else 0

            # Cal bying pressure
            buy_ratio = (taker_buy_base / volume * 100) if volume > 0 else 50.0

            # Classify volume intensity by num_trades (smart money indicator)
            trade_intensity = "inst" if (volume > 5000 and num_trades < 8000) else "retail"

            lines.append(
                f"  {date}: O=${o:.2f} H=${h:.2f} L=${l:.2f} C=${c:.2f} ({change:+.1f}%) | "
                f"Vol={volume:,.0f} Trades={num_trades:,} BuyPressure={buy_ratio:.1f}% [{trade_intensity}]"
            )

        return "\n".join(lines)



    @staticmethod
    def format_4h_candles(candles: list) -> str:
        if not candles or len(candles) == 0:
            return "No data available"

        lines = []
        for candle in candles[-12:]:
            time = candle.get('open_time', 'N/A')
            c = candle.get('close', 0)
            change = ((candle.get('close', 0) - candle.get('open', 0)) / candle.get('open', 1) * 100)
            pattern = TechnicalAgent.detect_candle_pattern(candle)

            pattern_str = f" [{pattern}]" if pattern != "NONE" else ""
            lines.append(f"  {time}: ${c:.2f} ({change:+.1f}%){pattern_str}")

        return "\n".join(lines)



    @staticmethod
    def format_volume_progression(candles: list) -> str:
        # Show volume trend and buying pressure over last 14 days
        if not candles or len(candles) < 14:
            return "Insufficient data"

        recent = candles[-14:]
        volumes = [c.get('volume', 0) for c in recent]
        avg_volume = sum(volumes) / len(volumes)

        # volume trend
        first_half_avg = sum(volumes[:7]) / 7
        second_half_avg = sum(volumes[7:]) / 7
        volume_trend = "INCREASING" if second_half_avg > first_half_avg * 1.1 else "DECREASING" if second_half_avg < first_half_avg * 0.9 else "STABLE"

        # Calculate buying pressure trend (first 7d vs last 7d)
        first_half_buy_pressure = []
        second_half_buy_pressure = []

        for i, candle in enumerate(recent):
            volume = candle.get('volume', 0)
            taker_buy = candle.get('taker_buy_base', 0)
            buy_ratio = (taker_buy / volume * 100) if volume > 0 else 50.0

            if i < 7:
                first_half_buy_pressure.append(buy_ratio)
            else:
                second_half_buy_pressure.append(buy_ratio)

        avg_buy_pressure_first = sum(first_half_buy_pressure) / len(first_half_buy_pressure) if first_half_buy_pressure else 50.0
        avg_buy_pressure_second = sum(second_half_buy_pressure) / len(second_half_buy_pressure) if second_half_buy_pressure else 50.0

        buy_pressure_trend = "STRENGTHENING" if avg_buy_pressure_second > avg_buy_pressure_first + 3 else "WEAKENING" if avg_buy_pressure_second < avg_buy_pressure_first - 3 else "STABLE"

        # Current buying pressure
        latest_candle = recent[-1]
        latest_volume = latest_candle.get('volume', 0)
        latest_taker_buy = latest_candle.get('taker_buy_base', 0)
        latest_buy_pressure = (latest_taker_buy / latest_volume * 100) if latest_volume > 0 else 50.0

        return (
            f"  Volume Trend: {volume_trend}\n"
            f"  14d Avg Volume: {avg_volume:,.0f}\n"
            f"  Recent 7d Avg: {second_half_avg:,.0f} ({((second_half_avg/first_half_avg - 1) * 100):+.1f}% vs prior 7d)\n"
            f"  \n"
            f"  Buying Pressure Trend: {buy_pressure_trend}\n"
            f"  First 7d Avg Buy Pressure: {avg_buy_pressure_first:.1f}%\n"
            f"  Recent 7d Avg Buy Pressure: {avg_buy_pressure_second:.1f}%\n"
            f"  Latest Buy Pressure: {latest_buy_pressure:.1f}% (>50% = buyers aggressive)"
        )



    @staticmethod
    def detect_patterns_at_levels(candles: list, support: float, resistance: float) -> str:
        # Detect patterns forming at key support/resistance levels
        if not candles or len(candles) < 2:
            return "Insufficient data"

        patterns = []
        recent = candles[-5:]  # Last 5 candles

        for i, candle in enumerate(recent):
            low = candle.get('low', 0)
            high = candle.get('high', 0)
            close = candle.get('close', 0)

            # Check if testing support
            if support and abs(low - support) / support < 0.02:  # Within 2%
                pattern = TechnicalAgent.detect_candle_pattern(candle)
                if pattern != "NONE":
                    patterns.append(f"  {pattern} at support ${support:.2f}")

            # Check if testing resistance
            if resistance and abs(high - resistance) / resistance < 0.02:  # Within 2%
                pattern = TechnicalAgent.detect_candle_pattern(candle)
                if pattern != "NONE":
                    patterns.append(f"  {pattern} at resistance ${resistance:.2f}")

        return "\n".join(patterns) if patterns else "  No significant patterns at key levels"



    def execute(self, state: AgentState) -> AgentState:
        dq = DataQuery()

        ticker = dq.get_ticker_data()
        if not ticker:
            raise ValueError("No ticker data available")

        indicators_data = dq.get_indicators_data()
        if not indicators_data:
            raise ValueError("No indicators data available")

        # Get price action data for context
        daily_candles = dq.get_candlestick_data(days=14)  # Last 14 days
        intraday_4h = dq.get_intraday_candles(limit=12)  # Last 48h of 4h candles

        current_price = float(ticker.get('lastPrice', 0))
        change_24h = float(ticker.get('priceChangePercent', 0))
        high_24h = float(ticker.get('highPrice', 0))
        low_24h = float(ticker.get('lowPrice', 0))

        # 24h range position
        range_24h = high_24h - low_24h
        if range_24h > 0:
            range_position_24h = (current_price - low_24h) / range_24h
        else:
            range_position_24h = 0.5

        # Extract all raw indicators
        ema20 = float(indicators_data.get('ema20', 0))
        ema50 = float(indicators_data.get('ema50', 0))
        ema200 = float(indicators_data.get('ema200', 0))
        kijun_sen = float(indicators_data.get('kijun_sen', 0))
        high_14d = float(indicators_data.get('high_14d', 0))
        low_14d = float(indicators_data.get('low_14d', 0))

        rsi14 = float(indicators_data.get('rsi14', 50))
        rsi_divergence_type = indicators_data.get('rsi_divergence_type', 'NONE')
        rsi_divergence_strength = float(indicators_data.get('rsi_divergence_strength', 0))
        stoch_rsi = float(indicators_data.get('stoch_rsi', 0.5))

        macd_line = float(indicators_data.get('macd_line', 0))
        macd_signal = float(indicators_data.get('macd_signal', 0))
        macd_histogram = float(indicators_data.get('macd_histogram', 0))

        volume_ratio = float(indicators_data.get('volume_ratio', 1.0))
        volume_classification = indicators_data.get('volume_classification', 'ACCEPTABLE')
        volume_trading_allowed = indicators_data.get('volume_trading_allowed', True)
        volume_confidence_multiplier = float(indicators_data.get('volume_confidence_multiplier', 1.0))
        days_since_volume_spike = int(indicators_data.get('days_since_volume_spike', 999))

        # Calculate volume surge from ticker
        volume_24h = float(ticker.get('volume', 0))
        volume_ma20 = float(indicators_data.get('volume_ma20', 1))
        volume_surge_24h = volume_24h / volume_ma20 if volume_ma20 > 0 else 1.0

        atr = float(indicators_data.get('atr', 0))
        atr_percent = float(indicators_data.get('atr_percent', 0))
        bb_upper = float(indicators_data.get('bb_upper', 0))
        bb_lower = float(indicators_data.get('bb_lower', 0))

        support1 = float(indicators_data.get('support1') or 0)
        support1_percent = float(indicators_data.get('support1_percent') or 0)
        support2 = float(indicators_data.get('support2') or 0)
        support2_percent = float(indicators_data.get('support2_percent') or 0)

        resistance1 = float(indicators_data.get('resistance1') or 0)
        resistance1_percent = float(indicators_data.get('resistance1_percent') or 0)
        resistance2 = float(indicators_data.get('resistance2') or 0)
        resistance2_percent = float(indicators_data.get('resistance2_percent') or 0)

        pivot_weekly = float(indicators_data.get('pivot_weekly') or 0)
        fib_382 = float(indicators_data.get('fib_level_382', 0))
        fib_618 = float(indicators_data.get('fib_level_618', 0))

        # Format price action data
        daily_ohlc_text = self.format_daily_ohlc(daily_candles)
        intraday_4h_text = self.format_4h_candles(intraday_4h)
        volume_progression_text = self.format_volume_progression(daily_candles)
        candle_patterns_text = self.detect_patterns_at_levels(
            daily_candles,
            support1 if support1 > 0 else None,
            resistance1 if resistance1 > 0 else None
        )

        full_prompt = SYSTEM_PROMPT + "\n\n" + TECHNICAL_PROMPT.format(
            current_price=current_price,
            change_24h=change_24h,
            high_24h=high_24h,
            low_24h=low_24h,
            range_position_24h=range_position_24h,
            daily_ohlc=daily_ohlc_text,
            intraday_4h=intraday_4h_text,
            volume_progression=volume_progression_text,
            candle_patterns=candle_patterns_text,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            kijun_sen=kijun_sen,
            high_14d=high_14d,
            low_14d=low_14d,
            rsi14=rsi14,
            rsi_divergence_type=rsi_divergence_type,
            rsi_divergence_strength=rsi_divergence_strength,
            stoch_rsi=stoch_rsi,
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            volume_ratio=volume_ratio,
            volume_classification=volume_classification,
            volume_trading_allowed=volume_trading_allowed,
            volume_confidence_multiplier=volume_confidence_multiplier,
            days_since_volume_spike=days_since_volume_spike,
            volume_surge_24h=volume_surge_24h,
            atr=atr,
            atr_percent=atr_percent,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            support1=support1,
            support1_percent=support1_percent,
            support2=support2,
            support2_percent=support2_percent,
            resistance1=resistance1,
            resistance1_percent=resistance1_percent,
            resistance2=resistance2,
            resistance2_percent=resistance2_percent,
            pivot_weekly=pivot_weekly,
            fib_382=fib_382,
            fib_618=fib_618,
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
                answer_json = response

            answer_json = re.sub(r'```json\s*|\s*```', '', answer_json).strip()
            analysis = json.loads(answer_json)

            state['technical'] = {
                'recommendation': analysis.get('recommendation', 'HOLD'),
                'confidence': float(analysis.get('confidence', 0.5)),
                'timeframe': analysis.get('timeframe', '1-7 days'),
                'key_signals': analysis.get('key_signals', []),
                'entry_level': analysis.get('entry_level'),
                'stop_loss': analysis.get('stop_loss'),
                'take_profit': analysis.get('take_profit'),
                'reasoning': analysis.get('reasoning', ''),
                'confidence_breakdown': analysis.get('confidence_breakdown', []),  # Fixed: [] not {}
                'thinking': thinking if thinking else ''
            }

            dm = DataManager()
            dm.save_technical_analysis(data=state['technical'])


        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Technical agent parsing error: {e}")
            print(f"Response: {response[:300]}")

            state['technical'] = {
                'recommendation': 'HOLD',
                'confidence': 0.0,
                'reasoning': f"Analysis parsing error: {str(e)[:100]}",
                'key_signals': [],
                'entry_level': None,
                'stop_loss': None,
                'take_profit': None,
                'timeframe': 'N/A',
                'confidence_breakdown': [],  # Fixed: Added missing field
                'thinking': ''  # Fixed: Added missing field
            }

        return state


if __name__ == "__main__":
    agent = TechnicalAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== TECHNICAL AGENT OUTPUT =====")
    print(f"\n {result}")
