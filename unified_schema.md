# 00 - Unified Schema for All Agents

## Philosophy: Transparency Through Simplicity

Every agent in TradingMate must output **transparent, actionable, and scannable** analysis. Users should be able to glance at any agent and immediately understand:
1. What the agent recommends (BUY/SELL/HOLD/WAIT)
2. How the agent sees the market (market condition)
3. Why the agent thinks this way (confidence with specific reasoning)

**Core Principle**: Paint a picture with data, don't just list data.

---

## Universal Top-Level Structure

Every agent MUST output these 4 fields at the top level:

```json
{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",
  "market_condition": "<agent-specific interpretation>",
  "confidence": {
    "score": 0.75,
    "reasoning": "2-3 sentences with SPECIFIC DATA painting a clear picture"
  },
  "timestamp": "2026-01-06T12:00:00Z"
}
```

### Field Definitions

#### 1. `recommendation_signal` (required)
**Type**: String enum  
**Values**: `BUY` | `SELL` | `HOLD` | `WAIT`

- **BUY**: Clear bullish setup with acceptable risk
- **SELL**: Clear bearish setup or profit-taking opportunity
- **HOLD**: No strong directional edge, maintain current position
- **WAIT**: Setup exists but conditions not met (volume, confirmation, etc.)

#### 2. `market_condition` (required)
**Type**: String (agent-specific)

Each agent interprets "market condition" through their specialty:

- **Technical Agent**: Chart state
  - Values: `TRENDING` | `RANGING` | `VOLATILE` | `QUIET`
  
- **Sentiment Agent**: Sentiment direction
  - Values: `BULLISH` | `BEARISH` | `NEUTRAL`
  
- **Reflection Agent**: Agent alignment
  - Values: `ALIGNED` | `CONFLICTED` | `MIXED`
  
- **Trader Agent**: Final market stance
  - Values: `BULLISH` | `BEARISH` | `NEUTRAL` | `WAIT`

#### 3. `confidence` (required)
**Type**: Object with 2 fields

```json
"confidence": {
  "score": 0.75,  // 0.0 - 1.0
  "reasoning": "Clear explanation with specific data"
}
```

**`confidence.score`** rules:
- **0.80-1.00**: Very high confidence, strong conviction
- **0.65-0.79**: High confidence, good setup
- **0.50-0.64**: Moderate confidence, acceptable but watch closely
- **0.35-0.49**: Low confidence, edge is unclear
- **0.00-0.34**: Very low confidence, avoid trading

**`confidence.reasoning`** rules (CRITICAL):
- ✅ **Must be 2-3 sentences**
- ✅ **Must include SPECIFIC DATA** (numbers, prices, dates, ratios)
- ✅ **Must paint a picture** - tell a story, don't just list facts
- ✅ **Must be natural language** - readable by non-technical traders
- ❌ **No vague statements** like "indicators look good"
- ❌ **No generic phrases** like "market is showing strength"

**Good Examples**:
```
"High confidence (0.82) driven by volume surge to 1.8x average confirming breakout above $145 resistance, with RSI at healthy 66 (not overbought). The 3.2:1 risk/reward ratio at $142 support makes this a textbook swing trade setup."

"Low confidence (0.32) despite bullish news - volume has been dead at 0.56x average for 43 days straight, and we're testing resistance with bearish BTC correlation (0.92). Even good news can't move price without institutional buying pressure."

"Strong confidence (0.88) in WAIT call - Morgan Stanley ETF filing is genuine institutional catalyst, but RSI is already at 78.5 (overbought) with price 8% above EMA50. Better entry will come on healthy pullback to $135-137 support zone."
```

**Bad Examples** ❌:
```
"Confident because indicators align and trend is good."
→ Problem: No specific data, vague, doesn't paint picture

"The market looks bullish with positive momentum."
→ Problem: Generic, no numbers, could apply to any situation

"Setup quality is high at 0.72 with good risk/reward."
→ Problem: Just stating the score, not explaining WHY
```

#### 4. `timestamp` (required)
**Type**: ISO 8601 string with UTC timezone  
**Example**: `"2026-01-06T12:34:56Z"`

---

## Keys to REMOVE from All Agents

These fields create redundancy and reduce clarity:

### ❌ Remove: `summary`
**Why**: We already have `thinking` (chain-of-thought) and `confidence.reasoning` (concise explanation). A separate summary is redundant.

**Replace with**: Strong `confidence.reasoning` that serves as the summary

### ❌ Remove: Nested confidence objects
**Current problem**:
```json
// Technical has:
"confidence": {
  "analysis_confidence": 0.85,
  "setup_quality": 0.65,      // confusing
  "interpretation": "..."      // redundant
}

// Sentiment has:
"confidence": {
  "analysis_confidence": 0.80,
  "signal_strength": 0.62,     // confusing
  "interpretation": "..."       // redundant
}
```

**Replace with**:
```json
"confidence": {
  "score": 0.75,
  "reasoning": "Clear explanation with data"
}
```

### ❌ Remove: Overly nested structures
**Problem**: JSON structures like `news_sentiment.score` buried 2-3 levels deep

**Solution**: Flatten to 1-2 levels max. If a field is important, bring it up.

---

## Agent-Specific Extensions

Each agent can add specialized fields AFTER the universal top 4, but must follow these rules:

### General Rules:
1. **Max 2 levels of nesting** (except for arrays of objects)
2. **Descriptive key names** - no abbreviations, no jargon
3. **Consistent naming**: use snake_case for all keys
4. **No duplicate information** across keys

### Technical Agent Extensions:
```json
{
  "recommendation_signal": "WAIT",
  "market_condition": "TRENDING",
  "confidence": { "score": 0.85, "reasoning": "..." },
  "timestamp": "...",
  
  // Extensions:
  "analysis": {
    "trend": { "direction": "BULLISH", "strength": "MODERATE", "detail": "..." },
    "momentum": { ... },
    "volume": { ... }
  },
  "trade_setup": {
    "entry": 145.50,
    "stop_loss": 142.00,
    "take_profit": 155.00,
    "risk_reward": 3.2,
    "timeframe": "3-5 days"
  },
  "watch_list": { ... },
  "invalidation": [ ... ]
}
```

### Sentiment Agent Extensions:
```json
{
  "recommendation_signal": "HOLD",
  "market_condition": "BULLISH",
  "confidence": { "score": 0.68, "reasoning": "..." },
  "timestamp": "...",
  
  // Extensions:
  "fear_greed_index": {
    "score": 66,
    "classification": "Greed",
    "interpretation": "..."
  },
  "key_events": [
    {
      "title": "Morgan Stanley Files Solana ETF",
      "date": "2026-01-06",
      "impact": "BULLISH",
      "source": "CoinDesk"
    }
  ],
  "risk_flags": [ ... ],
  "invalidation": "..."
}
```

### Reflection Agent Extensions:
```json
{
  "recommendation_signal": "WAIT",
  "market_condition": "CONFLICTED",
  "confidence": { "score": 0.45, "reasoning": "..." },
  "timestamp": "...",
  
  // Extensions:
  "agent_alignment": {
    "technical_says": "BUY (0.72)",
    "sentiment_says": "BULLISH (0.65)",
    "alignment_score": 0.85,
    "synthesis": "Both agents bullish but Technical sees overbought risk..."
  },
  "blind_spots": {
    "technical_missed": [ ... ],
    "sentiment_missed": [ ... ]
  },
  "primary_risk": "...",
  "monitoring": { ... }
}
```

### Trader Agent Extensions:
```json
{
  "recommendation_signal": "WAIT",
  "market_condition": "NEUTRAL",
  "confidence": { "score": 0.45, "reasoning": "..." },
  "timestamp": "...",
  
  // Extensions:
  "agent_synthesis": {
    "weighted_confidence": 0.45,
    "agreement_summary": "..."
  },
  "execution_plan": {
    "position_size": "0%",
    "entry_timing": "...",
    "timeframe": "Re-evaluate in 3-5 days"
  },
  "risk_management": { ... }
}
```

---

## Validation Checklist

Before committing any agent changes, verify:

### ✅ Structure
- [ ] Has `recommendation_signal` (BUY/SELL/HOLD/WAIT)
- [ ] Has `market_condition` (appropriate for agent type)
- [ ] Has `confidence.score` (0.0-1.0)
- [ ] Has `confidence.reasoning` (2-3 sentences with data)
- [ ] Has `timestamp` (ISO 8601 UTC)
- [ ] No `summary` field
- [ ] No nested confidence objects
- [ ] Max 2 levels of nesting

### ✅ Transparency Test
Read `confidence.reasoning` and ask:
- [ ] Can I understand WHY this recommendation in 10 seconds?
- [ ] Does it cite SPECIFIC data (numbers, dates, prices)?
- [ ] Does it paint a PICTURE or just list facts?
- [ ] Is it NATURAL language (not robotic)?

### ✅ Actionability Test
- [ ] Clear what to DO (entry/exit/wait)
- [ ] Clear what to WATCH (invalidation triggers)
- [ ] Clear WHY this matters (risk/reward)

---

## Implementation Order

1. ✅ Define this unified schema (this document)
2. 🔄 Technical Agent (simplest - just simplify confidence)
3. 🔄 Sentiment Agent (flatten structure, fix market_condition)
4. 🔄 Reflection Agent (add recommendation_signal, fix alignment)
5. 🔄 Trader Agent (complete rewrite to consume new schema)

---

## Notes for Claude Code

When implementing these changes:

1. **Update system prompts** to specify the new output format
2. **Update parsing logic** to handle new structure
3. **Update database schemas** if needed (confidence structure change)
4. **Test with real data** to ensure reasoning is specific and clear
5. **Validate JSON** structure before saving to database

Remember: **Transparency through simplicity**. Every field must earn its place.
