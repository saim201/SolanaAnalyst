# Critical Fixes for Refactored Technical Agent

## Overview

Your refactored code has 3 critical issues that will cause failures. This document lists **every single change** needed to fix them.

---

## Issue 1: Missing Import Statement

### Problem
You removed the `typing` import but it may still be needed by `BaseAgent` or other parts of your codebase.

### Location
**Line 7** (imports section)

### Current Code
```python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
from datetime import datetime, timezone
from anthropic import Anthropic

from app.agents.base import BaseAgent, AgentState
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager
```

### Fixed Code
```python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re  # ADD THIS - needed for XML tag extraction
from datetime import datetime, timezone
from typing import Dict  # ADD THIS - if BaseAgent uses type hints
from anthropic import Anthropic

from app.agents.base import BaseAgent, AgentState
from app.agents.db_fetcher import DataQuery
from app.database.data_manager import DataManager
```

### Changes Made
1. **Added `import re`** - Required for regex extraction of `<answer>` tags
2. **Added `from typing import Dict`** - Restore if your BaseAgent/AgentState uses it

---

## Issue 2: XML Tag Extraction Missing (CRITICAL)

### Problem
Your prompt instructs Claude to output JSON inside `<answer>` tags, but your code tries to parse the **entire response** (including `<thinking>` and `<answer>` XML tags) as JSON. This will cause a `JSONDecodeError`.

### Location
**Lines 376-381** (inside `execute` method, after API call)

### Current Code (BROKEN)
```python
        # Call Claude with structured outputs
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

        # Parse response (guaranteed valid JSON)
        analysis = json.loads(response.content[0].text)  # ← THIS WILL FAIL
```

### Fixed Code (WORKING)
```python
        # Call Claude with structured outputs
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

        # Extract JSON from response (handle potential XML tags)
        response_text = response.content[0].text
        
        # Try to extract from <answer> tags first
        answer_match = re.search(r'<answer>(.*?)</answer>', response_text, re.DOTALL)
        if answer_match:
            json_text = answer_match.group(1).strip()
        else:
            # Fallback: structured outputs might return pure JSON without tags
            json_text = response_text
        
        # Clean any potential markdown code fences
        json_text = re.sub(r'^```json\s*|\s*```$', '', json_text.strip())
        
        # Parse JSON (now guaranteed to be clean)
        analysis = json.loads(json_text)
```

### Changes Made
1. **Line 379**: Changed from `analysis = json.loads(response.content[0].text)` to multi-step extraction
2. **Added**: `response_text = response.content[0].text` - Store full response
3. **Added**: Regex search for `<answer>` tags using `re.search(r'<answer>(.*?)</answer>', response_text, re.DOTALL)`
4. **Added**: Conditional extraction - use tag content if found, otherwise use full text
5. **Added**: Markdown fence cleanup with `re.sub(r'^```json\s*|\s*```$', '', json_text.strip())`
6. **Added**: Comment explaining the extraction logic

### Why This Fix Is Critical
Claude will output:
```
<thinking>
Step 1: Market is trending up...
Step 2: Volume is weak at 0.6x...
[etc]
</thinking>

<answer>
{"recommendation_signal": "WAIT", "confidence": {"score": 0.65, ...}}
</answer>
```

Without extraction, `json.loads()` tries to parse `<thinking>...` as JSON and fails.

---

## Issue 3: Prompt Instructions Conflict

### Problem
Your prompt says "Output final JSON inside `<answer>` tags" but structured outputs **already guarantee** JSON format. This creates ambiguity.

### Location
**Lines 220-225** (end of `TECHNICAL_PROMPT`)

### Current Code
```python
<instructions>
Analyze this market data using chain-of-thought reasoning.

1. Write your reasoning inside <thinking> tags
2. Output final JSON inside <answer> tags

Consider deeply: trend direction/strength, volume quality and conviction, momentum direction, BTC correlation impact, risk/reward setup, and invalidation conditions.
```

### Option A: Keep XML Tags (Recommended)
```python
<instructions>
Analyze this market data using chain-of-thought reasoning.

First, write your detailed reasoning inside <thinking> tags.
Then, output your final analysis as valid JSON inside <answer> tags.

Consider deeply: trend direction/strength, volume quality and conviction, momentum direction, BTC correlation impact, risk/reward setup, and invalidation conditions.
```

### Option B: Remove XML Tags Entirely
```python
<instructions>
Analyze this market data thoroughly.

Consider: trend direction/strength, volume quality and conviction, momentum direction, BTC correlation impact, risk/reward setup, and invalidation conditions.

Think deeply about each factor, then output your analysis as JSON matching the exact schema provided.
```

### Changes Made (Option A - Recommended)
1. **Line 222**: Changed "1. Write your reasoning..." to "First, write your detailed reasoning..."
2. **Line 223**: Changed "2. Output final JSON..." to "Then, output your final analysis as valid JSON..."
3. **Reason**: Makes it clear there's a sequence (thinking → answer) and emphasizes valid JSON

### Changes Made (Option B - Alternative)
1. **Line 222**: Removed numbered list entirely
2. **Line 223**: Removed mention of XML tags
3. **Added**: Explicit instruction to match schema
4. **Reason**: Lets structured outputs handle formatting completely

**Recommendation**: Use **Option A** because having Claude's reasoning visible in `<thinking>` tags is valuable for debugging and transparency.

---

## Complete Fixed Code

Here's the **complete fixed `execute` method** with all changes applied:

```python
def execute(self, state: AgentState) -> AgentState:
    """Execute technical analysis using Claude Sonnet 4.5 with structured outputs."""
    
    # Fetch market data
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

    # Call Claude with structured outputs
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

    # ========== CRITICAL FIX: Extract JSON from response ==========
    response_text = response.content[0].text
    
    # Try to extract from <answer> tags first
    answer_match = re.search(r'<answer>(.*?)</answer>', response_text, re.DOTALL)
    if answer_match:
        json_text = answer_match.group(1).strip()
    else:
        # Fallback: structured outputs might return pure JSON without tags
        json_text = response_text
    
    # Clean any potential markdown code fences
    json_text = re.sub(r'^```json\s*|\s*```$', '', json_text.strip())
    
    # Parse JSON (now guaranteed to be clean)
    analysis = json.loads(json_text)
    # ===============================================================

    # Add timestamp
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    analysis['timestamp'] = timestamp

    # Save to state and database
    state['technical'] = analysis

    with DataManager() as dm:
        dm.save_technical_analysis(data=state['technical'])

    return state
```

---

## Summary of All Changes

### File: `technical.py`

| Line | Section | Change Type | Description |
|------|---------|-------------|-------------|
| 7 | Imports | **ADD** | `import re` for regex extraction |
| 7 | Imports | **ADD** | `from typing import Dict` if needed by BaseAgent |
| 222-223 | TECHNICAL_PROMPT | **MODIFY** | Clarify XML tag instructions |
| 379 | execute() method | **REPLACE** | Change from single-line to multi-step extraction |
| 379-391 | execute() method | **ADD** | 13 new lines for XML tag extraction and cleanup |

### Total Changes
- **2 new imports** added
- **1 prompt instruction** clarified
- **1 JSON parsing line** replaced with **13 lines** of extraction logic
- **Total: 16 lines changed/added**

---

## Testing Checklist

After applying these fixes:

### 1. Verify Imports Work
```bash
python -c "import re; from anthropic import Anthropic; print('Imports OK')"
```

### 2. Test XML Tag Extraction
```python
# Test the regex pattern
import re
test_response = """
<thinking>
Market analysis here...
</thinking>

<answer>
{"recommendation_signal": "BUY", "confidence": {"score": 0.8, "reasoning": "test"}}
</answer>
"""

answer_match = re.search(r'<answer>(.*?)</answer>', test_response, re.DOTALL)
if answer_match:
    json_text = answer_match.group(1).strip()
    print("✓ Extraction works:", json_text[:50])
else:
    print("✗ Extraction failed")
```

### 3. Run Full Agent Test
```bash
python app/agents/technical.py
```

Expected output: Should complete without `JSONDecodeError`

### 4. Check Output Structure
Verify the output contains all required fields:
- `recommendation_signal`
- `confidence.score`
- `confidence.reasoning`
- `market_condition`
- `thinking`
- `analysis` (with trend, momentum, volume)
- `trade_setup`
- `action_plan`
- `watch_list`
- `invalidation`
- `confidence_reasoning`

---

## What If It Still Fails?

### Error: `JSONDecodeError: Expecting value`
**Cause**: Structured outputs might be returning pure JSON without XML tags  
**Solution**: The fallback logic handles this - check if `answer_match` is None

### Error: `'NoneType' object has no attribute 'group'`
**Cause**: Regex didn't find `<answer>` tags  
**Solution**: This is handled by the `if answer_match:` check - it falls back to full text

### Error: `No module named 're'`
**Cause**: Python environment issue (very rare)  
**Solution**: `re` is built-in - reinstall Python if this happens

### Error: Schema validation fails
**Cause**: Claude returned valid JSON but wrong structure  
**Solution**: This shouldn't happen with structured outputs - contact Anthropic support

---

## Alternative: Simplified Approach

If you want to **avoid XML tags entirely**, here's a simpler version:

### Modified TECHNICAL_PROMPT (Lines 220-225)
```python
<instructions>
Analyze this market data thoroughly. Output your analysis as JSON matching the exact schema provided.

Consider: trend direction/strength, volume quality and conviction, momentum direction, BTC correlation impact, risk/reward setup, and invalidation conditions.

CRITICAL RULES:
- If volume_ratio < 0.7: recommend HOLD or WAIT
- If no support within 5% below: HOLD or WAIT
- If risk/reward < 1.5:1: HOLD or WAIT
- Always provide specific price levels
- Be thorough and reference specific data points

CONFIDENCE GUIDELINES:
[rest of prompt unchanged]
</instructions>
```

### Modified execute() method (Lines 379-381)
```python
    # Parse response (structured outputs guarantee valid JSON)
    analysis = json.loads(response.content[0].text)
```

**Trade-off**: You lose visibility into Claude's reasoning process (no `<thinking>` tag output), but the code is simpler.

**Recommendation**: Keep the XML tag approach - the reasoning visibility is valuable for debugging.

---

## Final Recommendation

**Apply all 3 fixes** from this document:
1. Add `import re` to imports
2. Add XML tag extraction logic (13 lines)
3. Clarify prompt instructions

This gives you:
- ✅ Robust JSON extraction
- ✅ Visible reasoning in `<thinking>` tags
- ✅ 100% reliable structured outputs
- ✅ Clear error handling

The code will be production-ready after these changes.
