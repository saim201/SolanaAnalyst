# Technical Agent v2.0 - Complete Implementation Guide for Claude Code

## IMPORTANT: Read This First

This document contains ALL changes needed to refactor the TradingMate technical analysis agent. The changes address:

1. **Volume Bug** - Incomplete candle causing 0.14x ratio
2. **Chain of Thought** - Using XML `<thinking>` and `<answer>` tags for better reasoning
3. **Timestamps in Data** - Adding temporal context so LLM understands when data is from
4. **Indicator Curation** - Reducing from 30+ to 12 focused indicators
5. **Output Structure** - New actionable format with action plans and watch lists
6. **Model Upgrade** - From Haiku to Sonnet for better analysis

Follow each part in order. Test after each major part before proceeding.

---

## PART 1: VOLUME BUG FIX

### Problem
The `volume_ratio` shows ~0.14x because the last daily candle is incomplete (partial day volume). When the pipeline runs mid-day, today's candle only has a few hours of volume compared to the 20-day MA which uses complete 24-hour candles.

### File: `app/data/indicators.py`

### Step 1.1: Add imports at the top of the file (if not already present)

```python
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
```

### Step 1.2: Add this function AFTER the imports, BEFORE `classify_volume_quality`

```python
def exclude_incomplete_candle_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove the most recent candle if it's from today (incomplete).
    
    THE BUG: When pipeline runs mid-day, the last daily candle only has
    partial volume (e.g., 6 hours instead of 24 hours). This makes
    volume_ratio appear extremely low (0.14x) when actual volume is normal.
    
    THE FIX: Exclude today's incomplete candle from volume calculations.
    """
    if df.empty or len(df) < 2:
        return df
    
    last_open_time = df['open_time'].iloc[-1]
    
    # Handle different date formats
    if isinstance(last_open_time, str):
        try:
            last_date = datetime.fromisoformat(last_open_time.replace('Z', '+00:00')).date()
        except:
            return df
    elif hasattr(last_open_time, 'date'):
        last_date = last_open_time.date()
    elif isinstance(last_open_time, date):
        last_date = last_open_time
    else:
        return df
    
    today = date.today()
    
    if last_date == today:
        print(f" Excluding incomplete candle from {last_date} for volume calculation")
        return df.iloc[:-1].copy()
    
    return df
```

### Step 1.3: In `IndicatorsProcessor.calculate_all_indicators()`, find this code block:

```python
vol_ma = IndicatorsCalculator.volume_ma(df['volume'], 20)
current_vol = float(df['volume'].iloc[-1])
indicators['volume_ma20'] = float(vol_ma.iloc[-1] or 0)
indicators['volume_current'] = current_vol
indicators['volume_ratio'] = IndicatorsCalculator.volume_ratio(current_vol, indicators['volume_ma20'])
```

### Step 1.4: Replace it with:

```python
# VOLUME CALCULATION - Fixed to exclude incomplete candles
df_complete = exclude_incomplete_candle_df(df)

if len(df_complete) < 20:
    print(f"⚠️ Not enough complete candles for volume MA (need 20, got {len(df_complete)})")
    indicators['volume_ma20'] = 0
    indicators['volume_current'] = 0
    indicators['volume_ratio'] = 1.0
else:
    vol_ma = IndicatorsCalculator.volume_ma(df_complete['volume'], 20)
    # Use the last COMPLETE candle's volume, not today's partial
    current_vol = float(df_complete['volume'].iloc[-1])
    indicators['volume_ma20'] = float(vol_ma.iloc[-1] or 0)
    indicators['volume_current'] = current_vol
    indicators['volume_ratio'] = IndicatorsCalculator.volume_ratio(current_vol, indicators['volume_ma20'])
```

### Step 1.5: Also update `days_since_volume_spike` to use complete candles

Find:
```python
indicators['days_since_volume_spike'] = IndicatorsCalculator.days_since_volume_spike(df, spike_threshold=1.5)
```

Replace with:
```python
indicators['days_since_volume_spike'] = IndicatorsCalculator.days_since_volume_spike(df_complete, spike_threshold=1.5)
```

---

## PART 2: UPDATE DATABASE MODEL

### File: `app/database/models/analysis.py`

### Step 2.1: Update the TechnicalAnalyst model

Find your existing TechnicalAnalyst class and update it to include these fields:

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()  # Or use your existing Base

class TechnicalAnalyst(Base):
    __tablename__ = 'technical_analysis'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Core fields
    timestamp = Column(String(50))
    recommendation = Column(String(10))  # BUY, SELL, HOLD, WAIT
    confidence = Column(Float)
    market_condition = Column(String(20))  # TRENDING, RANGING, VOLATILE, QUIET
    
    # New structured fields (store as JSON)
    summary = Column(Text)  # 2-3 sentence actionable summary
    thinking = Column(JSON)  # Array of reasoning steps
    analysis = Column(JSON)  # {trend, momentum, volume} objects
    trade_setup = Column(JSON)  # {viability, entry, stop_loss, take_profit, etc.}
    action_plan = Column(JSON)  # {primary, alternative, if_in_position, avoid}
    watch_list = Column(JSON)  # {next_24h, next_48h} arrays
    invalidation = Column(JSON)  # Array of invalidation conditions
    confidence_reasoning = Column(JSON)  # {supporting, concerns, assessment}
```

### Step 2.2: Create database migration

After updating the model, run migration:

```bash
# If using Alembic
alembic revision --autogenerate -m "Update technical analysis schema v2"
alembic upgrade head

# Or if manually managing schema, run this SQL:
# ALTER TABLE technical_analysis ADD COLUMN market_condition VARCHAR(20);
# ALTER TABLE technical_analysis ADD COLUMN summary TEXT;
# ALTER TABLE technical_analysis ADD COLUMN thinking JSON;
# ALTER TABLE technical_analysis ADD COLUMN analysis JSON;
# ALTER TABLE technical_analysis ADD COLUMN trade_setup JSON;
# ALTER TABLE technical_analysis ADD COLUMN action_plan JSON;
# ALTER TABLE technical_analysis ADD COLUMN watch_list JSON;
# ALTER TABLE technical_analysis ADD COLUMN invalidation JSON;
# ALTER TABLE technical_analysis ADD COLUMN confidence_reasoning JSON;
```

---

## PART 3: UPDATE TECHNICAL AGENT

### File: `app/agents/technical.py`

### Step 3.1: Update imports at the top

Make sure these imports are present:

```python
import sys
import os
import json
import re
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional, Any

# Your existing imports
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager
```

### Step 3.2: Change the model from Haiku to Sonnet

Find:
```python
def __init__(self):
    super().__init__(
        model="claude-3-5-haiku-20241022",
        temperature=0.3
    )
```

Replace with:
```python
def __init__(self):
    super().__init__(
        model="claude-sonnet-4-20250514",
        temperature=0.3
    )
```

### Step 3.3: Replace SYSTEM_PROMPT entirely

Delete the existing SYSTEM_PROMPT and replace with:

```python
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
```

### Step 3.4: Replace TECHNICAL_PROMPT entirely

Delete the existing TECHNICAL_PROMPT and replace with:

```python
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

### OUTPUT FORMAT:

After your thinking, output the final JSON inside <answer> tags. The JSON must follow this EXACT structure:

```json
{{
  "recommendation": "BUY|SELL|HOLD|WAIT",
  "confidence": 0.72,
  "market_condition": "TRENDING|RANGING|VOLATILE|QUIET",
  
  "summary": "2-3 sentences: What's happening and what to do. Be specific and actionable.",
  
  "thinking": [
    "Market story: [your observation]",
    "Volume assessment: [your observation]",
    "Momentum read: [your observation]",
    "BTC context: [your observation]",
    "Setup evaluation: [your observation]",
    "Key conclusion: [your conclusion]"
  ],
  
  "analysis": {{
    "trend": {{
      "direction": "BULLISH|BEARISH|NEUTRAL",
      "strength": "STRONG|MODERATE|WEAK",
      "detail": "1-2 sentences max"
    }},
    "momentum": {{
      "direction": "BULLISH|BEARISH|NEUTRAL",
      "strength": "STRONG|MODERATE|WEAK",
      "detail": "1-2 sentences max"
    }},
    "volume": {{
      "quality": "STRONG|ACCEPTABLE|WEAK|DEAD",
      "ratio": 0.82,
      "detail": "1-2 sentences max"
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
    "primary": "Main action to take",
    "alternative": "Alternative if primary doesn't trigger",
    "if_in_position": "Guidance for existing holders",
    "avoid": "What NOT to do"
  }},
  
  "watch_list": {{
    "next_24h": ["Item 1", "Item 2", "Item 3"],
    "next_48h": ["Item 1", "Item 2", "Item 3"]
  }},
  
  "invalidation": [
    "Condition 1 that kills the thesis",
    "Condition 2 that kills the thesis"
  ],
  
  "confidence_reasoning": {{
    "supporting": ["Factor 1", "Factor 2", "Factor 3"],
    "concerns": ["Concern 1", "Concern 2", "Concern 3"],
    "assessment": "One sentence explaining final confidence score"
  }}
}}
```

IMPORTANT NOTES:
- Write your full reasoning in <thinking> tags FIRST
- Then output ONLY valid JSON in <answer> tags
- All price values should be numbers, not strings
- Confidence should be between 0.0 and 1.0
- If recommending HOLD/WAIT, set entry/stop_loss/take_profit to null but still provide support/resistance/current_price
</instructions>
"""
```

### Step 3.5: Add helper functions BEFORE the TechnicalAgent class

Add these functions after the prompts but before the class definition:

```python
def calculate_distance_percent(current: float, level: float) -> float:
    """Calculate percentage distance from current price to a level."""
    if current == 0:
        return 0.0
    return ((level - current) / current) * 100


def get_btc_interpretation(correlation: float, btc_trend: str) -> str:
    """Generate human-readable BTC correlation interpretation."""
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
    """Get human-readable RSI status."""
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
    """Describe MACD histogram trend."""
    if histogram > 0:
        return "Positive - bullish momentum"
    elif histogram < 0:
        return "Negative - bearish momentum"
    else:
        return "Neutral"


def get_atr_interpretation(atr_percent: float) -> str:
    """Interpret ATR as volatility context."""
    if atr_percent >= 8:
        return "HIGH volatility - expect large swings"
    elif atr_percent >= 4:
        return "MODERATE volatility - normal for SOL"
    else:
        return "LOW volatility - potential breakout building"


def get_volume_trend(buy_pressure: float, volume_ratio: float) -> str:
    """Describe overall volume trend."""
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
    """Classify correlation strength."""
    if correlation >= 0.8:
        return "VERY STRONG"
    elif correlation >= 0.6:
        return "STRONG"
    elif correlation >= 0.4:
        return "MODERATE"
    else:
        return "WEAK"


def format_recent_price_action(candles: list, limit: int = 7) -> str:
    """Format recent daily candles with timestamps for context."""
    if not candles:
        return "No recent data available"
    
    lines = []
    for candle in candles[-limit:]:
        # Get date
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
    """Calculate where current price sits in 14d range (0-100%)."""
    range_size = high_14d - low_14d
    if range_size == 0:
        return 0.5
    return (current - low_14d) / range_size
```

### Step 3.6: Replace the entire execute() method

Find the existing `execute()` method and replace it entirely with:

```python
def execute(self, state: AgentState) -> AgentState:
    """Main execution method with chain-of-thought prompting."""
    
    # ----- STEP 1: Fetch Data -----
    with DataQuery() as dq:
        ticker = dq.get_ticker_data()
        if not ticker:
            raise ValueError("No ticker data available")

        indicators_data = dq.get_indicators_data()
        if not indicators_data:
            raise ValueError("No indicators data available")

        daily_candles = dq.get_candlestick_data(days=14)

    # ----- STEP 2: Extract Current Values -----
    current_price = float(ticker.get('lastPrice', 0))
    change_24h = float(ticker.get('priceChangePercent', 0))
    high_24h = float(ticker.get('highPrice', 0))
    low_24h = float(ticker.get('lowPrice', 0))

    # Range position in 24h
    range_24h = high_24h - low_24h
    range_position_24h = (current_price - low_24h) / range_24h if range_24h > 0 else 0.5

    # ----- STEP 3: Extract Indicator Values -----
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

    # BTC correlation
    sol_btc_correlation = float(indicators_data.get('sol_btc_correlation', 0.8))
    btc_trend = indicators_data.get('btc_trend', 'NEUTRAL')
    btc_price_change_30d = float(indicators_data.get('btc_price_change_30d', 0))

    # ----- STEP 4: Calculate Derived Values -----
    ema20_distance = calculate_distance_percent(current_price, ema20)
    ema50_distance = calculate_distance_percent(current_price, ema50)
    support1_distance = abs(calculate_distance_percent(current_price, support1))
    support2_distance = abs(calculate_distance_percent(current_price, support2))
    resistance1_distance = calculate_distance_percent(current_price, resistance1)
    resistance2_distance = calculate_distance_percent(current_price, resistance2)
    price_position_14d = calculate_price_position_in_range(current_price, high_14d, low_14d)

    # Status strings
    rsi_status = get_rsi_status(rsi14)
    macd_trend = get_macd_trend(macd_histogram)
    bb_squeeze_status = "ACTIVE (breakout imminent)" if bb_squeeze_active else "INACTIVE"
    btc_interpretation = get_btc_interpretation(sol_btc_correlation, btc_trend)
    atr_interpretation = get_atr_interpretation(atr_percent)
    volume_trend = get_volume_trend(weighted_buy_pressure, volume_ratio)
    correlation_strength = get_correlation_strength(sol_btc_correlation)
    
    # Format price action with timestamps
    recent_price_action = format_recent_price_action(daily_candles, limit=7)
    
    # Analysis timestamp
    analysis_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    # ----- STEP 5: Build Prompt -----
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

    # ----- STEP 6: Call LLM -----
    response = llm(
        full_prompt,
        model=self.model,
        temperature=self.temperature,
        max_tokens=4096
    )

    # ----- STEP 7: Parse Response -----
    try:
        # Extract thinking section (for logging/debugging)
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
        raw_thinking = thinking_match.group(1).strip() if thinking_match else ""
        
        # Extract answer section
        answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
        if answer_match:
            json_str = answer_match.group(1).strip()
        else:
            # Fallback: try to find JSON directly
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")
        
        # Clean up JSON string
        json_str = json_str.replace('"', '"').replace('"', '"')
        json_str = json_str.replace(''', "'").replace(''', "'")
        json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
        
        # Remove markdown code blocks if present
        json_str = re.sub(r'^```json\s*', '', json_str)
        json_str = re.sub(r'\s*```$', '', json_str)
        
        # Find the JSON object
        first_brace = json_str.find('{')
        last_brace = json_str.rfind('}')
        if first_brace != -1 and last_brace != -1:
            json_str = json_str[first_brace:last_brace+1]
        
        analysis = json.loads(json_str)
        
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        state['technical'] = {
            'timestamp': timestamp,
            'recommendation': analysis.get('recommendation', 'HOLD'),
            'confidence': float(analysis.get('confidence', 0.5)),
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

        # Save to database
        with DataManager() as dm:
            dm.save_technical_analysis(data=state['technical'])
            
        # Log the raw thinking for debugging
        if raw_thinking:
            print(f" LLM Thinking Process:\n{raw_thinking[:500]}...")

    except (json.JSONDecodeError, ValueError) as e:
        print(f" Technical agent parsing error: {e}")
        print(f"Response preview: {response[:500]}")
        
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        state['technical'] = {
            'timestamp': timestamp,
            'recommendation': 'HOLD',
            'confidence': 0.0,
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
            print(f"  Failed to save fallback: {save_err}")

    return state
```

### Step 3.7: Remove old helper methods from the class

Delete these methods from inside the TechnicalAgent class (they are no longer used):
- `detect_candle_pattern()` 
- `format_daily_ohlc()`
- `format_4h_candles()`
- `format_volume_progression()`
- `detect_patterns_at_levels()`

---

## PART 4: UPDATE DATA MANAGER

### File: `app/database/data_manager.py`

### Step 4.1: Update save_technical_analysis() method

Find the `save_technical_analysis()` method and replace it with:

```python
def save_technical_analysis(self, data: dict):
    """Save technical analysis with v2 schema."""
    from app.database.models.analysis import TechnicalAnalyst
    
    record = TechnicalAnalyst(
        timestamp=data.get('timestamp'),
        recommendation=data.get('recommendation'),
        confidence=data.get('confidence'),
        market_condition=data.get('market_condition'),
        summary=data.get('summary'),
        thinking=data.get('thinking'),
        analysis=data.get('analysis'),
        trade_setup=data.get('trade_setup'),
        action_plan=data.get('action_plan'),
        watch_list=data.get('watch_list'),
        invalidation=data.get('invalidation'),
        confidence_reasoning=data.get('confidence_reasoning'),
    )
    
    self.db.add(record)
    self.db.commit()
    print(f" Saved technical analysis: {data.get('recommendation')} @ {data.get('confidence'):.0%} confidence")
```

---

## PART 5: UPDATE API ROUTES

### File: `app/api/routes.py`

### Step 5.1: Update the technical_data dictionary in get_latest_analysis()

Find the `technical_data = {...}` dictionary and replace it with:

```python
technical_data = {
    "timestamp": technical.timestamp if technical.timestamp else technical.created_at.isoformat(),
    "recommendation": technical.recommendation,
    "confidence": technical.confidence,
    "market_condition": technical.market_condition,
    "summary": technical.summary,
    "thinking": technical.thinking,
    "analysis": technical.analysis,
    "trade_setup": technical.trade_setup,
    "action_plan": technical.action_plan,
    "watch_list": technical.watch_list,
    "invalidation": technical.invalidation,
    "confidence_reasoning": technical.confidence_reasoning,
}
```

---

## PART 6: UPDATE API SCHEMA (Optional but Recommended)

### File: `app/api/schemas.py`

### Step 6.1: Add/update Pydantic models for type safety

```python
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class TrendAnalysis(BaseModel):
    direction: str  # BULLISH, BEARISH, NEUTRAL
    strength: str  # STRONG, MODERATE, WEAK
    detail: str

class MomentumAnalysis(BaseModel):
    direction: str
    strength: str
    detail: str

class VolumeAnalysis(BaseModel):
    quality: str  # STRONG, ACCEPTABLE, WEAK, DEAD
    ratio: float
    detail: str

class Analysis(BaseModel):
    trend: TrendAnalysis
    momentum: MomentumAnalysis
    volume: VolumeAnalysis

class TradeSetup(BaseModel):
    viability: str  # VALID, WAIT, INVALID
    entry: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward: Optional[float]
    support: float
    resistance: float
    current_price: float
    timeframe: str

class ActionPlan(BaseModel):
    primary: str
    alternative: str
    if_in_position: str
    avoid: str

class WatchList(BaseModel):
    next_24h: List[str]
    next_48h: List[str]

class ConfidenceReasoning(BaseModel):
    supporting: List[str]
    concerns: List[str]
    assessment: str

class TechnicalAnalysisV2(BaseModel):
    timestamp: str
    recommendation: str
    confidence: float
    market_condition: str
    summary: str
    thinking: List[str]
    analysis: Analysis
    trade_setup: TradeSetup
    action_plan: ActionPlan
    watch_list: WatchList
    invalidation: List[str]
    confidence_reasoning: ConfidenceReasoning
```

---

## PART 7: VERIFICATION TESTS

After implementing all changes, run these tests:

### Test 7.1: Volume Fix Verification

```python
# Run in Python shell or create a test file
from app.data.indicators import exclude_incomplete_candle_df
import pandas as pd
from datetime import datetime, timedelta

# Create test data with today's incomplete candle
today = datetime.now()
dates = [today - timedelta(days=i) for i in range(25, 0, -1)]
dates.append(today)  # Add today (incomplete)

df = pd.DataFrame({
    'open_time': dates,
    'volume': [1000000] * 25 + [150000],  # Today has low volume
})

df_fixed = exclude_incomplete_candle_df(df)
print(f"Original rows: {len(df)}, Fixed rows: {len(df_fixed)}")
print(f"Incomplete candle excluded: {len(df) != len(df_fixed)}")
# Expected: Original rows: 26, Fixed rows: 25
```

### Test 7.2: Technical Agent Output Structure

```python
from app.agents.technical import TechnicalAgent
from app.agents.base import AgentState
import json

agent = TechnicalAgent()
state = AgentState()
result = agent.execute(state)

tech = result.get('technical', {})

# Verify all required fields exist
required_fields = [
    'timestamp', 'recommendation', 'confidence', 'market_condition',
    'summary', 'thinking', 'analysis', 'trade_setup', 'action_plan',
    'watch_list', 'invalidation', 'confidence_reasoning'
]

for field in required_fields:
    assert field in tech, f"Missing field: {field}"
    print(f" {field}: present")

# Verify thinking is array
assert isinstance(tech['thinking'], list), "thinking should be array"
print(f"✅thinking has {len(tech['thinking'])} steps")

# Verify watch_list structure
assert 'next_24h' in tech.get('watch_list', {}), "Missing next_24h"
assert 'next_48h' in tech.get('watch_list', {}), "Missing next_48h"
print(f" watch_list has 24h and 48h sections")

# Verify confidence is reasonable
conf = tech.get('confidence', 0)
assert 0 <= conf <= 1, f"Confidence {conf} out of range"
print(f" confidence: {conf:.0%}")

print("\n Full output:")
print(json.dumps(tech, indent=2))
```

### Test 7.3: API Response Test

```bash
# Start your server, then:
curl http://localhost:8000/api/sol/latest | python -m json.tool

# Verify technical_analysis has the new structure
```

---

## SUMMARY: Files Changed

| File | Changes Made |
|------|-------------|
| `app/data/indicators.py` | Added `exclude_incomplete_candle_df()`, fixed volume calculation |
| `app/database/models/analysis.py` | Added new JSON columns for v2 schema |
| `app/agents/technical.py` | New prompts with XML tags, helper functions, execute() method, Sonnet model |
| `app/database/data_manager.py` | Updated `save_technical_analysis()` |
| `app/api/routes.py` | Updated `technical_data` dictionary |
| `app/api/schemas.py` | Added Pydantic models (optional) |

---

## ROLLBACK PLAN

If something breaks badly:

1. Change model back to `claude-3-5-haiku-20241022`
2. Restore original SYSTEM_PROMPT and TECHNICAL_PROMPT
3. Restore original execute() method
4. **Keep the volume fix** - it's a bug fix, not a feature change

---

## KEY IMPROVEMENTS SUMMARY

1. **Volume Bug Fixed** - No more 0.14x false readings
2. **Chain of Thought** - Using `<thinking>` and `<answer>` XML tags for better reasoning
3. **Timestamps Added** - Price history now shows dates so LLM understands temporal context
4. **Richer Context** - Added RSI status, MACD trend, ATR interpretation, volume trend
5. **Curated Indicators** - Focused on 12 key indicators instead of 30+
6. **Better Output** - Actionable structure with action_plan, watch_list (24h/48h), invalidation
7. **Model Upgrade** - Sonnet for more sophisticated analysis
8. **Confidence Separated** - Clear supporting factors vs concerns

---

## END OF IMPLEMENTATION GUIDE
