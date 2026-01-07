# 01 - Technical Agent Refactor

## Current Problems

### ❌ Problem 1: Overly Complex Confidence Structure
```python
# Current output:
"confidence": {
    "analysis_confidence": 0.85,
    "setup_quality": 0.65,
    "interpretation": "High confidence in analysis, good trade setup"
}
```

**Issues**:
- Two separate scores confuse users - which one matters?
- "setup_quality" is jargon - what does 0.65 mean?
- "interpretation" is too generic - doesn't explain the WHY with data

### ❌ Problem 2: Redundant `summary` Field
```python
"summary": "Strong bullish setup with volume confirmation...",
"confidence": {
    "interpretation": "High confidence in analysis, good trade setup"
}
```

**Issue**: We're saying the same thing twice. We also have `thinking` for chain-of-thought.

### ❌ Problem 3: Confidence Reasoning Lacks Specificity

**Current example**:
> "High confidence in WAIT recommendation backed by clear overbought RSI at 78.5, insufficient volume conviction, and significant BTC headwind with 0.94 correlation."

**Problem**: While this mentions data, it reads like a list. It doesn't paint a picture of WHY these factors matter or tell the story.

---

## Solutions

### ✅ Solution 1: Simplify Confidence to Single Score + Reasoning

**Remove**:
- `analysis_confidence`
- `setup_quality`
- `interpretation`

**Replace with**:
```python
"confidence": {
    "score": 0.75,
    "reasoning": "2-3 sentences with specific data that paint a picture"
}
```

### ✅ Solution 2: Remove `summary` Field Entirely

The `confidence.reasoning` serves as the summary. We don't need both.

### ✅ Solution 3: Write Better Confidence Reasoning

**Rules**:
1. **Paint a picture** - tell the story of what's happening
2. **Use specific data** - cite actual numbers (volume ratio, RSI, prices)
3. **Natural language** - write like you're explaining to a friend
4. **Connect the dots** - show HOW the data leads to the recommendation

**Template**:
```
"[Market story with specific price/trend]. [Volume/momentum observation with numbers]. [Risk/reward or key factor with specific level]."
```

---

## Code Changes Required

### 📝 Change 1: Update Confidence Guidelines in Prompt

**Location**: `technical.py` → `TECHNICAL_PROMPT` → `<confidence_guidelines>` section

**Current**:
```
## Analysis Confidence (0.70-0.95)
How confident are you in this ANALYSIS (not the trade)?

## Setup Quality (0.0-1.0)
How good is the TRADE SETUP (if someone were to trade)?

## Interpretation
Explain WHY these confidence levels with SPECIFIC data
```

**Replace with**:
```
## Confidence Score (0.0-1.0)
How confident are you in this recommendation overall?

- 0.80-1.00: Very high confidence, strong conviction
- 0.65-0.79: High confidence, good setup
- 0.50-0.64: Moderate confidence, acceptable but watch closely
- 0.35-0.49: Low confidence, edge is unclear
- 0.00-0.34: Very low confidence, avoid trading

## Confidence Reasoning (CRITICAL)
Write 2-3 sentences that paint a picture of WHY this recommendation:
- ✅ Include SPECIFIC DATA (volume ratio, RSI values, support/resistance prices, days since volume spike)
- ✅ Tell the STORY of what's happening in the market
- ✅ Connect the dots - show HOW the data leads to your recommendation
- ✅ Use NATURAL language like explaining to a trader friend
- ❌ Don't just list facts robotically
- ❌ Don't use vague phrases like "indicators look good"

**Examples of GOOD reasoning**:

"High confidence (0.82) in this BUY - price broke above EMA50 at $145 with volume surging to 1.8x average, confirming institutional interest. RSI at 66 is healthy (not overbought), and the $142 support gives us a clean 3.2:1 risk/reward setup for a 3-5 day swing."

"Strong confidence (0.85) in WAIT despite bullish momentum - volume has been dead at 0.56x average for 43 straight days with no spike, making this rally fragile. Combine that with bearish BTC correlation (0.92) and testing resistance at $144.93, there's no edge here until volume returns."

"Moderate confidence (0.68) for this HOLD - we're in a tight $135-137 range with declining volume (0.82x), suggesting accumulation before next move. MACD showing bullish divergence hints upside potential, but need confirmation above $138 with volume >1.5x to commit capital."

**Examples of BAD reasoning** ❌:

"High confidence because multiple indicators align and setup quality is good."
→ No specific data, vague, doesn't explain WHY

"Volume is low and RSI is overbought, creating uncertainty."
→ Just listing observations, not connecting to recommendation

"The technical setup shows 0.72 confidence with acceptable risk/reward."
→ Circular logic - explaining confidence score with confidence score
```

### 📝 Change 2: Update Output Format Section

**Location**: `technical.py` → `TECHNICAL_PROMPT` → `### OUTPUT FORMAT`

**Find this section**:
```json
"confidence": {
  "analysis_confidence": 0.85,
  "setup_quality": 0.72,
  "interpretation": "High confidence in analysis, good trade setup"
}
```

**Replace with**:
```json
"confidence": {
  "score": 0.75,
  "reasoning": "Write 2-3 sentences painting a clear picture: [Market story with prices/trend] → [Volume/momentum with specific numbers] → [Risk/reward or key factor]. Be specific and natural."
}
```

### 📝 Change 3: Remove `summary` Field from Output

**Location**: `technical.py` → `TECHNICAL_PROMPT` → JSON output format

**Remove**:
```json
"summary": "2-3 sentences: What's happening and what to do. Be specific and actionable.",
```

**Why**: The `confidence.reasoning` now serves this purpose.

### 📝 Change 4: Update Parsing Logic

**Location**: `technical.py` → `TechnicalAgent.execute()` method → `try` block (around line 330-380)

**Find this code**:
```python
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
```

**Replace with**:
```python
confidence = analysis.get('confidence', {})

# Validate confidence structure
if not isinstance(confidence, dict):
    # Fallback if confidence is not a dict
    confidence = {
        'score': 0.5,
        'reasoning': 'Invalid confidence format - using default'
    }
elif 'score' not in confidence:
    # Backward compatibility: convert old nested structure
    if 'setup_quality' in confidence:
        score = float(confidence.get('setup_quality', 0.5))
    elif 'analysis_confidence' in confidence:
        score = float(confidence.get('analysis_confidence', 0.5))
    else:
        score = 0.5
    
    reasoning = confidence.get('interpretation', 'Converted from old format')
    
    confidence = {
        'score': score,
        'reasoning': reasoning
    }

# Ensure score is valid (0.0 - 1.0)
confidence['score'] = max(0.0, min(1.0, float(confidence.get('score', 0.5))))

# Ensure reasoning exists and is non-empty
if not confidence.get('reasoning') or not isinstance(confidence['reasoning'], str):
    confidence['reasoning'] = 'No reasoning provided'
```

### 📝 Change 5: Update Fallback Error Handling

**Location**: `technical.py` → `except` block (around line 385-420)

**Find**:
```python
state['technical'] = {
    'timestamp': timestamp,
    'recommendation_signal': 'HOLD',
    'confidence': {
        'analysis_confidence': 0.5,
        'setup_quality': 0.0,
        'interpretation': f'Analysis error: {str(e)[:50]}'
    },
    # ... rest
}
```

**Replace with**:
```python
state['technical'] = {
    'timestamp': timestamp,
    'recommendation_signal': 'HOLD',
    'confidence': {
        'score': 0.3,
        'reasoning': f'Technical analysis failed - {str(e)[:100]}. Using HOLD as safe default until issue is resolved.'
    },
    # ... rest
}
```

### 📝 Change 6: Update System Prompt Reminder

**Location**: `technical.py` → `SYSTEM_PROMPT`

**Add this paragraph at the end**:
```
CRITICAL: Your confidence.reasoning must paint a clear picture with specific data. Don't just list facts - tell the story of what's happening and why it matters. A trader should read it and immediately understand your conviction level and the key factors driving it.
```

---

## Updated JSON Output Schema

```json
{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",
  "market_condition": "TRENDING|RANGING|VOLATILE|QUIET",
  "confidence": {
    "score": 0.75,
    "reasoning": "Price broke above EMA50 at $145 with volume surging to 1.8x average, confirming institutional interest after 45 days of dead volume. RSI at 66 (healthy, not overbought) plus clean support at $142 creates a 3.2:1 risk/reward setup - textbook swing trade opportunity."
  },
  "timestamp": "2026-01-06T12:34:56Z",
  
  "thinking": "MARKET STORY\n...\n\nVOLUME ASSESSMENT\n...",
  
  "analysis": {
    "trend": {
      "direction": "BULLISH",
      "strength": "STRONG",
      "detail": "Uptrend confirmed by price above EMA20 ($133), rallied 9% from $123 to $134. However, testing EMA50 resistance with weak volume (0.56x) suggests fragility."
    },
    "momentum": { ... },
    "volume": { ... }
  },
  
  "trade_setup": {
    "viability": "VALID",
    "entry": 145.50,
    "stop_loss": 142.00,
    "take_profit": 155.00,
    "risk_reward": 3.2,
    "support": 142.50,
    "resistance": 145.20,
    "current_price": 145.50,
    "timeframe": "3-5 days"
  },
  
  "action_plan": { ... },
  "watch_list": { ... },
  "invalidation": [ ... ],
  "confidence_reasoning": { ... }
}
```

**Note**: The `confidence_reasoning` object at the bottom is DIFFERENT from the top-level `confidence.reasoning`. This stays as is (it has `supporting` and `concerns` fields for detailed breakdown).

---

## Examples: Before & After

### Example 1: WAIT Recommendation

**❌ BEFORE (Generic)**:
```json
"confidence": {
  "analysis_confidence": 0.85,
  "setup_quality": 0.25,
  "interpretation": "High confidence in analysis, poor setup quality"
},
"summary": "SOL showing bullish momentum but volume too low to trust."
```

**✅ AFTER (Specific + Story)**:
```json
"confidence": {
  "score": 0.32,
  "reasoning": "Despite price climbing from $122 to $134 (9% rally), volume is catastrophically dead at 0.56x average with no spike in 43 days - institutions aren't participating. Add bearish BTC correlation (0.92) while BTC is down 4.3%, and this rally is built on quicksand. Clear WAIT until volume confirms."
}
```

### Example 2: BUY Recommendation

**❌ BEFORE (Vague)**:
```json
"confidence": {
  "analysis_confidence": 0.88,
  "setup_quality": 0.75,
  "interpretation": "Strong setup with good risk/reward"
},
"summary": "Bullish breakout with volume confirmation and strong momentum."
```

**✅ AFTER (Paints Picture)**:
```json
"confidence": {
  "score": 0.82,
  "reasoning": "Clean breakout above $145 EMA50 resistance with volume exploding to 1.8x average - the first real institutional participation in 6 weeks. RSI at 66 leaves room to run, and tight stop at $142 gives us 3.2:1 risk/reward to $155 target. This is the setup we've been waiting for."
}
```

### Example 3: HOLD Recommendation

**❌ BEFORE (Lists Facts)**:
```json
"confidence": {
  "analysis_confidence": 0.72,
  "setup_quality": 0.55,
  "interpretation": "Moderate confidence, mixed signals"
},
"summary": "Range-bound with declining volume. MACD shows divergence."
```

**✅ AFTER (Tells Story)**:
```json
"confidence": {
  "score": 0.61,
  "reasoning": "Stuck in tight $135-137 consolidation for 8 days with volume fading to 0.82x (below average but not dead). MACD histogram showing bullish divergence hints at coiling energy, but needs breakout above $138 with volume >1.5x to confirm - until then, HOLD and watch."
}
```

---

## Validation Checklist

Before submitting changes, verify:

### ✅ Schema
- [ ] `confidence` is now `{score, reasoning}` (not nested object)
- [ ] `confidence.score` is 0.0-1.0 float
- [ ] `confidence.reasoning` is 2-3 sentences
- [ ] No `summary` field exists
- [ ] All other fields remain unchanged

### ✅ Transparency Test
Read 3 sample outputs and ask:
- [ ] Does `confidence.reasoning` cite SPECIFIC data (volume ratios, RSI values, prices)?
- [ ] Does it PAINT A PICTURE (tell story, not list facts)?
- [ ] Is it NATURAL language (readable by non-technical trader)?
- [ ] Can I understand the conviction level in 10 seconds?

### ✅ Code Quality
- [ ] Parsing logic handles both new and old format (backward compatibility)
- [ ] Fallback error handling uses new structure
- [ ] Prompt clearly instructs LLM on new format
- [ ] Examples in prompt show good vs bad reasoning

### ✅ Testing
Test with these scenarios:
- [ ] High confidence BUY (volume spike + breakout)
- [ ] Low confidence WAIT (dead volume)
- [ ] Moderate confidence HOLD (consolidation)
- [ ] Error case (parsing failure → fallback)

---

## Implementation Steps

1. **Backup current code** - Save `technical.py` before changes
2. **Update prompt** - Modify confidence guidelines and output format
3. **Update parsing** - Change parsing logic for new confidence structure
4. **Update fallback** - Change error handling for new structure
5. **Test with live data** - Run agent and verify output quality
6. **Validate reasoning** - Check that reasoning is specific and paints picture
7. **Commit changes** - If validation passes

---

## Notes for Implementation

- The `thinking` field stays as-is (chain-of-thought reasoning)
- The `confidence_reasoning` object at bottom stays as-is (detailed breakdown)
- Only the top-level `confidence` object changes
- All other fields (analysis, trade_setup, watch_list, etc.) remain unchanged
- This is a **minimal, focused refactor** - only fixing confidence structure

**Estimated Time**: 30-45 minutes  
**Risk Level**: Low (backward compatibility maintained)  
**Testing Required**: Yes (run with live data before deploying)
