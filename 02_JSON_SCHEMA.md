# JSON Schema for Structured Outputs

## Overview

This schema defines the exact structure Claude Sonnet 4.5 must follow when outputting technical analysis. The API guarantees the response will match this schema.

---

## Complete Schema Definition

```python
TECHNICAL_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation_signal": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD", "WAIT"],
            "description": "Primary trading recommendation"
        },
        "confidence": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Confidence level from 0.0 to 1.0"
                },
                "reasoning": {
                    "type": "string",
                    "description": "2-3 sentences explaining confidence with specific data points"
                }
            },
            "required": ["score", "reasoning"],
            "additionalProperties": False
        },
        "market_condition": {
            "type": "string",
            "enum": ["TRENDING", "RANGING", "VOLATILE", "QUIET"],
            "description": "Overall market state"
        },
        "thinking": {
            "type": "string",
            "description": "Detailed chain-of-thought reasoning process"
        },
        "analysis": {
            "type": "object",
            "properties": {
                "trend": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["BULLISH", "BEARISH", "NEUTRAL"]
                        },
                        "strength": {
                            "type": "string",
                            "enum": ["STRONG", "MODERATE", "WEAK"]
                        },
                        "detail": {
                            "type": "string",
                            "description": "2-3 sentences with specific indicator values"
                        }
                    },
                    "required": ["direction", "strength", "detail"],
                    "additionalProperties": False
                },
                "momentum": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["BULLISH", "BEARISH", "NEUTRAL"]
                        },
                        "strength": {
                            "type": "string",
                            "enum": ["STRONG", "MODERATE", "WEAK"]
                        },
                        "detail": {
                            "type": "string",
                            "description": "2-3 sentences with specific indicator values"
                        }
                    },
                    "required": ["direction", "strength", "detail"],
                    "additionalProperties": False
                },
                "volume": {
                    "type": "object",
                    "properties": {
                        "quality": {
                            "type": "string",
                            "enum": ["STRONG", "ACCEPTABLE", "WEAK", "DEAD"]
                        },
                        "ratio": {
                            "type": "number",
                            "description": "Volume ratio vs average"
                        },
                        "detail": {
                            "type": "string",
                            "description": "2-3 sentences with specific values"
                        }
                    },
                    "required": ["quality", "ratio", "detail"],
                    "additionalProperties": False
                }
            },
            "required": ["trend", "momentum", "volume"],
            "additionalProperties": False
        },
        "trade_setup": {
            "type": "object",
            "properties": {
                "viability": {
                    "type": "string",
                    "enum": ["VALID", "WAIT", "INVALID"]
                },
                "entry": {
                    "type": "number",
                    "description": "Entry price level"
                },
                "stop_loss": {
                    "type": "number",
                    "description": "Stop loss price level"
                },
                "take_profit": {
                    "type": "number",
                    "description": "Take profit target"
                },
                "risk_reward": {
                    "type": "number",
                    "description": "Risk to reward ratio"
                },
                "support": {
                    "type": "number",
                    "description": "Key support level"
                },
                "resistance": {
                    "type": "number",
                    "description": "Key resistance level"
                },
                "current_price": {
                    "type": "number",
                    "description": "Current market price"
                },
                "timeframe": {
                    "type": "string",
                    "description": "Expected trade duration"
                }
            },
            "required": ["viability", "entry", "stop_loss", "take_profit", 
                        "risk_reward", "support", "resistance", "current_price", "timeframe"],
            "additionalProperties": False
        },
        "action_plan": {
            "type": "object",
            "properties": {
                "for_buyers": {
                    "type": "string",
                    "description": "Guidance for buyers"
                },
                "for_sellers": {
                    "type": "string",
                    "description": "Guidance for sellers"
                },
                "if_holding": {
                    "type": "string",
                    "description": "Guidance for current holders"
                },
                "avoid": {
                    "type": "string",
                    "description": "What NOT to do"
                }
            },
            "required": ["for_buyers", "for_sellers", "if_holding", "avoid"],
            "additionalProperties": False
        },
        "watch_list": {
            "type": "object",
            "properties": {
                "bullish_signals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Conditions that would make setup bullish"
                },
                "bearish_signals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Conditions that would invalidate setup"
                }
            },
            "required": ["bullish_signals", "bearish_signals"],
            "additionalProperties": False
        },
        "invalidation": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Conditions that kill the thesis"
        },
        "confidence_reasoning": {
            "type": "object",
            "properties": {
                "supporting": {
                    "type": "string",
                    "description": "2-5 sentences on what supports the recommendation"
                },
                "concerns": {
                    "type": "string",
                    "description": "2-5 sentences on what could go wrong"
                }
            },
            "required": ["supporting", "concerns"],
            "additionalProperties": False
        }
    },
    "required": [
        "recommendation_signal",
        "confidence",
        "market_condition",
        "thinking",
        "analysis",
        "trade_setup",
        "action_plan",
        "watch_list",
        "invalidation",
        "confidence_reasoning"
    ],
    "additionalProperties": False
}
```

---

## Schema Breakdown

### Top-Level Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recommendation_signal` | enum | Yes | BUY, SELL, HOLD, or WAIT |
| `confidence` | object | Yes | Score (0.0-1.0) and reasoning |
| `market_condition` | enum | Yes | TRENDING, RANGING, VOLATILE, or QUIET |
| `thinking` | string | Yes | Full chain-of-thought reasoning |
| `analysis` | object | Yes | Trend, momentum, volume analysis |
| `trade_setup` | object | Yes | Entry, stop, target, R/R, levels |
| `action_plan` | object | Yes | Guidance for different trader types |
| `watch_list` | object | Yes | Bullish/bearish signals to monitor |
| `invalidation` | array | Yes | Conditions that kill the thesis |
| `confidence_reasoning` | object | Yes | Supporting factors and concerns |

### Nested Structures

#### `confidence`
```json
{
  "score": 0.75,
  "reasoning": "High confidence (0.75) in WAIT - volume at 0.56x average with no spike in 43 days suggests fragile rally. Testing EMA50 resistance at $134.93 with poor 0.88:1 risk/reward."
}
```

#### `analysis.trend`
```json
{
  "direction": "BULLISH",
  "strength": "MODERATE",
  "detail": "Price above EMA20 ($133) and rallied 9% from $123 to $134. However, now testing EMA50 resistance with weak volume (0.56x avg) suggesting fragility."
}
```

#### `trade_setup`
```json
{
  "viability": "WAIT",
  "entry": 128.50,
  "stop_loss": 125.00,
  "take_profit": 138.00,
  "risk_reward": 2.71,
  "support": 128.50,
  "resistance": 135.00,
  "current_price": 134.25,
  "timeframe": "3-5 days"
}
```

---

## Usage in Code

### Basic Implementation

```python
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    temperature=0.3,
    messages=[
        {"role": "user", "content": your_prompt_here}
    ],
    extra_headers={
        "anthropic-beta": "structured-outputs-2025-11-13"
    },
    extra_body={
        "output_format": {
            "type": "json_schema",
            "schema": TECHNICAL_ANALYSIS_SCHEMA
        }
    }
)

# Guaranteed valid JSON
analysis_json = response.content[0].text
analysis = json.loads(analysis_json)
```

### With Retry Logic (Optional)

While structured outputs guarantee valid JSON, you might still want retry logic for network errors:

```python
import time
from anthropic import APIError

def get_technical_analysis(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
                extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
                extra_body={
                    "output_format": {
                        "type": "json_schema",
                        "schema": TECHNICAL_ANALYSIS_SCHEMA
                    }
                }
            )
            
            # No JSON parsing errors possible with structured outputs
            return json.loads(response.content[0].text)
            
        except APIError as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
```

---

## Schema Customization

### If You Want to Add Fields

Add them to the schema:

```python
"properties": {
    # ... existing fields ...
    "risk_score": {
        "type": "number",
        "minimum": 0,
        "maximum": 10,
        "description": "Overall risk score 0-10"
    }
},
"required": [
    # ... existing required fields ...
    "risk_score"
]
```

### If You Want to Make Fields Optional

Remove them from the `required` array:

```python
"required": [
    "recommendation_signal",
    "confidence",
    "market_condition",
    # "thinking",  # Now optional
    # "invalidation",  # Now optional
    # ... other required fields
]
```

### If You Want to Add Enum Values

Expand the enum list:

```python
"recommendation_signal": {
    "type": "string",
    "enum": ["BUY", "SELL", "HOLD", "WAIT", "STRONG_BUY", "STRONG_SELL"],
    "description": "Primary trading recommendation"
}
```

---

## Testing Your Schema

### Validate Schema Structure

```python
import jsonschema

# Test that your schema is valid JSON Schema
try:
    jsonschema.Draft7Validator.check_schema(TECHNICAL_ANALYSIS_SCHEMA)
    print("✓ Schema is valid")
except jsonschema.exceptions.SchemaError as e:
    print(f"✗ Schema error: {e}")
```

### Test Against Sample Output

```python
sample_output = {
    "recommendation_signal": "WAIT",
    "confidence": {
        "score": 0.65,
        "reasoning": "Moderate confidence due to conflicting signals..."
    },
    # ... rest of output
}

try:
    jsonschema.validate(instance=sample_output, schema=TECHNICAL_ANALYSIS_SCHEMA)
    print("✓ Sample output matches schema")
except jsonschema.exceptions.ValidationError as e:
    print(f"✗ Validation error: {e}")
```

---

## Common Schema Issues

### Issue 1: `additionalProperties` Warning

**Problem**: If you forget `"additionalProperties": False`, Claude might add unexpected fields.

**Solution**: Always include it at every nested object level:
```python
"confidence": {
    "type": "object",
    "properties": { ... },
    "additionalProperties": False  # ← Important
}
```

### Issue 2: Missing Required Fields

**Problem**: Claude might try to omit fields you expect.

**Solution**: Be explicit in your `required` array and in your prompt:
```
All fields in the schema are required. Do not omit any fields.
```

### Issue 3: Type Mismatches

**Problem**: String where number expected, etc.

**Solution**: Structured outputs prevent this entirely - the API enforces types.

---

## Migration Note

Your current code has this fallback:

```python
state['technical'] = {
    'timestamp': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    'recommendation_signal': 'HOLD',
    'confidence': {
        'score': 0.3,
        'reasoning': f'Technical analysis failed - {str(e)[:100]}...'
    },
    # ...
}
```

With structured outputs, **you can delete this entirely**. The API guarantees valid output, so this fallback never triggers.

---

## Next Steps

1. Copy `TECHNICAL_ANALYSIS_SCHEMA` into your `technical.py` file
2. See `03_REFACTORED_CODE.md` for the complete implementation
3. Test with real market data
4. Compare outputs with your current system

---

## References

- [JSON Schema Reference](https://json-schema.org/understanding-json-schema/)
- [Anthropic Structured Outputs Docs](https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs)
