
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager


SYSTEM_PROMPT = """You are a veteran swing trader analysing SOLANA (SOL/USDT) cryptocurrency with 15 years of experience in crypto markets, specialising in 1-5 day holds. You worked as a quantitative analyst at Renaissance Technologies focusing on mean-reversion and momentum strategies.

Your trading philosophy:
- Risk management is paramount: Never risk >2% per trade
- Volume confirms everything: Low volume signals are FALSE signals
- Multiple timeframe confluence: Daily trend + 4h momentum confirmation
- Contrarian at extremes: Sell greed, buy fear
- Support must be within 5% for valid swing trades

CRITICAL: You are analysing SOLANA (SOL) - a high-volatility L1 blockchain cryptocurrency.

Your analysis style is:
- Tell the STORY of what's happening in the market (not just data points)
- Think like a detective: What are buyers/sellers doing? Who's winning?
- Always explain the "why" behind moves, not just the "what"
- Forward-looking: What happens next? What are we watching for?
- Honest about uncertainty: When you don't know, you say so
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
YOUR RESPONSE MUST USE THIS EXACT FORMAT:


<thinking>
PHASE 1: THE MARKET CONTEXT - "Where are we in the story?"
First, paint the big picture. Don't just list indicators—explain what they mean together:
- What's the dominant trend? (Are we in a bull run, bear market, or choppy range?)
- Where in the trend are we? (Early breakout, extended move, exhaustion, reversal?)
- Is price at a critical juncture? (Testing support/resistance, breaking out, coiling?)
- What's the overall market structure telling you? (Clean trends, messy chop, compression before expansion?)
Write 3-4 sentences describing the STORY of what's happening in SOL right now.
Example: "SOL is in a strong uptrend, grinding higher above all major EMAs. However, we're now testing resistance at $195 for the third time in 5 days, suggesting sellers are defending this level. The trend is intact but momentum is fading—RSI rolling over from overbought and MACD histogram compressing. This feels like a market taking a breather after a strong run."



PHASE 2: THE VOLUME STORY - "What are traders actually doing?"
Volume is the truth serum of markets. Describe what you see:
- Is volume confirming or contradicting price action?
- What's the buying pressure trend? (Are buyers getting more/less aggressive?)
- Any institutional vs retail patterns? (High volume, low trades = smart money)
- Volume trend over last 7-14 days? (Building, fading, explosive, dead?)
Critical: If volume is WEAK (<0.7x) or DEAD, this invalidates ALL other signals. State this clearly.
Write 2-3 sentences explaining what volume is telling you about conviction.
Example: "Volume is concerning. We're up 8% in the last 3 days but volume has DECREASED by 20%—classic divergence. Buying pressure dropped from 58% to 47%, meaning sellers are becoming more aggressive on rallies. This rally lacks conviction and is vulnerable to reversal."



PHASE 3: MOMENTUM & SENTIMENT - "What's the energy of this move?"
Connect momentum indicators to market psychology:
- RSI: Are we overbought/oversold? But more importantly—is momentum confirming trend?
- MACD: Is momentum accelerating or decelerating? Histogram expanding or compressing?
- Stoch RSI: Are we at extremes? Ready to turn?
- Any divergences? (Price making new highs but RSI not = bearish divergence)
Explain what these indicators reveal about trader sentiment and where we are in the cycle.
Write 2-3 sentences about momentum and what it means for the next move.
Example: "Momentum is mixed. RSI at 65 shows bulls still in control but not euphoric—there's room to run. However, MACD histogram is compressing (shrinking from 0.45 to 0.28), suggesting the upward momentum is slowing. We're not seeing capitulation yet, but we're not seeing acceleration either—this is a consolidation pattern forming."



PHASE 4: THE SETUP - "Is there a tradeable opportunity?"
Now connect everything to a specific trade idea:
- Entry: Where's the optimal entry based on support/value?
- Stop Loss: Where does the trade invalidate? (Must be within 5% and below key support)
- Target: Where's the next resistance/target? 
- Risk/Reward: Calculate the R:R ratio (must be >1.5:1)
- Timeframe: When should this play out? (1-5 days)
Be specific with numbers. If there's NO good setup, explain why waiting is better.
Write 3-4 sentences describing the specific trade setup or why you're passing.
Example: "There's a potential long setup if price pulls back to $182-184 (EMA20 + S1 support). That would offer a 4% stop loss to $176 (below S2) and a 7% upside to $198 (R1 resistance), giving us 1.75:1 R/R. However, at current price of $188, we're in no-man's land—too far from support for a safe stop. Better to wait for the pullback or a breakout above $195 on strong volume."



PHASE 5: RISK ASSESSMENT - "What could go wrong?"
Every trade has risks. Be brutally honest:
- What's the bear case if you're bullish? (Or bull case if bearish?)
- What level invalidates your thesis?
- Any macro/external factors? (BTC correlation, market uncertainty)
- What's your confidence level and why? (Be specific about doubts)
This is where you apply the volume confidence multiplier and acknowledge uncertainty.
Write 2-3 sentences about risks and confidence adjustments.
Example: "Main risk: This rally is on declining volume. If we don't see a volume surge (>1.4x) in the next 24-48 hours, this move is suspect. Also, we're 8% above EMA50—getting extended. My base confidence is 0.75 but WEAK volume (0.82x) reduces this to 0.62. This is a tentative setup, not a high-conviction trade."



PHASE 6: THE WATCH LIST - "What happens next? What are we monitoring?"
Trading is dynamic. Tell the trader what to watch:
- Confirmation signals: What validates your thesis? (Volume spike, breakout, specific level hold)
- Invalidation signals: What proves you wrong? (Break of support, volume dying, specific pattern)
- Key levels to watch in next 24-48 hours
- Time-based triggers: If X doesn't happen by Y time, reassess
This gives the trader a roadmap, not just a static recommendation.
Write 2-3 sentences about forward-looking monitoring.
Example: "Watch for: (1) A volume surge above 1.5x to confirm bulls are serious, (2) Price holding above $184 (EMA20) on any pullback—loss of this level invalidates the bullish case, (3) BTC holding $42k+ as SOL is highly correlated. If we don't see higher volume within 48 hours, exit any longs at breakeven. This setup has a 72-hour window."


</thinking>


<answer>
Provide your trading recommendation in this EXACT JSON format:

{{
  "recommendation": "BUY|SELL|HOLD",
  "confidence": 0.75,
  
  "confidence_breakdown": {{
    "trend_strength": {{"score": 0.8, "reasoning": "Strong uptrend, price above all EMAs"}},
    "momentum_quality": {{"score": 0.7, "reasoning": "Bullish but decelerating, MACD compressing"}},
    "volume_conviction": {{"score": 0.5, "reasoning": "WEAK volume (0.82x) - major red flag"}},
    "risk_reward_setup": {{"score": 0.9, "reasoning": "Excellent 1.8:1 R/R with clear levels"}},
    "final_adjusted": {{"score": 0.62, "reasoning": "Base 0.75 reduced by volume multiplier (0.82)"}}
  }},
  
  "timeframe": "1-5 days",
  
  "key_signals": [
    "Price 5.2% above EMA20 - bullish structure intact",
    "MACD histogram positive but compressing (0.45→0.28) - momentum slowing",
    "Volume WEAK at 0.82x with declining buy pressure (58%→47%) - conviction lacking",
    "Testing R1 resistance at $195 for 3rd time - sellers defending"
  ],
  
  "entry_level": 184.00,
  "stop_loss": 176.50,
  "take_profit": 198.00,
  
  "reasoning": "SOL is in a confirmed uptrend (above all EMAs, MACD positive) but showing signs of exhaustion at resistance. The technical setup is sound with 1.8:1 R/R, but WEAK volume is a significant concern—this rally lacks conviction. Wait for a pullback to $182-184 (EMA20 support) for better entry, or a volume-confirmed breakout above $195. Current price is in no-man's land.",
  
  "recommendation_summary": "WAIT for better entry—don't chase here. Price is extended 8% above EMA50 and testing resistance on WEAK volume (0.82x). If you're not in, be patient: either wait for a pullback to $182-184 (EMA20) for a safer entry with tight stop, OR wait for a volume-confirmed breakout above $195 (needs >1.5x volume surge). If already long, consider taking partial profits and tightening stops to $188. Watch volume closely over next 48 hours—if it stays weak, this rally is vulnerable to sharp reversal. Key invalidation: break below $184 (EMA20).",
  
  "watch_list": {{
    "confirmation_signals": [
      "Volume surge above 1.5x (currently 0.82x) - validates bullish move",
      "Breakout and 4h close above $195 on strong volume",
      "Buying pressure returning above 55% (currently 47%)"
    ],
    "invalidation_signals": [
      "Break and close below $184 (EMA20) - trend break",
      "Volume remains weak (<1.0x) for 48+ hours - no conviction",
      "RSI divergence forms (lower high while price makes higher high)"
    ],
    "key_levels_24_48h": [
      "$195 - Critical resistance, 3rd test, must break with volume",
      "$184 - EMA20 support, must hold on any pullback",
      "$176 - Stop loss / invalidation level (below S1 support)"
    ],
    "time_based_triggers": [
      "48 hours: If volume doesn't improve to >1.2x, exit longs at breakeven",
      "5 days: If still ranging $180-195, reassess - may need longer consolidation"
    ]
  }}
}}
</answer>

CRITICAL OUTPUT FORMAT REQUIREMENTS:
1. Start your response IMMEDIATELY with <thinking> - NO introduction, NO "I understand", NO preamble
2. End with </answer> - NOTHING after it
3. The JSON in <answer> must be valid and complete
4. DO NOT explain the task, DO NOT acknowledge instructions - JUST START WITH <thinking>

</analysis_framework>

CRITICAL RULES (OVERRIDE EVERYTHING):
1. If volume_trading_allowed is False (DEAD volume <0.7x), you MUST recommend HOLD and explain why in recommendation_summary
2. If no clear support within 5% below entry, you MUST recommend HOLD - no trade is better than bad trade
3. If risk/reward ratio < 1.5:1, you MUST recommend HOLD - edge is insufficient
4. Apply volume_confidence_multiplier to your final confidence score and EXPLAIN the reduction
5. Never recommend entry without calculating exact stop_loss and take_profit with reasoning
6. If recommending HOLD, set entry_level, stop_loss, take_profit to null but provide detailed watch_list
7. In recommendation_summary, always include: (a) specific action, (b) key reason, (c) what to watch next, (d) invalidation level
8. confidence_breakdown must include REASONING for each score, not just numbers
9. watch_list is MANDATORY - always provide forward-looking guidance on what to monitor
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
        if not candles:
            return "No data available"

        lines = []
        for candle in candles[-14:]:
            date = candle.get('open_time', 'N/A')
            o = candle.get('open', 0)
            h = candle.get('high', 0)
            l = candle.get('low', 0)
            c = candle.get('close', 0)
            volume = candle.get('volume', 0)
            taker_buy_base = candle.get('taker_buy_base', 0)

            change = ((c - o) / o * 100) if o > 0 else 0
            buy_ratio = (taker_buy_base / volume * 100) if volume > 0 else 50.0

            lines.append(
                f"  {date}: O=${o:.2f} H=${h:.2f} L=${l:.2f} C=${c:.2f} ({change:+.1f}%) | "
                f"Vol={volume:,.0f} BuyPressure={buy_ratio:.1f}%"
            )

        return "\n".join(lines)



    @staticmethod
    def format_4h_candles(candles: list) -> str:
        if not candles:
            return "No data available"

        lines = []
        for candle in candles[-12:]:
            time = candle.get('open_time', 'N/A')
            o = candle.get('open', 0)
            c = candle.get('close', 0)
            change = ((c - o) / o * 100) if o > 0 else 0
            pattern = TechnicalAgent.detect_candle_pattern(candle)

            pattern_str = f" [{pattern}]" if pattern != "NONE" else ""
            lines.append(f"  {time}: ${c:.2f} ({change:+.1f}%){pattern_str}")

        return "\n".join(lines)



    @staticmethod
    def format_volume_progression(candles: list) -> str:
        if not candles or len(candles) < 14:
            return "Insufficient data"

        recent = candles[-14:]
        volumes = [c.get('volume', 0) for c in recent]

        first_half_avg = sum(volumes[:7]) / 7
        second_half_avg = sum(volumes[7:]) / 7
        volume_trend = "INCREASING" if second_half_avg > first_half_avg * 1.1 else "DECREASING" if second_half_avg < first_half_avg * 0.9 else "STABLE"

        first_half_buy = []
        second_half_buy = []

        for i, candle in enumerate(recent):
            volume = candle.get('volume', 0)
            taker_buy = candle.get('taker_buy_base', 0)
            buy_ratio = (taker_buy / volume * 100) if volume > 0 else 50.0

            if i < 7:
                first_half_buy.append(buy_ratio)
            else:
                second_half_buy.append(buy_ratio)

        avg_buy_first = sum(first_half_buy) / 7
        avg_buy_second = sum(second_half_buy) / 7
        buy_trend = "STRENGTHENING" if avg_buy_second > avg_buy_first + 3 else "WEAKENING" if avg_buy_second < avg_buy_first - 3 else "STABLE"

        latest = recent[-1]
        latest_buy = (latest.get('taker_buy_base', 0) / latest.get('volume', 1) * 100)

        return (
            f"  Volume Trend: {volume_trend}\n"
            f"  Recent 7d Avg: {second_half_avg:,.0f} ({((second_half_avg/first_half_avg - 1) * 100):+.1f}% vs prior 7d)\n"
            f"  Buying Pressure Trend: {buy_trend}\n"
            f"  Recent 7d Avg: {avg_buy_second:.1f}% (prior 7d: {avg_buy_first:.1f}%)\n"
            f"  Latest: {latest_buy:.1f}% (>50% = buyers control)"
        )



    @staticmethod
    def detect_patterns_at_levels(candles: list, support: float, resistance: float) -> str:
        if not candles or len(candles) < 2:
            return "Insufficient data"

        patterns = []
        recent = candles[-5:]

        for candle in recent:
            low = candle.get('low', 0)
            high = candle.get('high', 0)

            if support and abs(low - support) / support < 0.02:
                pattern = TechnicalAgent.detect_candle_pattern(candle)
                if pattern != "NONE":
                    patterns.append(f"  {pattern} at support ${support:.2f}")

            if resistance and abs(high - resistance) / resistance < 0.02:
                pattern = TechnicalAgent.detect_candle_pattern(candle)
                if pattern != "NONE":
                    patterns.append(f"  {pattern} at resistance ${resistance:.2f}")

        return "\n".join(patterns) if patterns else "  No significant patterns at key levels"



    def execute(self, state: AgentState) -> AgentState:
        with DataQuery() as dq:
            ticker = dq.get_ticker_data()
            if not ticker:
                raise ValueError("No ticker data available")

            indicators_data = dq.get_indicators_data()
            if not indicators_data:
                raise ValueError("No indicators data available")

            daily_candles = dq.get_candlestick_data(days=14)  # Last 14 days
            intraday_4h = dq.get_intraday_candles(limit=12)  # Last 48h of 4h candles

        current_price = float(ticker.get('lastPrice', 0))
        change_24h = float(ticker.get('priceChangePercent', 0))
        high_24h = float(ticker.get('highPrice', 0))
        low_24h = float(ticker.get('lowPrice', 0))

        range_24h = high_24h - low_24h
        if range_24h > 0:
            range_position_24h = (current_price - low_24h) / range_24h
        else:
            range_position_24h = 0.5

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
            max_tokens=4096
        )

        try:
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
            thinking = thinking_match.group(1).strip() if thinking_match else ""
            
            answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
            if answer_match:
                answer_json = answer_match.group(1).strip()
            else:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    answer_json = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")
            
            answer_json = answer_json.strip()
            answer_json = re.sub(r'^```json\s*', '', answer_json)
            answer_json = re.sub(r'\s*```$', '', answer_json)
            first_brace = answer_json.find('{')
            last_brace = answer_json.rfind('}')
            if first_brace != -1 and last_brace != -1:
                answer_json = answer_json[first_brace:last_brace+1]
            
            answer_json = answer_json.replace('"', '"').replace('"', '"')
            answer_json = answer_json.replace(''', "'").replace(''', "'")
            answer_json = re.sub(r'[\x00-\x1F\x7F]', '', answer_json)

            try:
                analysis = json.loads(answer_json)
            except json.JSONDecodeError as json_err:
                print(f"JSON Parse Error: {json_err}")
                print(f"Sanitized JSON (first 500 chars): {answer_json[:500]}")
                print(f"Sanitized JSON (around error position): {answer_json[max(0, json_err.pos-100):json_err.pos+100]}")
                raise

            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


            state['technical'] = {
                'timestamp': timestamp,
                'recommendation': analysis.get('recommendation', 'HOLD'),
                'confidence': float(analysis.get('confidence', 0.5)),
                'timeframe': analysis.get('timeframe', '1-7 days'),
                'key_signals': analysis.get('key_signals', []),
                'entry_level': analysis.get('entry_level'),
                'stop_loss': analysis.get('stop_loss'),
                'take_profit': analysis.get('take_profit'),
                'reasoning': analysis.get('reasoning', ''),
                'confidence_breakdown': analysis.get('confidence_breakdown', []),  
                'recommendation_summary': analysis.get('recommendation_summary', ''),
                'watch_list': analysis.get('watch_list', {}),
                'thinking': thinking if thinking else ''
            }

            with DataManager() as dm:
                dm.save_technical_analysis(data=state['technical'])


        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Technical agent parsing error: {e}")
            print(f"Response: {response[:300]}")

            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            state['technical'] = {
                'timestamp': timestamp,
                'recommendation': 'HOLD',
                'confidence': 0.0,
                'reasoning': f"Analysis parsing error: {str(e)[:100]}",
                'key_signals': [],
                'entry_level': None,
                'stop_loss': None,
                'take_profit': None,
                'timeframe': 'N/A',
                'confidence_breakdown': {},
                'recommendation_summary': 'Error occurred during analysis',
                'watch_list': {},
                'thinking': ''
            }

            # Save fallback data to database
            try:
                with DataManager() as dm:
                    dm.save_technical_analysis(data=state['technical'])
            except Exception as save_err:
                print(f"⚠️  Failed to save fallback technical analysis: {save_err}")

        return state


if __name__ == "__main__":
    agent = TechnicalAgent()
    test_state = AgentState()
    result = agent.execute(test_state)
    print("\n===== TECHNICAL AGENT OUTPUT =====")
    print(f"\n {result}")
