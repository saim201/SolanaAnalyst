# Post-Implementation Cleanup Guide for Claude Code

## IMPORTANT: Run This AFTER Implementing FINAL_IMPLEMENTATION_GUIDE.md

This guide helps you verify all changes are working correctly, then clean up unused code, database columns, and indicators.

---

## PHASE 1: VERIFY ALL CHANGES ARE WORKING

Before removing anything, confirm the implementation is working.

### Step 1.1: Test the Technical Agent

Run this test:

```python
from app.agents.technical import TechnicalAgent
from app.agents.base import AgentState
import json

agent = TechnicalAgent()
state = AgentState()
result = agent.execute(state)

tech = result.get('technical', {})

# Print the output
print(json.dumps(tech, indent=2))

# Check required fields
required = ['recommendation', 'confidence', 'market_condition', 'summary', 
            'thinking', 'analysis', 'trade_setup', 'action_plan', 
            'watch_list', 'invalidation', 'confidence_reasoning']

missing = [f for f in required if f not in tech]
if missing:
    print(f"❌ MISSING FIELDS: {missing}")
else:
    print("✅ All required fields present")

# Check thinking is populated
if tech.get('thinking') and len(tech['thinking']) >= 3:
    print(f"✅ Thinking has {len(tech['thinking'])} steps")
else:
    print("❌ Thinking is empty or too short")

# Check confidence is reasonable (not 0 or near 0 unless market is dead)
if tech.get('confidence', 0) > 0.1:
    print(f"✅ Confidence: {tech['confidence']:.0%}")
else:
    print(f"⚠️  Low confidence: {tech.get('confidence', 0):.0%} - verify this is correct")
```

**If test fails:** Do not proceed. Fix the implementation first.

**If test passes:** Continue to Phase 2.

---

## PHASE 2: IDENTIFY UNUSED INDICATORS

### Current Indicators Used in New Prompt

The new technical agent prompt uses ONLY these indicators:

**CORE (Always used):**
```
ema20, ema50
rsi14, rsi_divergence_type, rsi_divergence_strength
macd_line, macd_signal, macd_histogram
volume_ratio, volume_classification, weighted_buy_pressure, days_since_volume_spike
support1, support2, resistance1, resistance2
support1_percent, support2_percent, resistance1_percent, resistance2_percent
high_14d, low_14d
atr, atr_percent
```

**SITUATIONAL (Sometimes used):**
```
bb_squeeze_ratio, bb_squeeze_active
sol_btc_correlation, btc_trend, btc_price_change_30d
```

### Indicators NO LONGER Used (Can Be Removed)

```
ema200                    # Too slow for swing trading
stoch_rsi                 # Redundant with RSI
kijun_sen                 # Ichimoku noise, not needed
vwap                      # Day trading indicator
vwap_distance_percent     # Not used
fib_level_382             # Not in new prompt
fib_level_618             # Not in new prompt
pivot_weekly              # Not in new prompt
momentum_24h              # Calculated differently now
range_position_24h        # Calculated from ticker directly
volume_surge_24h          # Replaced by volume_ratio
btc_price                 # Not displayed, only btc_trend used
volume_current            # Internal calculation, not in prompt
volume_confidence_multiplier  # Logic moved to prompt
volume_trading_allowed    # Logic moved to prompt
```

---

## PHASE 3: CLEAN UP indicators.py

### File: `app/data/indicators.py`

### Step 3.1: In `IndicatorsProcessor.calculate_all_indicators()`, REMOVE these calculations:

Find and DELETE these blocks:

```python
# REMOVE: EMA200 calculation
indicators['ema200'] = float(IndicatorsCalculator.ema(df['close'], 200).iloc[-1] or 0)
```

```python
# REMOVE: Stochastic RSI
indicators['stoch_rsi'] = IndicatorsCalculator.stochastic_rsi(rsi_series, period=14)
```

```python
# REMOVE: Kijun-Sen
indicators['kijun_sen'] = IndicatorsCalculator.kijun_sen(df, period=26)
```

```python
# REMOVE: VWAP calculations
vwap_data = IndicatorsCalculator.calculate_vwap(df.tail(20))
indicators['vwap'] = vwap_data['vwap']
indicators['vwap_distance_percent'] = vwap_data['vwap_distance_percent']
```

```python
# REMOVE: Fibonacci levels
swing_high, swing_low = IndicatorsCalculator.find_recent_swing(df, 30)
fib_levels = IndicatorsCalculator.fibonacci_retracement(swing_high, swing_low)
indicators['fib_level_382'] = float(fib_levels['38.2%'])
indicators['fib_level_618'] = float(fib_levels['61.8%'])
```

```python
# REMOVE: Weekly pivot
if len(df) >= 7:
    last_week = df.tail(7)
    week_high = float(last_week['high'].max())
    week_low = float(last_week['low'].min())
    week_close = float(last_week['close'].iloc[-1])
    indicators['pivot_weekly'] = (week_high + week_low + week_close) / 3
else:
    indicators['pivot_weekly'] = None
```

### Step 3.2: In `IndicatorsCalculator` class, these methods are NO LONGER NEEDED:

You can REMOVE these methods (or keep them for potential future use):

```python
# OPTIONAL TO REMOVE - Not used in new implementation:

@staticmethod
def kijun_sen(df: pd.DataFrame, period: int = 26) -> float:
    # ... entire method

@staticmethod
def stochastic_rsi(rsi_series: pd.Series, period: int = 14) -> float:
    # ... entire method

@staticmethod
def calculate_vwap(df: pd.DataFrame) -> Dict[str, float]:
    # ... entire method

@staticmethod
def fibonacci_retracement(swing_high: float, swing_low: float) -> Dict[str, float]:
    # ... entire method

@staticmethod
def find_recent_swing(df: pd.DataFrame, lookback_days: int = 30) -> Tuple[float, float]:
    # ... entire method
```

**NOTE:** If you want to keep these methods for future use, that's fine. Just ensure they're not being called.

### Step 3.3: In `IndicatorsProcessor.calculate_ticker_indicators()`, verify it only calculates what's needed:

The method should calculate:
- `momentum_24h` - Keep if used elsewhere, otherwise remove
- `range_position_24h` - Keep if used elsewhere, otherwise remove
- `volume_surge_24h` - Keep if used elsewhere, otherwise remove

If these are ONLY used by the old technical agent and not elsewhere, you can simplify or remove this method.

---

## PHASE 4: CLEAN UP DATABASE MODEL - IndicatorsModel

### File: `app/database/models/indicators.py` (or wherever IndicatorsModel is defined)

### Step 4.1: Identify columns to REMOVE from IndicatorsModel

These columns are NO LONGER populated or used:

```python
# REMOVE these columns from IndicatorsModel:

ema200 = Column(Float)              # Not used
stoch_rsi = Column(Float)           # Not used
kijun_sen = Column(Float)           # Not used
vwap = Column(Float)                # Not used
vwap_distance_percent = Column(Float)  # Not used
fib_level_382 = Column(Float)       # Not used
fib_level_618 = Column(Float)       # Not used
pivot_weekly = Column(Float)        # Not used
momentum_24h = Column(Float)        # Check if used elsewhere
range_position_24h = Column(Float)  # Check if used elsewhere
volume_surge_24h = Column(Float)    # Check if used elsewhere
volume_confidence_multiplier = Column(Float)  # Logic in prompt now
volume_trading_allowed = Column(String)       # Logic in prompt now
```

### Step 4.2: Keep these columns in IndicatorsModel:

```python
class IndicatorsModel(Base):
    __tablename__ = 'indicators'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    
    # KEEP - Trend
    ema20 = Column(Float)
    ema50 = Column(Float)
    high_14d = Column(Float)
    low_14d = Column(Float)
    
    # KEEP - Momentum
    rsi14 = Column(Float)
    rsi_divergence_type = Column(String)
    rsi_divergence_strength = Column(Float)
    macd_line = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    
    # KEEP - Volume
    volume_ma20 = Column(Float)
    volume_current = Column(Float)
    volume_ratio = Column(Float)
    volume_classification = Column(String)
    weighted_buy_pressure = Column(Float)
    days_since_volume_spike = Column(Integer)
    
    # KEEP - Levels
    support1 = Column(Float)
    support1_percent = Column(Float)
    support2 = Column(Float)
    support2_percent = Column(Float)
    resistance1 = Column(Float)
    resistance1_percent = Column(Float)
    resistance2 = Column(Float)
    resistance2_percent = Column(Float)
    
    # KEEP - Volatility
    atr = Column(Float)
    atr_percent = Column(Float)
    bb_upper = Column(Float)
    bb_lower = Column(Float)
    bb_squeeze_ratio = Column(Float)
    bb_squeeze_active = Column(String)
    
    # KEEP - BTC Correlation
    btc_price = Column(Float)
    btc_price_change_30d = Column(Float)
    btc_trend = Column(String)
    sol_btc_correlation = Column(Float)
    btc_correlation_strength = Column(String)
```

### Step 4.3: Create migration to drop unused columns

```bash
# Using Alembic
alembic revision -m "Remove unused indicator columns"
```

In the migration file:

```python
def upgrade():
    # Drop unused columns
    op.drop_column('indicators', 'ema200')
    op.drop_column('indicators', 'stoch_rsi')
    op.drop_column('indicators', 'kijun_sen')
    op.drop_column('indicators', 'vwap')
    op.drop_column('indicators', 'vwap_distance_percent')
    op.drop_column('indicators', 'fib_level_382')
    op.drop_column('indicators', 'fib_level_618')
    op.drop_column('indicators', 'pivot_weekly')
    op.drop_column('indicators', 'volume_confidence_multiplier')
    op.drop_column('indicators', 'volume_trading_allowed')
    # Add more as needed

def downgrade():
    # Add columns back if needed
    op.add_column('indicators', sa.Column('ema200', sa.Float))
    # ... etc
```

---

## PHASE 5: CLEAN UP DATABASE MODEL - TechnicalAnalyst

### File: `app/database/models/analysis.py`

### Step 5.1: Remove OLD columns from TechnicalAnalyst that are no longer used:

```python
# REMOVE these columns (replaced by new schema):

reasoning = Column(Text)              # REPLACED BY: summary + thinking
key_signals = Column(JSON)            # REPLACED BY: analysis
recommendation_summary = Column(Text) # REPLACED BY: summary + action_plan
confidence_breakdown = Column(JSON)   # REPLACED BY: confidence_reasoning
indicators_analysis = Column(JSON)    # REMOVED - not needed
btc_correlation_impact = Column(JSON) # REMOVED - folded into analysis
entry_level = Column(Float)           # REPLACED BY: trade_setup.entry
stop_loss = Column(Float)             # REPLACED BY: trade_setup.stop_loss
take_profit = Column(Float)           # REPLACED BY: trade_setup.take_profit
timeframe = Column(String)            # REPLACED BY: trade_setup.timeframe
```

### Step 5.2: Final TechnicalAnalyst model should look like:

```python
class TechnicalAnalyst(Base):
    __tablename__ = 'technical_analysis'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Core
    timestamp = Column(String(50))
    recommendation = Column(String(10))
    confidence = Column(Float)
    market_condition = Column(String(20))
    
    # New v2 fields
    summary = Column(Text)
    thinking = Column(JSON)
    analysis = Column(JSON)
    trade_setup = Column(JSON)
    action_plan = Column(JSON)
    watch_list = Column(JSON)
    invalidation = Column(JSON)
    confidence_reasoning = Column(JSON)
```

### Step 5.3: Create migration

```python
def upgrade():
    # Drop old columns
    op.drop_column('technical_analysis', 'reasoning')
    op.drop_column('technical_analysis', 'key_signals')
    op.drop_column('technical_analysis', 'recommendation_summary')
    op.drop_column('technical_analysis', 'confidence_breakdown')
    op.drop_column('technical_analysis', 'indicators_analysis')
    op.drop_column('technical_analysis', 'btc_correlation_impact')
    op.drop_column('technical_analysis', 'entry_level')
    op.drop_column('technical_analysis', 'stop_loss')
    op.drop_column('technical_analysis', 'take_profit')
    op.drop_column('technical_analysis', 'timeframe')
```

---

## PHASE 6: CLEAN UP db_fetcher.py

### File: `app/agents/db_fetcher.py`

### Step 6.1: Update `get_indicators_data()` to only return used fields

The method should only return indicators that are actually used. Update the return dictionary:

```python
def get_indicators_data(self, days: int = 30) -> dict:
    cutoff = datetime.now() - timedelta(days=days)
    indicators = self.db.query(IndicatorsModel).filter(
        IndicatorsModel.timestamp >= cutoff
    ).order_by(IndicatorsModel.timestamp.desc()).first()

    if not indicators:
        return {}

    return {
        "timestamp": indicators.timestamp,
        
        # Trend
        "ema20": indicators.ema20,
        "ema50": indicators.ema50,
        "high_14d": indicators.high_14d,
        "low_14d": indicators.low_14d,
        
        # Momentum
        "rsi14": indicators.rsi14,
        "rsi_divergence_type": indicators.rsi_divergence_type,
        "rsi_divergence_strength": indicators.rsi_divergence_strength,
        "macd_line": indicators.macd_line,
        "macd_signal": indicators.macd_signal,
        "macd_histogram": indicators.macd_histogram,
        
        # Volume
        "volume_ma20": indicators.volume_ma20,
        "volume_ratio": indicators.volume_ratio,
        "volume_classification": indicators.volume_classification,
        "weighted_buy_pressure": indicators.weighted_buy_pressure,
        "days_since_volume_spike": indicators.days_since_volume_spike,
        
        # Levels
        "support1": indicators.support1,
        "support1_percent": indicators.support1_percent,
        "support2": indicators.support2,
        "support2_percent": indicators.support2_percent,
        "resistance1": indicators.resistance1,
        "resistance1_percent": indicators.resistance1_percent,
        "resistance2": indicators.resistance2,
        "resistance2_percent": indicators.resistance2_percent,
        
        # Volatility
        "atr": indicators.atr,
        "atr_percent": indicators.atr_percent,
        "bb_squeeze_ratio": indicators.bb_squeeze_ratio,
        "bb_squeeze_active": indicators.bb_squeeze_active == 'True',
        
        # BTC
        "sol_btc_correlation": indicators.sol_btc_correlation,
        "btc_trend": indicators.btc_trend,
        "btc_price_change_30d": indicators.btc_price_change_30d,
        "btc_correlation_strength": indicators.btc_correlation_strength,
    }
```

**REMOVE** these from the return dictionary (no longer used):
- `ema200`
- `stoch_rsi`
- `kijun_sen`
- `vwap`
- `vwap_distance_percent`
- `fib_level_382`
- `fib_level_618`
- `pivot_weekly`
- `momentum_24h`
- `range_position_24h`
- `volume_surge_24h`
- `volume_confidence_multiplier`
- `volume_trading_allowed`
- `btc_price`
- `volume_current`

---

## PHASE 7: CLEAN UP data_manager.py

### File: `app/database/data_manager.py`

### Step 7.1: Update `save_indicators()` to only save used fields

Find the `save_indicators()` method and update it to only save the indicators we're actually using:

```python
def save_indicators(self, timestamp: datetime, indicators: dict):
    """Save calculated indicators to database."""
    from app.database.models.indicators import IndicatorsModel
    
    record = IndicatorsModel(
        timestamp=timestamp,
        
        # Trend
        ema20=indicators.get('ema20'),
        ema50=indicators.get('ema50'),
        high_14d=indicators.get('high_14d'),
        low_14d=indicators.get('low_14d'),
        
        # Momentum
        rsi14=indicators.get('rsi14'),
        rsi_divergence_type=indicators.get('rsi_divergence_type'),
        rsi_divergence_strength=indicators.get('rsi_divergence_strength'),
        macd_line=indicators.get('macd_line'),
        macd_signal=indicators.get('macd_signal'),
        macd_histogram=indicators.get('macd_histogram'),
        
        # Volume
        volume_ma20=indicators.get('volume_ma20'),
        volume_current=indicators.get('volume_current'),
        volume_ratio=indicators.get('volume_ratio'),
        volume_classification=indicators.get('volume_classification'),
        weighted_buy_pressure=indicators.get('weighted_buy_pressure'),
        days_since_volume_spike=indicators.get('days_since_volume_spike'),
        
        # Levels
        support1=indicators.get('support1'),
        support1_percent=indicators.get('support1_percent'),
        support2=indicators.get('support2'),
        support2_percent=indicators.get('support2_percent'),
        resistance1=indicators.get('resistance1'),
        resistance1_percent=indicators.get('resistance1_percent'),
        resistance2=indicators.get('resistance2'),
        resistance2_percent=indicators.get('resistance2_percent'),
        
        # Volatility
        atr=indicators.get('atr'),
        atr_percent=indicators.get('atr_percent'),
        bb_upper=indicators.get('bb_upper'),
        bb_lower=indicators.get('bb_lower'),
        bb_squeeze_ratio=indicators.get('bb_squeeze_ratio'),
        bb_squeeze_active=str(indicators.get('bb_squeeze_active', False)),
        
        # BTC
        btc_price=indicators.get('btc_price'),
        btc_price_change_30d=indicators.get('btc_price_change_30d'),
        btc_trend=indicators.get('btc_trend'),
        sol_btc_correlation=indicators.get('sol_btc_correlation'),
        btc_correlation_strength=indicators.get('btc_correlation_strength'),
    )
    
    self.db.add(record)
    self.db.commit()
    print(f"✅ Saved indicators at {timestamp}")
```

**REMOVE** these from the save (no longer calculated):
- `ema200`
- `stoch_rsi`
- `kijun_sen`
- `vwap`
- `vwap_distance_percent`
- `fib_level_382`
- `fib_level_618`
- `pivot_weekly`
- `momentum_24h`
- `range_position_24h`
- `volume_surge_24h`
- `volume_confidence_multiplier`
- `volume_trading_allowed`

---

## PHASE 8: VERIFY CLEANUP

### Step 8.1: Run the full pipeline

```python
from app.data.refresh_manager import RefreshManager

# This should complete without errors
RefreshManager.refresh_all_data()
```

### Step 8.2: Run the technical agent again

```python
from app.agents.technical import TechnicalAgent
from app.agents.base import AgentState

agent = TechnicalAgent()
state = AgentState()
result = agent.execute(state)

print(f"Recommendation: {result['technical']['recommendation']}")
print(f"Confidence: {result['technical']['confidence']:.0%}")
print(f"Summary: {result['technical']['summary']}")
```

### Step 8.3: Test API endpoint

```bash
curl http://localhost:8000/api/sol/analyse -X POST
curl http://localhost:8000/api/sol/latest
```

---

## PHASE 9: OPTIONAL - Remove Unused Files/Functions

### Check if these functions are used anywhere else before removing:

In `indicators.py` - IndicatorsCalculator class:
- `kijun_sen()` - Remove if not used
- `stochastic_rsi()` - Remove if not used
- `calculate_vwap()` - Remove if not used
- `fibonacci_retracement()` - Remove if not used
- `find_recent_swing()` - Remove if not used

**How to check if a function is used:**
```bash
# In your project directory
grep -r "kijun_sen" --include="*.py"
grep -r "stochastic_rsi" --include="*.py"
grep -r "calculate_vwap" --include="*.py"
grep -r "fibonacci_retracement" --include="*.py"
grep -r "find_recent_swing" --include="*.py"
```

If grep returns only the function definition (not any calls), it's safe to remove.

---

## SUMMARY: What Should Be Removed

### From `indicators.py`:
- [ ] Calculation of: ema200, stoch_rsi, kijun_sen, vwap, fib levels, pivot_weekly
- [ ] Methods (optional): kijun_sen(), stochastic_rsi(), calculate_vwap(), fibonacci_retracement(), find_recent_swing()

### From `IndicatorsModel`:
- [ ] Columns: ema200, stoch_rsi, kijun_sen, vwap, vwap_distance_percent, fib_level_382, fib_level_618, pivot_weekly, volume_confidence_multiplier, volume_trading_allowed

### From `TechnicalAnalyst` model:
- [ ] Old columns: reasoning, key_signals, recommendation_summary, confidence_breakdown, indicators_analysis, btc_correlation_impact, entry_level, stop_loss, take_profit, timeframe

### From `db_fetcher.py`:
- [ ] Return values for unused indicators

### From `data_manager.py`:
- [ ] Saving of unused indicators

---

## MIGRATION ORDER

1. ✅ Verify implementation works (Phase 1)
2. ✅ Update `indicators.py` - remove calculations (Phase 3)
3. ✅ Update `data_manager.py` - remove saves (Phase 7)
4. ✅ Update `db_fetcher.py` - remove returns (Phase 6)
5. ✅ Test that pipeline still works
6. ✅ Update database models (Phase 4, 5)
7. ✅ Run database migrations
8. ✅ Final verification (Phase 8)

---

## IF SOMETHING BREAKS

1. Check the error message
2. Verify the indicator/column you removed isn't being referenced somewhere else
3. Use `grep -r "column_name" --include="*.py"` to find all references
4. Add back the minimum required code to fix

---

## END OF CLEANUP GUIDE
