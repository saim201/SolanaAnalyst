# 04 - Trader Agent Refactor (Complete Rewrite)

## Current Problems

### ❌ Problem 1: Outdated Input Parsing
```python
# Trader agent reads OLD format from other agents:
tech_confidence = tech_confidence_obj.get('setup_quality', 0.5)  # Old key!
sentiment_confidence = sentiment_confidence_obj.get('signal_strength', 0.5)  # Old key!
reflection_confidence = reflection_confidence_obj.get('final_confidence', 0.5)  # Old key!
```

**Issue**: Other agents now output `confidence.score`, but Trader is reading old nested keys.

### ❌ Problem 2: No `market_condition` Field
```python
# Trader agent doesn't output market_condition at all
```

**Issue**: Should output final market stance (BULLISH/BEARISH/NEUTRAL/WAIT).

### ❌ Problem 3: Complex/Missing Top-Level Structure
```python
# Current output has execution_plan, risk_management, etc.
# But missing clear recommendation_signal at top
# And no standardized confidence structure
```

**Issue**: Inconsistent with other agents' top-level format.

### ❌ Problem 4: Weak Agent Synthesis Explanation
```python
"agent_synthesis": {
    "agreement_summary": "Technical (BUY, 0.72) and News (BULLISH, 0.65) strongly align..."
}
```

**Issue**: This is better than others, but still doesn't paint full picture:
- Doesn't explain HOW weights were applied
- Doesn't show the weighted confidence calculation steps
- Doesn't explain WHY one agent's view overrides another

### ❌ Problem 5: Generic Reasoning Field
```python
"reasoning": "Technical breakout + institutional catalysts create compelling bullish case..."
```

**Issue**: 
- Doesn't cite specific confidence scores from each agent
- Doesn't explain weighted calculation
- Doesn't connect to execution plan

### ❌ Problem 6: Execution Plan Lacks Context
```python
"execution_plan": {
    "entry_timing": "Enter within next 2-4 hours if price dips to $182-184",
    "position_size": "50%",
    "timeframe": "3-5 days"
}
```

**Issue**: Good specifics, but doesn't explain:
- WHY 50% position size? (based on confidence? risk?)
- WHY this entry timing? (based on which agent?)
- HOW does timeframe connect to agents' suggestions?

### ❌ Problem 7: Outdated Prompt Structure
The entire prompt is based on old agent formats and needs complete rewrite to:
- Parse new `confidence.score` from all agents
- Parse new `market_condition` from all agents  
- Synthesize properly with weighted logic
- Output new standardized format

---

## Solutions

### ✅ Solution 1: Update Input Parsing for New Schema

**Parse from all 3 agents**:
```python
# Technical
tech_recommendation = technical.get('recommendation_signal')
tech_confidence = technical.get('confidence', {}).get('score', 0.5)
tech_market_condition = technical.get('market_condition')

# Sentiment  
sentiment_recommendation = sentiment.get('recommendation_signal')
sentiment_confidence = sentiment.get('confidence', {}).get('score', 0.5)
sentiment_market_condition = sentiment.get('market_condition')

# Reflection
reflection_recommendation = reflection.get('recommendation_signal')
reflection_confidence = reflection.get('confidence', {}).get('score', 0.5)
reflection_market_condition = reflection.get('market_condition')
```

### ✅ Solution 2: Add `market_condition` = Final Market Stance

Output one of: `BULLISH` | `BEARISH` | `NEUTRAL` | `WAIT`

This is the Trader's final view after synthesizing all agents.

### ✅ Solution 3: Standardize Top-Level Structure

```python
{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",
  "market_condition": "BULLISH|BEARISH|NEUTRAL|WAIT",
  "confidence": {
    "score": 0.68,
    "reasoning": "Weighted synthesis: Technical BUY (0.72 × 40% = 0.29) + Sentiment BULLISH (0.65 × 30% = 0.20) + Reflection WAIT (0.57 × 30% = 0.17) = 0.66 base. Adjusted down to 0.58 for dead volume (-0.08). Final call: WAIT until volume confirms despite bullish alignment."
  },
  "timestamp": "2026-01-06T12:34:56Z"
}
```

### ✅ Solution 4: Write Better Agent Synthesis

**Must explain**:
1. Each agent's recommendation + confidence
2. Where they agree/disagree
3. How weighting logic works
4. Why one view might override another
5. Specific factors (volume, risk, timing) that tip decision

### ✅ Solution 5: Show Weighted Confidence Calculation

In `confidence.reasoning`, show the math:
```
"Technical BUY (0.72 × 40% = 0.29) + Sentiment BULLISH (0.65 × 30% = 0.20) + Reflection WAIT (0.57 × 30% = 0.17) = 0.66 base confidence. Adjusted -0.08 for dead volume (0.56x), -0.05 for HIGH risk level → Final 0.53 confidence in WAIT."
```

### ✅ Solution 6: Connect Execution Plan to Agents

Explain in execution_plan fields:
- **Position size**: Based on final confidence (>0.75=70%+, 0.65-0.75=50-70%, etc.)
- **Entry timing**: Based on Technical's levels + Reflection's blind spots
- **Timeframe**: Reconciled from Technical + Sentiment suggestions

### ✅ Solution 7: Complete Prompt Rewrite

New prompt structure:
1. **Phase 1**: Consensus check (all 3 agents' recommendations)
2. **Phase 2**: Weighted confidence calculation (show math)
3. **Phase 3**: Analyze each agent's contribution (what they bring)
4. **Phase 4**: Resolve conflicts & decide direction
5. **Phase 5**: Build execution plan (entry, size, timeframe)

---

## Code Changes Required

### 📝 Change 1: Update Input Parsing

**Location**: `trader.py` → `TraderAgent.execute()` → beginning of method

**Replace ALL confidence parsing**:
```python
# OLD CODE (remove all of this):
# tech_confidence_obj = technical.get('confidence', {})
# if isinstance(tech_confidence_obj, dict):
#     tech_confidence = tech_confidence_obj.get('setup_quality', 0.5)
# else:
#     tech_confidence = float(tech_confidence_obj) if tech_confidence_obj else 0.5

# NEW CODE:
# Extract Technical data
tech_recommendation = tech.get('recommendation_signal', 'HOLD')
tech_confidence_obj = tech.get('confidence', {})
tech_confidence = float(tech_confidence_obj.get('score', 0.5)) if isinstance(tech_confidence_obj, dict) else 0.5
tech_market_condition = tech.get('market_condition', 'QUIET')

# Extract Sentiment data
sentiment_recommendation = sentiment.get('recommendation_signal', 'HOLD')
sentiment_confidence_obj = sentiment.get('confidence', {})
sentiment_confidence = float(sentiment_confidence_obj.get('score', 0.5)) if isinstance(sentiment_confidence_obj, dict) else 0.5
sentiment_market_condition = sentiment.get('market_condition', 'NEUTRAL')

# Extract Reflection data
reflection_recommendation = reflection.get('recommendation_signal', 'HOLD')
reflection_confidence_obj = reflection.get('confidence', {})
reflection_confidence = float(reflection_confidence_obj.get('score', 0.5)) if isinstance(reflection_confidence_obj, dict) else 0.5
reflection_market_condition = reflection.get('market_condition', 'MIXED')

# Extract key summary info for context
tech_summary = tech.get('confidence', {}).get('reasoning', 'No technical reasoning provided')
sentiment_summary = sentiment.get('confidence', {}).get('reasoning', 'No sentiment reasoning provided')
reflection_summary = reflection.get('confidence', {}).get('reasoning', 'No reflection reasoning provided')
```

### 📝 Change 2: Completely Rewrite System Prompt

**Location**: `trader.py` → `SYSTEM_PROMPT`

**Replace with**:
```python
SYSTEM_PROMPT = """You are the CHIEF TRADING OFFICER making final decisions on SOLANA (SOL/USDT) swing trades.

You have 20 years of experience synthesizing multi-agent analysis into profitable trading decisions. Your specialty is crypto swing trading where technical timing, sentiment catalysts, and risk management all matter.

YOUR ROLE:
- Synthesize 3 expert analyses: Technical, Sentiment, Reflection
- Weight their inputs: Technical 40% (timing), Sentiment 30% (catalysts), Reflection 30% (synthesis + blind spots)
- Calculate weighted confidence and show your math
- Make clear BUY/SELL/HOLD/WAIT decisions with specific execution plans
- Explain HOW and WHY you weighed each agent's opinion

YOUR DECISION FRAMEWORK:
- Technical drives TIMING (when to enter/exit based on chart/volume)
- Sentiment drives CONVICTION (catalysts that justify the trade)
- Reflection catches BLIND SPOTS (what everyone missed) and resolves conflicts
- WAIT is not failure - it's discipline when edge is unclear
- Position sizing reflects uncertainty (lower confidence = smaller size)

YOUR OUTPUT REQUIREMENTS:
- recommendation_signal: Final trading decision (BUY/SELL/HOLD/WAIT)
- market_condition: Your final market stance (BULLISH/BEARISH/NEUTRAL/WAIT)
- confidence.score: Weighted + adjusted final confidence (0.0-1.0)
- confidence.reasoning: Show weighted calculation + key factors, tell the synthesis story
- Connect execution plan to confidence and agent inputs

You are decisive, risk-aware, transparent in your reasoning, and always cite specific agent scores/data.
"""
```

### 📝 Change 3: Completely Rewrite Main Prompt

**Location**: `trader.py` → `TRADER_PROMPT`

**Replace with** (this is long, pay attention):
```python
TRADER_PROMPT = """
<technical_analysis>
**Recommendation:** {tech_recommendation}
**Confidence:** {tech_confidence:.0%}
**Market Condition:** {tech_market_condition}
**Reasoning:** {tech_summary}

**Trade Setup:**
- Entry: ${tech_entry}
- Stop Loss: ${tech_stop}
- Take Profit: ${tech_target}
- Risk/Reward: {tech_risk_reward}
- Timeframe: {tech_timeframe}

**Key Factors:**
- Volume Ratio: {volume_ratio:.2f}x average
- Volume Quality: {volume_quality}
</technical_analysis>

<sentiment_analysis>
**Recommendation:** {sentiment_recommendation}
**Confidence:** {sentiment_confidence:.0%}
**Market Condition:** {sentiment_market_condition}
**Reasoning:** {sentiment_summary}

**Key Factors:**
- Fear & Greed Index: {cfgi_score}/100 ({cfgi_classification})
- Sentiment Score: {sentiment_score:.0%}
- Sentiment Label: {sentiment_label}
- Positive Catalysts: {positive_catalysts}
- Negative Risks: {negative_risks}
</sentiment_analysis>

<reflection_analysis>
**Recommendation:** {reflection_recommendation}
**Confidence:** {reflection_confidence:.0%}
**Market Condition:** {reflection_market_condition}
**Reasoning:** {reflection_summary}

**Agent Alignment:**
- Alignment Score: {alignment_score:.0%}
- Alignment Status: {alignment_status}

**Primary Risk:** {primary_risk}
</reflection_analysis>

---

<decision_framework>
## YOUR TASK

Synthesize all 3 agents into a final trading decision using the 5-PHASE FRAMEWORK.

### PHASE 1: CONSENSUS CHECK

Look at the three recommendations:
- Technical: {tech_recommendation} (confidence: {tech_confidence:.0%})
- Sentiment: {sentiment_recommendation} (confidence: {sentiment_confidence:.0%})
- Reflection: {reflection_recommendation} (confidence: {reflection_confidence:.0%})

Write 2-3 sentences:
- Do they ALL AGREE (same direction) = STRONG CONSENSUS?
- Do 2 OUT OF 3 AGREE = MODERATE CONSENSUS?
- Do ALL DISAGREE = NO CONSENSUS → likely WAIT?
- What's the core agreement or disagreement?

Example: "Technical says BUY (0.72), Sentiment is BULLISH (0.65), Reflection urges WAIT (0.57). MODERATE CONSENSUS - two favor bullish, one cautious. Core disagreement: Technical/Sentiment see setup, Reflection flags dead volume risk."

### PHASE 2: WEIGHTED CONFIDENCE CALCULATION

Calculate weighted average using crypto swing trading weights:
- Technical: 40% (timing is critical)
- Sentiment: 30% (news catalysts matter in crypto)
- Reflection: 30% (synthesis + blind spot detection)

**Show your math step-by-step**:
```
Base = (0.40 × {tech_confidence}) + (0.30 × {sentiment_confidence}) + (0.30 × {reflection_confidence})
Base = (0.40 × [technical_conf]) + (0.30 × [sentiment_conf]) + (0.30 × [reflection_conf])
Base = [calculation] = [result]
```

Then apply adjustments:
- Volume adjustment: If <0.7x = -0.08, if <1.0x = -0.05
- Risk adjustment: HIGH = -0.10, MEDIUM = -0.05
- Alignment adjustment: Strong agreement = +0.05, conflict = -0.10

**Show adjusted calculation**:
```
Adjusted = Base + [adjustments with reasons]
Final confidence = [final_score]
```

Write 1-2 sentences explaining what this final confidence means.

### PHASE 3: ANALYZE EACH AGENT'S CONTRIBUTION

Go through each agent:

**A) TECHNICAL ANALYST:**
- What's their strongest signal? (volume, momentum, support/resistance?)
- Are entry/stop/target levels valid and actionable?
- What did they miss that others caught?
- Trust level: High/Medium/Low and why?

Write 2-3 sentences.

**B) SENTIMENT ANALYST:**
- Real catalysts (partnerships, ETFs) or just hype?
- Any critical risk flags (regulatory, security)?
- Source credibility and news freshness?
- Does sentiment support or contradict Technical?

Write 2-3 sentences.

**C) REFLECTION ANALYST:**
- What blind spots did they identify?
- Is their risk assessment valid and actionable?
- Did they find something both Technical and Sentiment missed?
- Should their caution override the bullish/bearish case?

Write 2-3 sentences.

### PHASE 4: RESOLVE CONFLICTS & DECIDE DIRECTION

If agents disagree, resolve it:
- Which agent has stronger evidence?
- Does Technical's chart override Sentiment concerns? Or vice versa?
- Is Reflection's caution justified by real risks?
- What's the path of least regret?

**Decision rules**:
- Weighted confidence ≥0.65 AND 2+ agents agree → BUY/SELL
- Weighted confidence 0.50-0.64 AND moderate consensus → BUY/SELL with caution  
- Weighted confidence <0.50 OR no consensus → HOLD/WAIT
- Dead volume (<0.7x) ALWAYS forces WAIT regardless of other signals

Write 2-3 sentences explaining your final direction decision.

### PHASE 5: BUILD EXECUTION PLAN

Now create the specific trading plan:

**ENTRY TIMING:**
- Enter NOW or WAIT for better setup?
- If wait, what conditions? (price level, volume confirmation, time window)
- Be specific: "Enter if price dips to $184 with volume >1.5x" or "Wait for Technical's $145 breakout"

**POSITION SIZE:**
- Based on final confidence:
  - >0.75 = 70-100% position
  - 0.65-0.75 = 50-70%
  - 0.50-0.64 = 30-50%
  - <0.50 = 0% (HOLD/WAIT)
- Adjust down 20% if HIGH risk flagged by Reflection

**PRICE LEVELS:**
- Use Technical's entry/stop/target if valid
- If Technical has no levels but recommends BUY/SELL → WAIT instead
- Validate: Stop within 5%? R/R >1.5:1?

**TIMEFRAME:**
- Start with Technical's timeframe: {tech_timeframe}
- Consider Sentiment's suggestion (if different)
- Adjust for conviction: High confidence = full duration, Medium = take profits early
- Be specific: "3-5 days" or "Hold until $198 target OR 5 days max"

Write 3-4 sentences detailing exact execution.

---

## OUTPUT FORMAT

<thinking>
[Write your full 5-phase analysis here]

PHASE 1: CONSENSUS CHECK
[Your analysis...]

PHASE 2: WEIGHTED CONFIDENCE CALCULATION  
[Show the math...]

PHASE 3: ANALYZE EACH AGENT
[Technical: ...]
[Sentiment: ...]
[Reflection: ...]

PHASE 4: RESOLVE CONFLICTS
[Your decision logic...]

PHASE 5: EXECUTION PLAN
[Specific entry, size, levels, timeframe...]

</thinking>

<answer>
{{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",
  
  "market_condition": "BULLISH|BEARISH|NEUTRAL|WAIT",
  
  "confidence": {{
    "score": 0.68,
    "reasoning": "Weighted synthesis: Technical BUY (0.72 × 40% = 0.29) + Sentiment BULLISH (0.65 × 30% = 0.20) + Reflection WAIT (0.57 × 30% = 0.17) = 0.66 base. Dead volume adjustment (-0.08) drops to 0.58. Final call: WAIT until volume >1.5x confirms institutions buying Morgan Stanley story despite bullish alignment."
  }},
  
  "timestamp": "2026-01-06T12:34:56Z",
  
  "agent_synthesis": {{
    "technical_weight": 0.40,
    "sentiment_weight": 0.30,
    "reflection_weight": 0.30,
    "weighted_confidence": 0.58,
    "agreement_summary": "Write 4-6 sentences explaining how all 3 agents align or conflict. Technical says [X with score], Sentiment says [Y with score], Reflection says [Z with score]. Alignment score [N] indicates [strong/moderate/weak] consensus. Core disagreement is [specific issue]. This leads to [recommendation] because [weighted logic + key factors]."
  }},
  
  "execution_plan": {{
    "entry_timing": "Specific timing with conditions: 'Wait for volume >1.5x within 48h' or 'Enter on pullback to $184' or 'Execute immediately at market'",
    "position_size": "50%",
    "entry_price_target": 184.00,
    "stop_loss": 176.00,
    "take_profit": 198.00,
    "timeframe": "3-5 days",
    "risk_reward_ratio": "1.75:1"
  }},
  
  "risk_management": {{
    "max_loss_per_trade": "2%",
    "primary_risk": "Dead volume (0.56x) means rally lacks institutional backing - could reverse on any negative catalyst",
    "secondary_risks": [
      "Specific risk 1 from agents",
      "Specific risk 2 from agents"
    ],
    "exit_conditions": [
      "IMMEDIATE: Break below $176 stop",
      "24H: Volume stays <1.0x for 48h",
      "PROFIT: Hit $198 OR 5 days elapsed"
    ],
    "monitoring_checklist": [
      "Volume MUST surge >1.5x within 48h",
      "Price must hold $184 support",
      "Watch Morgan Stanley ETF progress"
    ]
  }}
}}
</answer>

</decision_framework>

<critical_rules>
1. If NO CONSENSUS (all 3 disagree) → MUST return WAIT
2. If weighted_confidence <0.50 → MUST return HOLD or WAIT
3. If Technical has NO entry/stop/target → MUST return WAIT (can't trade without levels)
4. If Sentiment has critical risk flags (delisting, lawsuit) → MUST return WAIT
5. If volume <0.7x (DEAD) → MUST return WAIT regardless of other signals
6. Position size MUST match confidence tiers
7. agreement_summary MUST be 4-6 sentences with all 3 agent scores
8. confidence.reasoning MUST show weighted calculation math
9. entry_timing MUST be specific with conditions and price levels
10. If recommendation is WAIT, set entry/stop/target to null, timeframe to "Wait [X] for [condition]"
</critical_rules>
"""
```

### 📝 Change 4: Update Format Variables

**Location**: `trader.py` → `TraderAgent.execute()` → building `full_prompt`

**Update variable extraction**:
```python
# Technical data
tech_recommendation = tech.get('recommendation_signal', 'HOLD')
tech_confidence = tech_confidence  # Already extracted above
tech_market_condition = tech.get('market_condition', 'QUIET')
tech_summary = tech.get('confidence', {}).get('reasoning', 'No reasoning provided')
tech_entry = get_nested(tech, 'trade_setup.entry', 0.0)
tech_stop = get_nested(tech, 'trade_setup.stop_loss', 0.0)
tech_target = get_nested(tech, 'trade_setup.take_profit', 0.0)
tech_risk_reward = get_nested(tech, 'trade_setup.risk_reward', 0.0)
tech_timeframe = get_nested(tech, 'trade_setup.timeframe', 'N/A')
volume_ratio = get_nested(tech, 'analysis.volume.ratio', 1.0)
volume_quality = get_nested(tech, 'analysis.volume.quality', 'UNKNOWN')

# Sentiment data
sentiment_recommendation = sentiment_recommendation  # Already extracted
sentiment_confidence = sentiment_confidence  # Already extracted
sentiment_market_condition = sentiment.get('market_condition', 'NEUTRAL')
sentiment_summary = sentiment.get('confidence', {}).get('reasoning', 'No reasoning provided')
cfgi_score = get_nested(sentiment, 'fear_greed_index.score', 50)
cfgi_classification = get_nested(sentiment, 'fear_greed_index.classification', 'Neutral')
sentiment_score = sentiment.get('sentiment_score', 0.5)
sentiment_label = sentiment.get('sentiment_label', 'NEUTRAL')
positive_catalysts = sentiment.get('positive_catalysts', 0)
negative_risks = sentiment.get('negative_risks', 0)

# Reflection data
reflection_recommendation = reflection_recommendation  # Already extracted
reflection_confidence = reflection_confidence  # Already extracted
reflection_market_condition = reflection.get('market_condition', 'MIXED')
reflection_summary = reflection.get('confidence', {}).get('reasoning', 'No reasoning provided')
alignment_score = get_nested(reflection, 'agent_alignment.alignment_score', 0.5)
alignment_status = reflection.get('market_condition', 'MIXED')  # Use market_condition as alignment status
primary_risk = reflection.get('primary_risk', 'No primary risk identified')
```

**Add helper function if not exists**:
```python
def get_nested(d, path, default=None):
    """Safely get nested dict values using dot notation"""
    keys = path.split('.')
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
            if d is None:
                return default
        else:
            return default
    return d if d is not None else default
```

### 📝 Change 5: Update Parsing Logic for Output

**Location**: `trader.py` → `TraderAgent.execute()` → `try` block

**Replace confidence validation**:
```python
trader_data = json.loads(answer_json)

# Validate and standardize recommendation_signal
decision = trader_data.get('recommendation_signal', 'HOLD').upper()
if decision not in ['BUY', 'SELL', 'HOLD', 'WAIT']:
    print(f"⚠️  Invalid decision '{decision}', defaulting to HOLD")
    decision = 'HOLD'
trader_data['recommendation_signal'] = decision

# Validate and standardize market_condition
market_condition = trader_data.get('market_condition', 'NEUTRAL').upper()
if market_condition not in ['BULLISH', 'BEARISH', 'NEUTRAL', 'WAIT']:
    print(f"⚠️  Invalid market_condition '{market_condition}', defaulting to NEUTRAL")
    market_condition = 'NEUTRAL'
trader_data['market_condition'] = market_condition

# Validate confidence structure
confidence = trader_data.get('confidence', {})
if not isinstance(confidence, dict):
    confidence = {
        'score': 0.5,
        'reasoning': 'Invalid confidence format'
    }
elif 'score' not in confidence:
    # Try to extract from old format
    score = float(confidence) if isinstance(confidence, (int, float)) else 0.5
    confidence = {
        'score': score,
        'reasoning': 'Converted from old format'
    }

# Ensure score is valid (0.0 - 1.0)
confidence['score'] = max(0.0, min(1.0, float(confidence.get('score', 0.5))))

# Ensure reasoning exists
if not confidence.get('reasoning') or not isinstance(confidence['reasoning'], str):
    confidence['reasoning'] = 'No reasoning provided'

trader_data['confidence'] = confidence

# Add thinking and timestamp
trader_data['thinking'] = thinking
trader_data['timestamp'] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

state['trader'] = trader_data
```

### 📝 Change 6: Update Fallback Error Handling

**Location**: `trader.py` → `except` block

**Replace with**:
```python
except (json.JSONDecodeError, ValueError) as e:
    print(f"⚠️  Trader agent parsing error: {e}")
    print(f"Response preview: {response[:500]}")

    # Use Reflection as most reliable fallback
    fallback_decision = reflection_recommendation if reflection_recommendation in ['BUY', 'SELL', 'HOLD', 'WAIT'] else 'WAIT'
    fallback_market_condition = reflection_market_condition if reflection_market_condition in ['ALIGNED', 'CONFLICTED', 'MIXED'] else 'NEUTRAL'
    
    # Map reflection market_condition to trader market_condition
    if fallback_market_condition == 'ALIGNED':
        if tech_recommendation in ['BUY'] or sentiment_recommendation in ['BUY']:
            trader_market_condition = 'BULLISH'
        elif tech_recommendation in ['SELL'] or sentiment_recommendation in ['SELL']:
            trader_market_condition = 'BEARISH'
        else:
            trader_market_condition = 'NEUTRAL'
    else:
        trader_market_condition = 'WAIT'

    # Calculate fallback confidence
    fallback_confidence = (tech_confidence + sentiment_confidence + reflection_confidence) / 3 * 0.8

    state['trader'] = {
        'recommendation_signal': fallback_decision,
        'market_condition': trader_market_condition,
        'confidence': {
            'score': fallback_confidence,
            'reasoning': f'Trader synthesis failed - using Reflection recommendation ({fallback_decision}) as fallback. Technical {tech_recommendation} ({tech_confidence:.0%}), Sentiment {sentiment_recommendation} ({sentiment_confidence:.0%}), Reflection {reflection_recommendation} ({reflection_confidence:.0%}). Average confidence {fallback_confidence:.0%}. Error: {str(e)[:100]}'
        },
        'timestamp': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        'agent_synthesis': {
            'technical_weight': 0.40,
            'sentiment_weight': 0.30,
            'reflection_weight': 0.30,
            'weighted_confidence': fallback_confidence,
            'agreement_summary': f'Parsing error - fallback mode. Using Reflection ({fallback_decision}) as safest option given error state.'
        },
        'execution_plan': {
            'entry_timing': 'Re-run trader analysis',
            'position_size': '0%',
            'entry_price_target': None,
            'stop_loss': None,
            'take_profit': None,
            'timeframe': 'N/A',
            'risk_reward_ratio': 'N/A'
        },
        'risk_management': {
            'max_loss_per_trade': '2%',
            'primary_risk': f'Analysis error: {str(e)[:100]}',
            'secondary_risks': ['Parsing failed - high uncertainty'],
            'exit_conditions': ['Re-run complete analysis'],
            'monitoring_checklist': ['Generate new trader analysis']
        },
        'thinking': f'Error: {str(e)}'
    }

    print(f"  FALLBACK DECISION: {fallback_decision} ({fallback_confidence:.0%})")
```

---

## Updated JSON Output Schema

```json
{
  "recommendation_signal": "WAIT",
  "market_condition": "BULLISH",
  "confidence": {
    "score": 0.58,
    "reasoning": "Weighted synthesis: Technical BUY (0.72 × 40% = 0.29) + Sentiment BULLISH (0.65 × 30% = 0.20) + Reflection WAIT (0.57 × 30% = 0.17) = 0.66 base. Dead volume at 0.56x drops confidence by -0.08 to final 0.58. Despite bullish alignment (Technical + Sentiment agree), Reflection correctly flags volume risk - WAIT until volume >1.5x proves institutions are buying the Morgan Stanley story."
  },
  "timestamp": "2026-01-06T12:34:56Z",
  
  "agent_synthesis": {
    "technical_weight": 0.40,
    "sentiment_weight": 0.30,
    "reflection_weight": 0.30,
    "weighted_confidence": 0.58,
    "agreement_summary": "Technical recommends BUY (0.72 confidence) on breakout setup with 3.2:1 R/R above $145. Sentiment confirms BULLISH (0.65) citing Morgan Stanley ETF filing (Jan 6, fresh catalyst). Both align on bullish direction (2 of 3 consensus). However, Reflection urges WAIT (0.57) - correctly identifying dead volume (0.56x for 43 days) as critical blind spot both others underweighted. The disagreement centers on whether fresh institutional news can override lack of volume confirmation. Weighted logic (40% Technical, 30% Sentiment, 30% Reflection) plus dead volume penalty (-0.08) yields 0.58 confidence, favoring WAIT until volume proves institutions are actually buying."
  },
  
  "execution_plan": {
    "entry_timing": "WAIT for volume confirmation: Enter only if volume surges above 1.5x average within next 48 hours AND price stays above $184 support. If no volume spike by Jan 9, re-evaluate entire setup. Do not chase current price.",
    "position_size": "0%",
    "entry_price_target": null,
    "stop_loss": null,
    "take_profit": null,
    