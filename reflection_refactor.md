# 03 - Reflection Agent Refactor

## Current Problems

### ❌ Problem 1: No Clear `recommendation_signal` at Top
```python
# Current output shows:
"recommendation_signal": "WAIT",  # Good!
# But it's buried or unclear in UI presentation
```

**Issue**: The recommendation exists but isn't prominently displayed like Technical/Sentiment agents.

### ❌ Problem 2: Wrong `market_condition` Output
```python
# Currently no market_condition field
# OR it outputs something inconsistent
```

**Issue**: Reflection should show agent ALIGNMENT status (ALIGNED/CONFLICTED/MIXED), not technical/sentiment states.

### ❌ Problem 3: Complex Confidence Structure
```python
# Current output:
"confidence": {
    "analysis_confidence": 0.80,
    "final_confidence": 0.57,
    "interpretation": "High confidence in synthesis, moderate final confidence due to risks"
}
```

**Issues**:
- Two confidence scores is confusing
- "analysis_confidence" vs "final_confidence" - which matters?
- "interpretation" doesn't paint a picture with data

### ❌ Problem 4: Weak Agreement Synthesis
```python
"agreement_analysis": {
    "alignment_status": "PARTIAL",
    "alignment_score": 0.75,
    "synthesis": "Technical and news both show bullish potential, but with significant reservations."
}
```

**Issues**:
- Generic synthesis doesn't explain HOW agents align/conflict
- Doesn't cite specific disagreements (e.g., "Technical says BUY at 0.72, Sentiment says HOLD at 0.65")
- Doesn't paint a picture - just states obvious
- Missing natural storytelling

### ❌ Problem 5: Blind Spots Are Lists, Not Stories
```python
"blind_spots": {
    "technical_missed": [
        "Network reliability risks",
        "Potential security vulnerabilities"
    ],
    "sentiment_missed": [
        "Strong momentum signals",
        "Institutional volume interest"
    ]
}
```

**Issue**: Just listing items. Doesn't explain WHY these matter or HOW they change the picture. Not actionable.

### ❌ Problem 6: Risk Assessment Lacks Context
```python
"risk_assessment": {
    "primary_risk": "Network infrastructure concerns could rapidly undermine bullish momentum",
    "risk_level": "MEDIUM",
    "risk_score": 0.55
}
```

**Issue**: States the risk but doesn't connect it to the recommendation. Why WAIT instead of HOLD if risk is MEDIUM?

### ❌ Problem 7: Auto-Generated Fields Are Too Mechanical

The code auto-generates:
```python
reflection_data['agreement_analysis']['technical_view'] = f"{tech_recommendation} ({tech_confidence:.0%})"
reflection_data['agreement_analysis']['sentiment_view'] = f"{sentiment_signal} ({sentiment_confidence:.0%})"
```

**Issue**: This is good for structure but the LLM's `synthesis` field doesn't leverage it naturally.

---

## Solutions

### ✅ Solution 1: Emphasize `recommendation_signal` at Top

Already exists, just ensure it's:
- Clearly derived from synthesis of Technical + Sentiment
- Explained in confidence reasoning

### ✅ Solution 2: Add `market_condition` = Agent Alignment

Output one of: `ALIGNED` | `CONFLICTED` | `MIXED`

- **ALIGNED**: Both agents agree on direction (both bullish or both bearish)
- **CONFLICTED**: Agents disagree on direction (one bullish, one bearish)
- **MIXED**: One agent neutral or unclear signals

### ✅ Solution 3: Simplify Confidence Structure

**Remove**:
- `analysis_confidence`
- `final_confidence` (or keep as `score`)
- `interpretation`

**Replace with**:
```python
"confidence": {
    "score": 0.57,
    "reasoning": "Technical says BUY (0.72 setup) but volume is dead at 0.56x for 43 days - institutions aren't buying. Sentiment is bullish (0.65) on Morgan Stanley news, but news can't move price without volume. This conflict plus weak volume drops confidence to 57% - clear WAIT until volume confirms."
}
```

### ✅ Solution 4: Make Synthesis Tell a Story

**Current** (generic):
> "Technical and news both show bullish potential, but with significant reservations."

**Fixed** (specific story):
> "Technical spots a breakout setup above $145 with 3.2:1 R/R (0.72 confidence), while Sentiment sees genuine institutional catalyst in Morgan Stanley ETF filing (0.65 confidence). They align on bullish direction BUT disagree on timing: Technical wants volume >1.5x to confirm, Sentiment says news is fresh enough. The gap is volume - without it, even good news can't sustain rallies."

**Keys**:
- Cite actual confidence scores
- Name specific factors (price levels, news events, volume ratios)
- Explain the DISAGREEMENT clearly
- Show HOW this affects the decision

### ✅ Solution 5: Make Blind Spots Actionable Stories

**Current** (list):
```
"technical_missed": ["Network reliability risks"]
```

**Fixed** (story):
```
"technical_missed": "Technical focused on chart patterns but missed the 2-hour network outage on Dec 30 that Sentiment flagged. This reliability risk could trigger stop-losses if it recurs, regardless of how bullish the chart looks."
```

Change from array to single string that explains:
1. WHAT was missed
2. WHY it matters
3. HOW it changes the picture

### ✅ Solution 6: Connect Risk to Recommendation

**Current**:
> "Primary risk: Network infrastructure concerns could rapidly undermine bullish momentum"

**Fixed**:
> "Primary risk: Dead volume (0.56x) means any bullish move lacks institutional backing. If price rises on retail hype alone (CFGI Social 96), it'll dump fast when institutions don't follow. This is WHY we WAIT - we need volume >1.5x to confirm institutions are actually buying the Morgan Stanley ETF story."

Connect risk → confidence → recommendation in natural flow.

### ✅ Solution 7: Let LLM Write Natural Synthesis

Remove some auto-generated fields, let LLM write:
- Keep auto-calculating `alignment_score` (objective)
- Keep auto-generating `technical_view` and `sentiment_view` (data)
- Let LLM write `synthesis` naturally using those data points

---

## Code Changes Required

### 📝 Change 1: Update System Prompt

**Location**: `reflection.py` → `SYSTEM_PROMPT`

**Add to end**:
```
YOUR OUTPUT REQUIREMENTS:
- market_condition: Agent alignment status (ALIGNED/CONFLICTED/MIXED)
- confidence.reasoning: Tell the story of how Technical + Sentiment combine. Cite their specific scores, disagreements, and why this leads to your recommendation. Paint a picture.
- synthesis: Don't just say "they agree/disagree" - explain WHAT they agree/disagree on with specifics
- blind_spots: Not just lists - explain WHY each blind spot matters and HOW it changes the analysis
- Connect everything: risk → confidence → recommendation in a natural flow
```

### 📝 Change 2: Update Output Format in Prompt

**Location**: `reflection.py` → `REFLECTION_PROMPT` → `<answer>` section

**Replace with**:
```json
{
  "recommendation_signal": "BUY|SELL|HOLD|WAIT",
  
  "market_condition": "ALIGNED|CONFLICTED|MIXED",
  
  "confidence": {
    "score": 0.57,
    "reasoning": "Technical says [X with score], Sentiment says [Y with score]. They [agree/conflict] on [specific aspect]. Combined with [key factor like volume/risk], this gives us [recommendation] with [score]% confidence because [specific reason]."
  },
  
  "timestamp": "2026-01-06T12:34:56Z",
  
  "agent_alignment": {
    "technical_says": "BUY (0.72)",
    "sentiment_says": "BULLISH (0.65)",
    "alignment_score": 0.85,
    "synthesis": "Both agents lean bullish - Technical sees breakout setup above $145 (3.2:1 R/R), Sentiment confirms with Morgan Stanley ETF catalyst (Jan 6). Key gap: Technical needs volume >1.5x to confirm but Sentiment thinks fresh news is enough. Without institutional volume showing up in the data, even strong catalysts can fail at resistance."
  },
  
  "blind_spots": {
    "technical_missed": "Technical focused on chart breakout but didn't weight the 2-hour network outage (Dec 30) that Sentiment flagged. Even with bullish momentum, reliability issues can trigger cascading stop-losses and invalidate the setup overnight.",
    
    "sentiment_missed": "Sentiment is excited about Morgan Stanley news but missed that volume is dead at 0.56x average for 43 days - no institutional buying is showing up yet. News creates potential, but Technical's volume data shows institutions haven't arrived. This timing gap is critical.",
    
    "critical_insight": "The real trade decision hinges on volume: if institutions start buying (volume >1.5x) within 48 hours of the Morgan Stanley news, this becomes a strong BUY. Without volume follow-through, it's just retail hype that will fade at resistance. WAIT and watch volume."
  },
  
  "primary_risk": "Dead volume (0.56x for 43 days) means bullish setup lacks institutional conviction. If price rallies on retail enthusiasm alone (CFGI Social 96) without institutions participating, it will dump at $144.93 resistance. This is why WAIT makes sense - we need volume proof before risking capital on news-driven hype.",
  
  "monitoring": {
    "watch_next_24h": [
      "Volume spike above 1.5x average - THE signal to enter",
      "Price reaction at $144.93 resistance with volume analysis",
      "Any Morgan Stanley ETF filing updates or SEC commentary"
    ],
    "invalidation_triggers": [
      "Volume stays below 0.8x for 48 more hours - news failed to attract institutions",
      "Break below $135 support invalidates Technical's bullish structure"
    ]
  },
  
  "final_reasoning": "Technical + Sentiment both lean bullish (alignment_score 0.85), but WAIT recommendation comes from their timing gap: Technical correctly demands volume proof (not seeing it at 0.56x), while Sentiment is early on the news catalyst. Smart play is wait for volume to confirm institutions are actually buying the story before committing capital."
}
```

**Key changes**:
- Added `market_condition` = agent alignment
- Simplified `confidence` to `{score, reasoning}` with story
- Made `synthesis` tell specific story with scores
- Changed `blind_spots` from arrays to narrative strings
- Made `primary_risk` connect to recommendation
- Renamed `reasoning` → `final_reasoning` for clarity

### 📝 Change 3: Update Thinking Framework

**Location**: `reflection.py` → `REFLECTION_PROMPT` → `<thinking>` section

**Replace with clearer instructions**:
```
<thinking>

**PHASE 1: AGENT ALIGNMENT ANALYSIS**

Compare Technical ({tech_recommendation}, {tech_confidence:.0%}) vs Sentiment ({sentiment_signal}, {sentiment_confidence:.0%}):

Write 3-4 sentences explaining:
- Do they AGREE on direction (both bullish/bearish)?
- What SPECIFIC factors drive each recommendation? (cite prices, volume, news, dates)
- Where's the KEY DISAGREEMENT? (timing? risk tolerance? data interpretation?)
- What's the alignment_score telling us? (>0.80=strong, 0.60-0.80=moderate, <0.60=weak)

Example: "Technical sees BUY setup (0.72) on breakout above $145 with 3.2:1 R/R. Sentiment also bullish (0.65) citing Morgan Stanley ETF news (Jan 6). Both agree on direction (alignment 0.85) but disagree on timing: Technical demands volume >1.5x first, Sentiment thinks news is catalyst enough. The gap is whether to trust the chart pattern or the news headline."


**PHASE 2: TECHNICAL BLIND SPOTS**

What did Technical analysis MISS that Sentiment revealed?

Write 2-3 sentences for EACH blind spot:
- WHAT was missed? (specific news event, risk flag, market context)
- WHY does it matter? (how does it change Technical's thesis?)
- HOW should this affect the trade decision?

Example: "Technical focused purely on the chart breakout but completely missed the 2-hour Solana network outage on Dec 30 that Sentiment flagged from news sources. This reliability concern isn't visible in price action yet, but if another outage hits, it would trigger cascading stop-losses regardless of how bullish the chart looks. This hidden risk justifies reducing position size even with a good technical setup."


**PHASE 3: SENTIMENT BLIND SPOTS**

What did Sentiment analysis MISS that Technical revealed?

Write 2-3 sentences for EACH blind spot:
- WHAT was missed? (volume data, chart structure, momentum signals)
- WHY does it matter? (how does it change Sentiment's thesis?)
- HOW should this affect the trade decision?

Example: "Sentiment is excited about Morgan Stanley ETF filing (fresh news, reputable source) but didn't see that volume has been dead at 0.56x average for 43 straight days - institutions AREN'T buying yet. News creates POTENTIAL for a move, but Technical's volume data shows institutional money hasn't arrived. This timing gap means news-driven rallies could fail at resistance without volume follow-through."


**PHASE 4: SYNTHESIS & DECISION**

Combine everything into your recommendation:

Write 3-4 sentences covering:
- What's the OVERALL PICTURE? (both agents bullish? conflicted? one neutral?)
- What's the PRIMARY RISK that could derail this trade?
- Given alignment + blind spots + risks, what's the RIGHT MOVE? (BUY/SELL/HOLD/WAIT)
- What SPECIFIC CONDITIONS would change your mind?

Example: "Both agents lean bullish (0.85 alignment) on genuine institutional catalyst, but timing is the issue. Technical correctly demands volume proof (not seeing it at 0.56x for 43 days) before trusting the rally. Sentiment is early on the news but blind to volume reality. Smart move is WAIT with 57% confidence - if institutions start buying (volume >1.5x) within 48 hours of Morgan Stanley news, this becomes strong BUY. Without volume follow-through, it's retail hype that will dump at resistance."

</thinking>
```

### 📝 Change 4: Update Confidence Guidelines

**Location**: `reflection.py` → Add new section before `<thinking>`

**Add**:
```
<confidence_guidelines>
## Confidence Score (0.15-1.0)
After synthesizing Technical + Sentiment, how confident are you in the final recommendation?

- 0.80-1.00: Very high - both agents strongly aligned, clear edge
- 0.65-0.79: High - good alignment, manageable risks
- 0.50-0.64: Moderate - some conflicts but edge exists
- 0.35-0.49: Low - significant conflicts or unclear edge
- 0.15-0.34: Very low - major conflicts, wait for clarity

## Confidence Reasoning (CRITICAL)
Write 2-3 sentences that tell the synthesis story:

✅ **Must include**:
- Both agents' recommendations + scores (e.g., "Technical BUY 0.72, Sentiment BULLISH 0.65")
- Specific point of agreement or conflict (volume, timing, risk)
- Key data that tips the decision (volume ratio, news date, price level)
- WHY this leads to your recommendation + confidence

✅ **Natural storytelling** - connect Technical + Sentiment into coherent picture
❌ **No generic statements** like "agents partially align"
❌ **No listing without context**

**GOOD Examples**:

"Technical screams BUY (0.72) on clean breakout with 3.2:1 R/R, and Sentiment confirms with Morgan Stanley ETF catalyst (0.65), creating 0.85 alignment. However, volume is dead at 0.56x for 43 days - institutions haven't shown up yet. Despite strong alignment, dead volume drops confidence to 58% for WAIT: need volume >1.5x to prove institutions are buying the story before risking capital."

"Strong conflict: Technical says WAIT (0.32) citing dead volume and overbought RSI, but Sentiment is bullish (0.68) on fresh Ondo Finance news. Alignment score 0.45 shows deep disagreement. Technical's volume data wins here - news can't move price without institutional buying pressure. Confidence 0.41 in WAIT: let volume confirm before trusting news-driven rallies."

"Perfect alignment (0.92): Technical BUY (0.78) and Sentiment BULLISH (0.75) both cite the same factors - volume surge to 1.8x, Morgan Stanley ETF, RSI healthy at 66. No blind spots found, primary risk is normal (BTC correlation). High confidence 0.82 in BUY with 3-5 day timeframe and tight stop at $142."

**BAD Examples** ❌:

"Moderate confidence due to partial agent alignment"
→ No specifics, doesn't explain WHY moderate

"Technical and Sentiment show some agreement but also concerns"
→ Vague, no data, no story

"Confidence is 0.57 based on synthesis of both analyses"
→ Circular, doesn't explain reasoning
</confidence_guidelines>
```

### 📝 Change 5: Update Parsing Logic

**Location**: `reflection.py` → `ReflectionAgent.execute()` → parsing section

**Find confidence parsing** (around line 280-320):
```python
# Current code handles nested confidence...
```

**Replace with**:
```python
confidence = reflection_data.get('confidence', {})

# Validate confidence structure
if not isinstance(confidence, dict):
    confidence = {
        'score': 0.5,
        'reasoning': 'Invalid confidence format'
    }
elif 'score' not in confidence:
    # Backward compatibility
    if 'final_confidence' in confidence:
        score = float(confidence.get('final_confidence', 0.5))
    elif 'analysis_confidence' in confidence:
        score = float(confidence.get('analysis_confidence', 0.5))
    else:
        score = 0.5
    
    reasoning = confidence.get('interpretation', 'Converted from old format')
    
    confidence = {
        'score': score,
        'reasoning': reasoning
    }

# Ensure score is valid (0.15 - 1.0)
confidence['score'] = max(0.15, min(1.0, float(confidence.get('score', 0.5))))

# Ensure reasoning exists
if not confidence.get('reasoning') or not isinstance(confidence['reasoning'], str):
    confidence['reasoning'] = 'No reasoning provided'

reflection_data['confidence'] = confidence

# Ensure market_condition exists (agent alignment)
if 'market_condition' not in reflection_data:
    alignment_status = reflection_data.get('agent_alignment', {}).get('alignment_status', 'PARTIAL')
    if alignment_status == 'STRONG':
        reflection_data['market_condition'] = 'ALIGNED'
    elif alignment_status == 'WEAK' or alignment_status == 'NONE':
        reflection_data['market_condition'] = 'CONFLICTED'
    else:
        reflection_data['market_condition'] = 'MIXED'
```

**Also update blind spots parsing** to handle both old (array) and new (string) formats:
```python
# Handle blind spots format (can be array or string now)
blind_spots = reflection_data.get('blind_spots', {})
if blind_spots:
    # Convert old array format to new string format if needed
    if 'technical_missed' in blind_spots and isinstance(blind_spots['technical_missed'], list):
        blind_spots['technical_missed'] = ' '.join(blind_spots['technical_missed'])
    
    if 'sentiment_missed' in blind_spots and isinstance(blind_spots['sentiment_missed'], list):
        blind_spots['sentiment_missed'] = ' '.join(blind_spots['sentiment_missed'])
```

### 📝 Change 6: Update Fallback Error Handling

**Location**: `reflection.py` → `except` block

**Replace fallback**:
```python
state['reflection'] = {
    'recommendation_signal': tech_recommendation,
    'market_condition': 'MIXED',
    'confidence': {
        'score': max(0.20, confidence_calc['final_confidence']),
        'reasoning': f'Reflection synthesis failed: {str(e)[:100]}. Defaulting to Technical recommendation ({tech_recommendation}) with reduced confidence. Re-run analysis for full synthesis.'
    },
    'timestamp': timestamp,
    'agent_alignment': {
        'alignment_status': alignment_status,
        'alignment_score': alignment_score,
        'technical_says': f"{tech_recommendation} ({tech_confidence:.0%})",
        'sentiment_says': f"{sentiment_signal} ({sentiment_confidence:.0%})",
        'synthesis': f'Parsing error prevented synthesis. Technical recommends {tech_recommendation} ({tech_confidence:.0%}), Sentiment shows {sentiment_signal} ({sentiment_confidence:.0%}). Alignment score {alignment_score:.0%}.'
    },
    'blind_spots': {
        'technical_missed': f'Unable to analyze due to error: {str(e)[:100]}',
        'sentiment_missed': f'Unable to analyze due to error: {str(e)[:100]}',
        'critical_insight': 'Re-run reflection analysis for complete synthesis'
    },
    'primary_risk': f'Reflection failed - using calculated values only. Primary risk: {primary_risk_narrative}',
    'monitoring': {
        'watch_next_24h': ['Re-run reflection analysis', 'Monitor Technical + Sentiment agent outputs'],
        'invalidation_triggers': ['N/A - re-run analysis first']
    },
    'final_reasoning': f'Fallback: Technical {tech_recommendation} ({tech_confidence:.0%}), Sentiment {sentiment_signal} ({sentiment_confidence:.0%}), Alignment {alignment_score:.0%}. Error prevented full synthesis.'
}
```

### 📝 Change 7: Keep Auto-Calculated Fields

**Location**: `reflection.py` → POST-PROCESS section (after LLM response)

**Keep these auto-generated fields** (they're good):
```python
# These stay - they're objective data points
reflection_data['agent_alignment']['alignment_score'] = alignment_score
reflection_data['agent_alignment']['technical_says'] = f"{tech_recommendation} ({tech_confidence:.0%})"
reflection_data['agent_alignment']['sentiment_says'] = f"{sentiment_signal} ({sentiment_confidence:.0%})"
```

**Let LLM write** (subjective synthesis):
- `agent_alignment.synthesis` - LLM writes this naturally
- `confidence.reasoning` - LLM connects the story
- `blind_spots.*` - LLM explains what matters
- `primary_risk` - LLM connects to recommendation

---

## Updated JSON Output Schema

```json
{
  "recommendation_signal": "WAIT",
  "market_condition": "CONFLICTED",
  "confidence": {
    "score": 0.57,
    "reasoning": "Technical says BUY (0.72 setup) but flags dead volume at 0.56x for 43 days. Sentiment bullish (0.65) on Morgan Stanley ETF filing (Jan 6, CoinDesk). They align on direction (0.85 score) but disagree on timing: can news move price without institutional volume? Dead volume wins this debate - WAIT with 57% confidence until volume >1.5x confirms institutions are buying the story."
  },
  "timestamp": "2026-01-06T12:34:56Z",
  
  "agent_alignment": {
    "technical_says": "BUY (0.72)",
    "sentiment_says": "BULLISH (0.65)",
    "alignment_score": 0.85,
    "synthesis": "Both agents lean bullish on genuine catalyst (Morgan Stanley ETF), creating strong 0.85 alignment. Technical sees clean breakout above $145 with 3.2:1 R/R, Sentiment confirms with fresh institutional news. KEY GAP: Technical correctly demands volume >1.5x to confirm rally, but Sentiment thinks fresh news is catalyst enough. Without volume follow-through in next 48 hours, even strong news can fail at resistance."
  },
  
  "blind_spots": {
    "technical_missed": "Technical focused on chart patterns but completely missed the 2-hour Solana network outage on Dec 30 that Sentiment caught from news sources. This reliability risk isn't in price action yet, but if another outage hits during a rally, it would trigger cascading stop-losses regardless of how bullish the technicals look. Hidden infrastructure risk that reduces position sizing even with good setup.",
    
    "sentiment_missed": "Sentiment is excited about Morgan Stanley ETF filing (fresh, reputable source) but didn't see Technical's volume data: 0.56x average for 43 straight days means institutions AREN'T buying yet. News creates potential but Technical's data shows institutional money hasn't arrived. This timing gap is critical - news-driven rallies can fail at resistance without volume confirmation from actual institutional buying.",
    
    "critical_insight": "The trade decision hinges entirely on volume in next 48 hours: if institutions start buying (volume >1.5x) after Morgan Stanley news drops, this becomes strong BUY. Without volume follow-through, it's just retail hype (CFGI Social 96) that will dump at $144.93 resistance. WAIT and watch volume as the key variable."
  },
  
  "primary_risk": "Dead volume (0.56x for 43 days) means bullish setup lacks institutional conviction. If price rallies on retail enthusiasm alone without institutions participating, it will fail at $144.93 resistance. This is exactly WHY the recommendation is WAIT despite bullish alignment - we need volume proof that institutions are buying the Morgan Stanley story before risking capital on news-driven hype that could evaporate.",
  
  "monitoring": {
    "watch_next_24h": [
      "Volume spike above 1.5x average - THE critical signal to enter",
      "Price action at $144.93 resistance with volume analysis",
      "Morgan Stanley ETF filing progress or SEC commentary",
      "Solana network stability (any outages invalidate setup immediately)"
    ],
    "invalidation_triggers": [
      "Volume stays below 0.8x for 48+ hours - news failed to attract institutions",
      "Break below $135.51 support ends Technical's bullish structure",
      "New Solana network outage or major security incident"
    ]
  },
  
  "final_reasoning": "High agent alignment (0.85) with both leaning bullish, but WAIT recommendation comes from their timing gap: Technical correctly demands volume proof (not seeing it), Sentiment is early on catalyst. Primary risk is dead volume making rallies fragile. Smart play: wait for volume >1.5x to confirm institutions are buying the story, then enter with high confidence. Until then, 57% confidence says patience beats premature entry."
}
```

---

## Examples: Before & After

### Example 1: Conflicting Agents

**❌ BEFORE (Generic)**:
```json
{
  "recommendation_signal": "HOLD",
  "confidence": {
    "analysis_confidence": 0.75,
    "final_confidence": 0.48,
    "interpretation": "Good synthesis but low final confidence due to conflicts"
  },
  "agreement_analysis": {
    "synthesis": "Technical and Sentiment show different priorities with some overlap."
  },
  "blind_spots": {
    "technical_missed": ["Major news catalyst"],
    "sentiment_missed": ["Volume concerns"]
  }
}
```

**✅ AFTER (Specific Story)**:
```json
{
  "recommendation_signal": "WAIT",
  "market_condition": "CONFLICTED",
  "confidence": {
    "score": 0.48,
    "reasoning": "Deep conflict: Technical says WAIT (0.32) citing dead volume and overbought RSI at 78.5, while Sentiment is bullish (0.68) on Ondo Finance partnership announcement. Alignment only 0.45 shows fundamental disagreement. Technical's volume data (0.56x for 43 days) trumps Sentiment's news excitement - institutions aren't buying despite good news. Low confidence 0.48 in WAIT: let volume confirm before trusting news-driven rallies."
  },
  "agent_alignment": {
    "technical_says": "WAIT (0.32)",
    "sentiment_says": "BULLISH (0.68)",
    "alignment_score": 0.45,
    "synthesis": "Major conflict on timing: Sentiment sees Ondo partnership (Dec 24, official source) as game-changer, but Technical sees overbought chart (RSI 78.5) with no institutional buying (volume 0.56x). Sentiment is early on the fundamental catalyst, Technical is right on execution risk. The disagreement isn't about IF Solana is good, but WHEN to enter - news needs volume confirmation before it's tradeable."
  },
  "blind_spots": {
    "technical_missed": "Technical laser-focused on dead volume but missed that Ondo Finance partnership (official announcement Dec 24) is first major RWA integration for Solana - this is structural upgrade to ecosystem, not just hype. If this partnership delivers, it changes Solana's fundamental value prop regardless of current volume drought.",
    
    "sentiment_missed": "Sentiment excited about partnership announcement but blind to Technical's volume reality: institutions AREN'T buying yet despite the news being 2 weeks old. If news was truly game-changing, volume would've spiked by now. Timing gap between announcement and institutional action suggests market isn't convinced yet.",
    
    "critical_insight": "Ondo partnership is REAL fundamental upgrade, but market timing is off. Technical is right to wait for volume, Sentiment is right about long-term catalyst. Resolution: WAIT for volume spike (proof institutions believe the story) OR wait for actual partnership implementation (proof of delivery) before entering. News alone isn't enough."
  },
  "primary_risk": "Getting caught in news-driven retail hype (CFGI Social 96) without institutional support. If we enter now based on Sentiment's excitement, we're buying into overbought technicals (RSI 78.5) with no volume safety net. When retail enthusiasm fades, there's no institutional floor to prevent sharp pullback. This is textbook 'sell the news' setup - WAIT for volume proof or implementation proof before risking capital."
}
```

### Example 2: Aligned Agents (High Confidence)

**❌ BEFORE (Weak)**:
```json
{
  "confidence": {
    "analysis_confidence": 0.88,
    "final_confidence": 0.82,
    "interpretation": "High confidence, agents aligned"
  },
  "agreement_analysis": {
    "synthesis": "Both agents show strong bullish signals with good alignment."
  }
}
```

**✅ AFTER (Strong)**:
```json
{
  "recommendation_signal": "BUY",
  "market_condition": "ALIGNED",
  "confidence": {
    "score": 0.82,
    "reasoning": "Perfect alignment (0.92): Technical BUY (0.78) on breakout above $145 with volume surge to 1.8x, Sentiment BULLISH (0.75) confirming Morgan Stanley ETF catalyst (Jan 6, CoinDesk). Both cite SAME factors - volume spike, institutional news, healthy RSI 66. No blind spots found, primary risk is normal (BTC correlation). High confidence 0.82 for BUY with 3-5 day hold and tight stop at $142."
  },
  "agent_alignment": {
    "technical_says": "BUY (0.78)",
    "sentiment_says": "BULLISH (0.75)",
    "alignment_score": 0.92,
    "synthesis": "Rare perfect storm: Technical sees textbook breakout (price above $145 EMA50, volume 1.8x confirming institutional participation, RSI 66 healthy), and Sentiment sees genuine institutional catalyst (Morgan Stanley ETF filing fresh on Jan 6). They're telling the SAME STORY from different angles - chart confirms institutions are buying, news explains WHY they're buying. This level of convergence (0.92 alignment) is what we wait for."
  },
  "blind_spots": {
    "technical_missed": "Technical analysis can't see that Morgan Stanley is the catalyst driving volume - it just sees volume spike. Sentiment adds crucial context: this isn't random volume, it's institutional response to credible ETF filing. Understanding the WHY behind volume makes the setup stickier - institutions buying for fundamental reasons tend to hold longer than momentum chasers.",
    
    "sentiment_missed": "Sentiment focused on news credibility but missed Technical's precision on entry/exit: clean support at $142 provides exact invalidation level, and 3.2:1 R/R to $155 target gives clear profit zone. News tells us WHAT to trade, Technical tells us HOW to trade it - entry, stop, target all defined.",
    
    "critical_insight": "When Technical's volume confirmation meets Sentiment's institutional catalyst on the same day, that's the highest-probability setup. Volume proves institutions are acting, news explains their thesis. This convergence is rare - don't overthink it, execute with proper risk management."
  },
  "primary_risk": "Normal risk: BTC correlation (0.88) means if BTC breaks down, SOL follows regardless of Morgan Stanley news. But risk is manageable with tight stop at $142. Unlike dead-volume scenarios, this has institutional support so selling pressure should find buyers. Standard execution risk, not structural concern."
}
```

---

## Validation Checklist

### ✅ Schema Compliance
- [ ] Has `recommendation_signal` (BUY/SELL/HOLD/WAIT)
- [ ] Has `market_condition` (ALIGNED/CONFLICTED/MIXED)
- [ ] Has `confidence.score` (0.15-1.0)
- [ ] Has `confidence.reasoning` (story connecting both agents)
- [ ] Has `timestamp`
- [ ] `agent_alignment.synthesis` tells specific story with scores
- [ ] `blind_spots.*` are narrative strings (not arrays)
- [ ] `primary_risk` connects to recommendation

### ✅ Transparency Test (CRITICAL)
Read 3 sample outputs and verify:
- [ ] Does confidence.reasoning cite BOTH agents' scores and recommendations?
- [ ] Does synthesis explain specific agreement/disagreement points?
- [ ] Do blind spots explain WHY each matters and HOW it changes analysis?
- [ ] Does primary_risk connect clearly to the recommendation?
- [ ] Can I understand the full synthesis story in 30 seconds?
- [ ] Is everything written in natural language (not robotic)?

### ✅ Story Quality Test
- [ ] Synthesis paints picture of how agents relate
- [ ] Blind spots explain impact, not just list what's missing
- [ ] Critical insight ties everything together
- [ ] Primary risk explains WHY recommendation makes sense given risk
- [ ] No generic phrases like "agents partially align"

### ✅ Code Quality
- [ ] Parsing handles old nested confidence format
- [ ] Parsing handles both array and string blind spots
- [ ] Fallback uses new structure
- [ ] Auto-calculated fields (scores, views) stay objective
- [ ] LLM writes subjective synthesis naturally

### ✅ Testing Scenarios
- [ ] High alignment (both bullish) → BUY
- [ ] High conflict (one bullish, one bearish) → WAIT
- [ ] Mixed (one neutral) → HOLD
- [ ] Dead volume override (bullish → WAIT)
- [ ] Error case → fallback with calculated values

---

## Implementation Steps

1. **Backup current code** - Save `reflection.py`
2. **Update system prompt** - Add output requirements
3. **Add confidence guidelines** - Show synthesis storytelling
4. **Update thinking framework** - More specific phase instructions
5. **Update output format** - New JSON structure
6. **Update parsing logic** - Handle new confidence + blind spots formats
7. **Update fallback** - Error handling with new structure
8. **Test with live data** - Verify synthesis quality
9. **Validate storytelling** - Check all narrative fields paint pictures
10. **Commit changes**

---

## Key Differences from Technical/Sentiment

1. **Confidence reasoning is synthesis-focused**:
   - Must cite BOTH agents' scores
   - Must explain alignment or conflict
   - Must show how blind spots affect decision

2. **market_condition is alignment-based**:
   - ALIGNED = agents agree on direction
   - CONFLICTED = agents disagree
   - MIXED = one neutral or unclear

3. **Blind spots are narrative, not lists**:
   - Explain WHAT was missed
   - Explain WHY it matters
   - Explain HOW it changes the picture

4. **Everything connects**:
   - Blind spots → Risk → Confidence → Recommendation
   - Natural flow, not disconnected sections

---

## Special Notes

### Auto-Calculated Fields (Keep Objective)
These are calculated in code (NOT by LLM):
- `alignment_score` - Objective calculation
- `risk_level` - Objective assessment
- `technical_says` / `sentiment_says` - Data formatting

### LLM-Written Fields (Keep Subjective)
These are written by LLM (natural language):
- `synthesis` - Tell the story
- `blind_spots.*` - Explain impact
- `confidence.reasoning` - Connect everything
- `primary_risk` - Link to recommendation

### The Critical Insight Field
This is THE MOST IMPORTANT blind spot. It should:
- Tie Technical + Sentiment together
- Reveal the hidden factor driving the trade
- Be actionable (tell traders what to watch)
- Be specific (cite data, not generic wisdom)

**Example**:
> "The trade hinges on volume in next 48h: if institutions start buying (volume >1.5x) after Morgan Stanley news, this becomes strong BUY. Without volume follow-through, it's retail hype that will dump at resistance. WAIT and watch volume as the key variable."

---

## Common Pitfalls to Avoid

❌ **Generic synthesis**: "Technical and Sentiment show some alignment"
✅ **Specific synthesis**: "Technical BUY (0.72) meets Sentiment BULLISH (0.65) on volume spike + Morgan Stanley news"

❌ **Listing blind spots**: ["Network risk", "Volume concern"]
✅ **Explaining blind spots**: "Technical missed the 2-hour outage that could trigger stops..."

❌ **Disconnected risk**: "Primary risk is market volatility"
✅ **Connected risk**: "Dead volume means rallies lack institutional support, which is WHY we WAIT..."

❌ **Weak reasoning**: "Moderate confidence due to mixed signals"
✅ **Strong reasoning**: "Technical says BUY (0.72) but volume dead at 0.56x for 43 days - confidence 0.57 for WAIT until volume confirms"

---

## Estimated Implementation Time

**Time**: 60-90 minutes (most complex refactor)
**Risk Level**: Medium (significant prompt + parsing changes)
**Testing Required**: Yes - verify synthesis quality with multiple scenarios
**Priority**: High - Reflection is the critical synthesis layer

---

## Success Criteria

After implementation, Reflection agent should:
1. ✅ Clearly show how Technical + Sentiment align or conflict
2. ✅ Explain blind spots with WHY and HOW they matter
3. ✅ Connect risk → confidence → recommendation naturally
4. ✅ Use specific data (scores, prices, dates, ratios)
5. ✅ Tell coherent stories, not list disconnected facts
6. ✅ Be scannable - user understands synthesis in 30 seconds

**The ultimate test**: Can a trader read the Reflection output and immediately understand:
- Do the agents agree or disagree?
- What did each miss?
- Why this recommendation makes sense?
- What to watch next?

If yes → successful refactor ✅