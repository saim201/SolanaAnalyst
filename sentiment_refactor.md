# 02 - Sentiment Agent Refactor

## Current Problems

### ❌ Problem 1: Wrong `market_condition` Output
```python
# Current: Sentiment agent doesn't output market_condition at all
# Or if it does, it's inconsistent
```

**Issue**: Sentiment agent should output its view of market sentiment direction (BULLISH/BEARISH/NEUTRAL), not technical states like "TRENDING".

### ❌ Problem 2: Complex Nested Confidence Structure
```python
# Current output:
"confidence": {
    "analysis_confidence": 0.80,
    "signal_strength": 0.62,
    "interpretation": "High confidence in analysis, moderate bullish signal"
}
```

**Issues**:
- Two scores confuse users - which matters?
- "signal_strength" vs "analysis_confidence" - what's the difference?
- "interpretation" is too generic

### ❌ Problem 3: Redundant `summary` Field
```python
"summary": "News presents a cautiously bullish 0.62 sentiment. CME futures and Ondo Finance partnerships...",
"confidence": {
    "interpretation": "High confidence in analysis, moderate bullish signal"
}
```

**Issue**: Saying the same thing twice. We have `thinking` for details.

### ❌ Problem 4: Confusing Nested Keys
```python
"news_sentiment": {
    "score": 0.62,
    "label": "SLIGHTLY_BULLISH",
    "catalysts_count": 2,
    "risks_count": 1
}
```

**Issue**: Why is this nested? It should be flattened or renamed for clarity.

### ❌ Problem 5: `signal` vs `recommendation_signal` Confusion
```python
"signal": "SLIGHTLY_BULLISH",
"recommendation_signal": "HOLD"
```

**Issue**: Two signals? Which one is the actual recommendation? This is confusing.

### ❌ Problem 6: Generic Confidence Reasoning
**Current example**:
> "High confidence in bullish sentiment analysis"

**Problem**: Vague. Doesn't cite specific CFGI scores, news titles, dates, or explain WHY bullish.

### ❌ Problem 7: `market_fear_greed` Naming
```python
"market_fear_greed": {
    "score": 55,
    "classification": "Neutral"
}
```

**Issue**: Should be renamed to `fear_greed_index` for clarity (CFGI = Crypto Fear & Greed Index).

---

## Solutions

### ✅ Solution 1: Add `market_condition` = Sentiment Direction

Output one of: `BULLISH` | `BEARISH` | `NEUTRAL`

This represents the sentiment agent's view of market mood based on news + CFGI.

### ✅ Solution 2: Simplify Confidence Structure

**Remove**:
- `analysis_confidence`
- `signal_strength`
- `interpretation`

**Replace with**:
```python
"confidence": {
    "score": 0.68,
    "reasoning": "CFGI at 66 (Greed) signals retail excitement, but whale caution (32 score) creates tension. Morgan Stanley ETF filing (Jan 6) is genuine institutional catalyst from reputable source, offsetting memecoin perception risks - moderate bullish edge with 68% confidence."
}
```

### ✅ Solution 3: Remove `summary` Field

The `confidence.reasoning` serves as the summary.

### ✅ Solution 4: Flatten and Clarify Keys

**Remove**: Nested `news_sentiment` object

**Add top-level**:
```python
"sentiment_score": 0.68,
"sentiment_label": "CAUTIOUSLY_BULLISH",
"positive_catalysts": 3,
"negative_risks": 1
```

### ✅ Solution 5: Keep Only `recommendation_signal`

**Remove**: `signal` field (it's redundant)

**Keep**: `recommendation_signal` (BUY/SELL/HOLD/WAIT)

The `sentiment_label` shows the sentiment direction, `recommendation_signal` shows the trading action.

### ✅ Solution 6: Write Better Confidence Reasoning

**Rules**:
1. Cite specific CFGI score and what it means
2. Name actual news events with dates
3. Mention source credibility (CoinDesk, official, questionable)
4. Connect dots between CFGI + news → recommendation

### ✅ Solution 7: Rename to `fear_greed_index`

More descriptive than `market_fear_greed`.

---

## Code Changes Required

### 📝 Change 1: Update System Prompt

**Location**: `sentiment.py` → `SENTIMENT_SYSTEM_PROMPT`

**Add to end**:
```
CRITICAL OUTPUT REQUIREMENTS:
- market_condition: Your sentiment view (BULLISH/BEARISH/NEUTRAL)
- confidence.reasoning: Must cite CFGI score, specific news titles/dates, source credibility. Paint a picture - don't just list facts. Tell the story of what sentiment is showing.
- Remove 'summary' field - confidence.reasoning serves this purpose
- Keep output flat and scannable
```

### 📝 Change 2: Update Confidence Guidelines

**Location**: `sentiment.py` → `SENTIMENT_PROMPT` → `<confidence_guidelines>` section

**Replace entire section with**:
```
<confidence_guidelines>
## Confidence Score (0.0-1.0)
How confident are you in this sentiment-based recommendation?

- 0.80-1.00: Very strong sentiment signal, multiple credible sources
- 0.65-0.79: Strong signal, good source quality
- 0.50-0.64: Moderate signal, mixed or aging news
- 0.35-0.49: Weak signal, conflicting data or questionable sources
- 0.00-0.34: No clear signal, noise only

## Confidence Reasoning (CRITICAL)
Write 2-3 sentences that paint the sentiment picture:

✅ **Must include**:
- CFGI score and what it means (e.g., "CFGI at 66 (Greed)")
- Specific news titles and dates (e.g., "Morgan Stanley ETF filing on Jan 6")
- Source credibility (e.g., "from reputable CoinDesk")
- How CFGI + news combine to create edge

✅ **Natural storytelling** - connect the dots, don't just list
❌ **No vague phrases** like "sentiment is positive"
❌ **No listing** without context

**GOOD Examples**:

"High confidence (0.82) - CFGI at 72 (Greed) but justified by genuine catalysts: Morgan Stanley ETF filing (Jan 6, CoinDesk) and Ondo Finance tokenization partnership (Dec 24, official). Retail excitement backed by institutional validation creates strong bullish edge, though brief stablecoin depeg adds minor caution."

"Low confidence (0.38) despite CFGI showing Fear at 28 - all recent news is 5+ days old with no fresh catalysts. Whale accumulation mentioned on Jan 1 (Santiment) lacks volume confirmation from technicals. Sentiment signal exists but stale data means edge has likely faded."

"Strong confidence (0.78) in BEARISH call - CFGI hit Extreme Greed at 84 (contrarian sell signal) while key risk flag emerged: Solana network outage (2 hours on Dec 30, verified by official sources). Euphoric retail positioning into reliability concerns creates high-probability reversal setup."

**BAD Examples** ❌:

"Bullish sentiment from positive news and good CFGI score"
→ No specifics, no dates, doesn't paint picture

"Confidence is high because multiple factors align"
→ Generic, could apply to anything

"News sentiment at 0.68 with CFGI showing greed"
→ Just stating data, not explaining WHY it matters
</confidence_guidelines>
```

### 📝 Change 3: Update Output Format in Prompt

**Location**: `sentiment.py` → `SENTIMENT_PROMPT` → `### OUTPUT FORMAT`

**Replace JSON structure with**:
```json
{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",
  
  "market_condition": "BULLISH|BEARISH|NEUTRAL",
  
  "confidence": {
    "score": 0.68,
    "reasoning": "Write 2-3 sentences: [CFGI score + meaning] → [Specific news with dates/sources] → [How they combine for edge]. Be specific and tell the story."
  },
  
  "timestamp": "2026-01-06T12:34:56Z",
  
  "fear_greed_index": {
    "score": 66,
    "classification": "Greed",
    "social": 96,
    "whales": 32,
    "trends": 88,
    "interpretation": "Retail excitement high but whale caution suggests potential pullback"
  },
  
  "sentiment_score": 0.68,
  "sentiment_label": "CAUTIOUSLY_BULLISH",
  "positive_catalysts": 3,
  "negative_risks": 1,
  
  "key_events": [
    {
      "title": "Morgan Stanley Files Solana ETF",
      "date": "2026-01-06",
      "impact": "BULLISH",
      "source": "CoinDesk",
      "url": "https://..."
    }
  ],
  
  "risk_flags": [
    "Brief stablecoin depeg on DEXs",
    "Memecoin perception challenge"
  ],
  
  "what_to_watch": [
    "Morgan Stanley ETF approval timeline",
    "Solana RWA ecosystem development"
  ],
  
  "invalidation": "Significant regulatory action against Solana or prolonged network instability",
  
  "suggested_timeframe": "3-5 days"
}
```

**Key changes**:
- Added `market_condition` field
- Simplified `confidence` to `{score, reasoning}`
- Removed `summary` field
- Renamed `market_fear_greed` → `fear_greed_index`
- Flattened `news_sentiment.*` to top-level `sentiment_*`
- Removed `signal` field (only `recommendation_signal` remains)

### 📝 Change 4: Update Critical Rules Section

**Location**: `sentiment.py` → `SENTIMENT_PROMPT` → `<critical_rules>`

**Replace rule #6 and #7 with**:
```
6. Valid sentiment_label values: STRONG_BULLISH, BULLISH, SLIGHTLY_BULLISH, NEUTRAL, SLIGHTLY_BEARISH, BEARISH, STRONG_BEARISH

7. market_condition must be: BULLISH (optimistic sentiment), BEARISH (pessimistic sentiment), or NEUTRAL (unclear/mixed sentiment)

8. recommendation_signal must be: BUY (strong bullish + catalysts), SELL (strong bearish + risks), HOLD (moderate signal, no urgency), WAIT (conflicting or stale data)

9. confidence is simplified: {score: 0.0-1.0, reasoning: "2-3 sentences with CFGI score, news titles/dates, source credibility"}

10. Remove 'signal' field - only output 'recommendation_signal'

11. Rename 'market_fear_greed' → 'fear_greed_index' for clarity

12. Flatten news_sentiment.* to top-level sentiment_score, sentiment_label, positive_catalysts, negative_risks
```

### 📝 Change 5: Update Parsing Logic

**Location**: `sentiment.py` → `SentimentAgent.execute()` → `try` block

**Find and replace confidence parsing**:
```python
# OLD CODE (remove):
# confidence = sentiment_data.get('confidence', {})
# if isinstance(confidence, (int, float)):
#     confidence = {
#         'analysis_confidence': 0.75,
#         'signal_strength': float(confidence),
#         'interpretation': f'Legacy format: {confidence:.0%} confidence'
#     }
# ...

# NEW CODE:
confidence = sentiment_data.get('confidence', {})

# Validate confidence structure
if not isinstance(confidence, dict):
    confidence = {
        'score': 0.5,
        'reasoning': 'Invalid confidence format - using default'
    }
elif 'score' not in confidence:
    # Backward compatibility: convert old nested structure
    if 'signal_strength' in confidence:
        score = float(confidence.get('signal_strength', 0.5))
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

# Ensure reasoning exists
if not confidence.get('reasoning') or not isinstance(confidence['reasoning'], str):
    confidence['reasoning'] = 'No reasoning provided'

sentiment_data['confidence'] = confidence

# Ensure market_condition exists
if 'market_condition' not in sentiment_data:
    # Derive from sentiment_label if missing
    label = sentiment_data.get('sentiment_label', 'NEUTRAL')
    if 'BULLISH' in label:
        sentiment_data['market_condition'] = 'BULLISH'
    elif 'BEARISH' in label:
        sentiment_data['market_condition'] = 'BEARISH'
    else:
        sentiment_data['market_condition'] = 'NEUTRAL'

# Remove 'signal' field if it exists (only recommendation_signal should remain)
if 'signal' in sentiment_data:
    del sentiment_data['signal']
```

### 📝 Change 6: Update Fallback Error Handling

**Location**: `sentiment.py` → `except` block

**Replace fallback structure**:
```python
state['sentiment'] = {
    "recommendation_signal": "HOLD",
    "market_condition": "NEUTRAL",
    "confidence": {
        "score": 0.3,
        "reasoning": f"Sentiment analysis failed due to parsing error: {str(e)[:100]}. Defaulting to HOLD with low confidence until resolved."
    },
    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "fear_greed_index": {
        "score": formatted_data["cfgi_score"],
        "classification": formatted_data["cfgi_classification"],
        "social": None,
        "whales": None,
        "trends": None,
        "interpretation": "Unable to analyze CFGI data due to error"
    },
    "sentiment_score": 0.5,
    "sentiment_label": "NEUTRAL",
    "positive_catalysts": 0,
    "negative_risks": 0,
    "key_events": [],
    "risk_flags": ["Parsing error occurred"],
    "what_to_watch": [],
    "invalidation": "N/A",
    "suggested_timeframe": "N/A",
    "thinking": f"Error: {str(e)}"
}
```

### 📝 Change 7: Update Format Function (Optional Cleanup)

**Location**: `sentiment.py` → `format_for_sentiment_agent()` function

**No major changes needed**, but ensure it returns data in a way that supports the new prompt. Already looks good.

---

## Updated JSON Output Schema

```json
{
  "recommendation_signal": "HOLD",
  "market_condition": "BULLISH",
  "confidence": {
    "score": 0.68,
    "reasoning": "CFGI at 66 (Greed) signals retail excitement, but whale caution at 32 creates tension. Morgan Stanley ETF filing (Jan 6, CoinDesk) is genuine institutional catalyst, offsetting memecoin risks. Moderate bullish edge exists but not strong enough for immediate BUY - HOLD and monitor."
  },
  "timestamp": "2026-01-06T12:34:56Z",
  
  "fear_greed_index": {
    "score": 66,
    "classification": "Greed",
    "social": 96,
    "whales": 32,
    "trends": 88,
    "interpretation": "Retail excitement high but whale caution suggests potential pullback"
  },
  
  "sentiment_score": 0.68,
  "sentiment_label": "CAUTIOUSLY_BULLISH",
  "positive_catalysts": 3,
  "negative_risks": 1,
  
  "key_events": [
    {
      "title": "Morgan Stanley Files Solana ETF",
      "date": "2026-01-06",
      "impact": "BULLISH",
      "source": "CoinDesk",
      "url": "https://www.coindesk.com/..."
    },
    {
      "title": "Ondo Finance Tokenization on Solana",
      "date": "2025-12-24",
      "impact": "BULLISH",
      "source": "CoinTelegraph",
      "url": "https://..."
    }
  ],
  
  "risk_flags": [
    "Brief stablecoin depeg on DEXs",
    "Memecoin perception challenge"
  ],
  
  "what_to_watch": [
    "Morgan Stanley ETF approval process",
    "Solana RWA ecosystem development",
    "Network stability metrics"
  ],
  
  "invalidation": "Significant regulatory action against Solana or prolonged network instability",
  
  "suggested_timeframe": "3-5 days",
  
  "thinking": "STEP 1: CFGI INTERPRETATION\n..."
}
```

---

## Examples: Before & After

### Example 1: Bullish Sentiment

**❌ BEFORE (Generic + Nested)**:
```json
{
  "signal": "SLIGHTLY_BULLISH",
  "recommendation_signal": "HOLD",
  "confidence": {
    "analysis_confidence": 0.85,
    "signal_strength": 0.65,
    "interpretation": "High confidence in bullish sentiment analysis"
  },
  "summary": "Solana shows promising institutional momentum with RWA expansion.",
  "market_fear_greed": {
    "score": 55,
    "classification": "Neutral"
  },
  "news_sentiment": {
    "score": 0.68,
    "label": "CAUTIOUSLY_BULLISH"
  }
}
```

**✅ AFTER (Clear + Flat + Story)**:
```json
{
  "recommendation_signal": "HOLD",
  "market_condition": "BULLISH",
  "confidence": {
    "score": 0.68,
    "reasoning": "CFGI at 55 (Neutral) lacks conviction, but fresh institutional catalysts tell the real story: Morgan Stanley ETF filing (Jan 6, CoinDesk) and Ondo Finance tokenization (Dec 24) are genuine moves, not hype. Retail hasn't caught on yet (social 45/100), creating opportunity - HOLD for now as setup develops."
  },
  "fear_greed_index": {
    "score": 55,
    "classification": "Neutral",
    "interpretation": "..."
  },
  "sentiment_score": 0.68,
  "sentiment_label": "CAUTIOUSLY_BULLISH",
  "positive_catalysts": 2,
  "negative_risks": 0
}
```

### Example 2: Bearish Sentiment (Contrarian)

**❌ BEFORE (Vague)**:
```json
{
  "signal": "BEARISH",
  "confidence": {
    "analysis_confidence": 0.78,
    "signal_strength": 0.72,
    "interpretation": "Strong bearish signal from extreme greed"
  },
  "summary": "Extreme greed suggests potential correction ahead."
}
```

**✅ AFTER (Specific + Contrarian Logic)**:
```json
{
  "recommendation_signal": "SELL",
  "market_condition": "BEARISH",
  "confidence": {
    "score": 0.78,
    "reasoning": "CFGI hit Extreme Greed at 84 (contrarian sell signal) right as network outage hit (2 hours on Dec 30, verified official sources). Euphoric retail (social 98/100) piling in while whales exit (26/100) - textbook top pattern. Risk/reward favors taking profits before correction."
  },
  "fear_greed_index": {
    "score": 84,
    "classification": "Extreme Greed"
  },
  "sentiment_score": 0.28,
  "sentiment_label": "BEARISH"
}
```

### Example 3: Neutral/Conflicting Sentiment

**❌ BEFORE (Confusing)**:
```json
{
  "signal": "NEUTRAL",
  "recommendation_signal": "WAIT",
  "confidence": {
    "analysis_confidence": 0.65,
    "signal_strength": 0.45,
    "interpretation": "Moderate confidence, mixed signals"
  },
  "summary": "Mixed sentiment with both positive and negative factors."
}
```

**✅ AFTER (Clear Conflict)**:
```json
{
  "recommendation_signal": "WAIT",
  "market_condition": "NEUTRAL",
  "confidence": {
    "score": 0.42,
    "reasoning": "CFGI neutral at 52 but all news is 5+ days old - no fresh catalysts. Morgan Stanley filing mentioned (Dec 30, CoinDesk) but SEC commentary on Jan 3 (Bloomberg) added uncertainty. Stale bullish news vs fresh regulatory questions creates no edge - WAIT for clarity."
  },
  "fear_greed_index": {
    "score": 52,
    "classification": "Neutral"
  },
  "sentiment_score": 0.50,
  "sentiment_label": "NEUTRAL"
}
```

---

## Validation Checklist

### ✅ Schema Compliance
- [ ] Has `recommendation_signal` (BUY/SELL/HOLD/WAIT)
- [ ] Has `market_condition` (BULLISH/BEARISH/NEUTRAL)
- [ ] Has `confidence.score` (0.0-1.0)
- [ ] Has `confidence.reasoning` (2-3 sentences with CFGI + news)
- [ ] Has `timestamp` (ISO 8601)
- [ ] No `signal` field (removed)
- [ ] No `summary` field (removed)
- [ ] Renamed `market_fear_greed` → `fear_greed_index`
- [ ] Flattened `news_sentiment.*` → `sentiment_*`

### ✅ Transparency Test
Read 3 sample outputs and check:
- [ ] Does reasoning cite CFGI score and interpretation?
- [ ] Does reasoning name specific news with dates?
- [ ] Does reasoning mention source credibility?
- [ ] Does reasoning tell a STORY (not just list)?
- [ ] Can I understand the sentiment edge in 10 seconds?

### ✅ Code Quality
- [ ] Parsing handles old nested confidence format (backward compat)
- [ ] Fallback error handling uses new structure
- [ ] Prompt clearly instructs new output format
- [ ] Examples show good storytelling

### ✅ Testing Scenarios
- [ ] Extreme Fear (contrarian buy signal)
- [ ] Extreme Greed (contrarian sell signal)
- [ ] Neutral CFGI with strong news catalyst
- [ ] Stale news (>72 hours old)
- [ ] Conflicting CFGI + news
- [ ] Error case (parsing failure)

---

## Implementation Steps

1. **Backup current code** - Save `sentiment.py`
2. **Update system prompt** - Add output requirements
3. **Update confidence guidelines** - Show good/bad examples
4. **Update output format** - New JSON structure in prompt
5. **Update critical rules** - Clarify field requirements
6. **Update parsing logic** - Handle new + old formats
7. **Update fallback** - Error handling with new structure
8. **Test with live data** - Verify CFGI + news parsing
9. **Validate reasoning** - Check specificity and storytelling
10. **Commit changes**

---

## Key Differences from Technical Agent

1. **Confidence reasoning focuses on**:
   - CFGI score interpretation (contrarian approach)
   - Specific news titles and dates
   - Source credibility (official, reputable, questionable)
   - News age (fresh vs stale)

2. **market_condition is sentiment-based**:
   - BULLISH = optimistic news + fear/neutral CFGI
   - BEARISH = negative news + greed CFGI
   - NEUTRAL = mixed or unclear

3. **Contrarian logic**:
   - Extreme Fear (CFGI <20) → Often bullish
   - Extreme Greed (CFGI >80) → Often bearish

---

## Notes for Implementation

- The `thinking` field stays (chain-of-thought)
- All detailed fields stay (key_events, risk_flags, what_to_watch, etc.)
- Only top-level structure changes for consistency
- Focus is on making sentiment analysis **transparent and actionable**

**Estimated Time**: 45-60 minutes  
**Risk Level**: Low-Medium (more changes than Technical)  
**Testing Required**: Yes (especially CFGI + news integration)
