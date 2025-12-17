"""
Reflection Agent - Cross-Analysis & Final Decision
Single LLM call that synthesizes technical + news analysis
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.database.data_manager import DataManager


SYSTEM_PROMPT = """You are a SENIOR TRADING STRATEGIST with 20 years experience reviewing analysis from technical and news analysts.

Your job:
- Compare technical vs news recommendations
- Find what each analyst missed (blind spots)
- Identify the PRIMARY RISK
- Make final BUY/SELL/HOLD decision

Your style: Honest, risk-focused, decisive, actionable.
"""


REFLECTION_PROMPT = """
<technical_analysis>
Recommendation: {tech_recommendation}
Confidence: {tech_confidence}
Entry: ${tech_entry} | Stop: ${tech_stop} | Target: ${tech_target}
Key Signals:
{tech_key_signals}

Reasoning: {tech_reasoning}

Summary: {tech_summary}

Watch List:
{tech_watchlist}

Confidence Breakdown:
{tech_confidence_breakdown}
</technical_analysis>

<news_analysis>
Sentiment: {news_sentiment} ({news_label})
Confidence: {news_confidence}

Key Events:
{news_key_events}

Event Summary:
{news_event_summary}

Risk Flags:
{news_risk_flags}

Reasoning: {news_reasoning}

Summary: {news_summary}

What to Watch:
{news_watch}

Invalidation: {news_invalidation}
</news_analysis>

<analysis_framework>
YOUR RESPONSE MUST USE THIS EXACT FORMAT:

<thinking>

PHASE 1: DO THEY AGREE OR CONFLICT?
Compare the recommendations:
- Technical says: [BUY/SELL/HOLD] with [X]% confidence
- News says: [BULLISH/BEARISH/NEUTRAL] with [X]% confidence
- Agreement: ALIGNED | PARTIAL | CONFLICTED

If both bullish (or both bearish) = ALIGNED
If one says BUY, other says SELL = CONFLICTED
If one neutral, other directional = PARTIAL

Calculate alignment score (0.0 to 1.0):
- ALIGNED = 0.8-1.0
- PARTIAL = 0.4-0.7
- CONFLICTED = 0.0-0.3

Write 2 sentences explaining the alignment.


PHASE 2: WHAT DID TECHNICAL MISS?
Look at the news analysis and ask:
- Did news mention any RISK FLAGS (hacks, regulatory, network issues)?
- Are there positive catalysts (partnerships, upgrades) technical didn't see?
- Is there a critical event that changes the technical setup?

List 2-3 things technical analysis overlooked from news.


PHASE 3: WHAT DID NEWS MISS?
Look at the technical analysis and ask:
- Did technical flag WEAK VOLUME that news ignored?
- Are there chart warnings (overbought, divergence, overextended)?
- Is the entry point risky (far from support)?

List 2-3 things news analysis overlooked from technical.


PHASE 4: WHAT'S THE PRIMARY RISK?
Combine both views and identify the BIGGEST threat:
- If both bullish: What could kill this trade?
- If conflicting: Which has stronger evidence?
- What's worst-case in next 24-48h?

Risk level: LOW | MEDIUM | HIGH
Write 2 sentences describing the primary risk.


PHASE 5: FINAL DECISION
Based on everything above:
- Start with the LOWER confidence of the two
- Adjust up if aligned (+10%)
- Adjust down if conflicted (-20%)
- Adjust down if high risk (-15%)

Final confidence = [calculated value]
Final recommendation = BUY | SELL | HOLD
Position size = [% based on confidence]

Write 2 sentences explaining your final decision.

</thinking>


<answer>
{{
  "recommendation": "BUY|SELL|HOLD",
  "confidence": 0.68,
  "agreement_analysis": {{
    "alignment_status": "ALIGNED|PARTIAL|CONFLICTED",
    "alignment_score": 0.75,
    "explanation": "Both technical and news are bullish, but news has liquidity concerns."
  }},

  "blind_spots": {{
    "technical_missed": [
      "Network outage risk mentioned in news",
      "Visa partnership provides fundamental catalyst"
    ],
    "news_missed": [
      "Volume is weak at 0.82x average - rally lacks conviction",
      "Price 8% above EMA50, getting overextended"
    ]
  }},

  "risk_assessment": {{
    "primary_risk": "Weak volume despite bullish setup - rally could reverse if conviction doesn't improve",
    "risk_level": "MEDIUM",
    "risk_score": 0.55
  }},

  "monitoring": {{
    "watch_next_24h": [
      "Volume must increase above 1.2x to validate rally",
      "Price must hold above $184 (EMA20 support)",
      "Watch for any network stability issues"
    ],
    "invalidation_trigger": "Break below $184 or volume stays weak <1.0x for 48h"
  }},

  "confidence_calculation": {{
    "starting_confidence": 0.62,
    "alignment_bonus": 0.10,
    "risk_penalty": -0.15,
    "confidence": 0.57,
    "reasoning": "Started with news confidence (lower of the two), added alignment bonus, subtracted for weak volume risk"
  }},

  "reasoning": "Technical and news both point bullish, giving us directional confidence. However, weak volume (0.82x) and network reliability concerns reduce conviction. Key watch: volume must surge above 1.2x within 48h to validate this move."
}}
</answer>

Do NOT write ANYTHING before the <thinking> tag or after the </answer> tag. you answer tag should exactly match the above answer tag 

</analysis_framework>

<critical_rules>
1. Always start with the LOWER confidence between technical and news
2. If alignment_score <0.4, reduce confidence by at least 20%
3. If risk_level is HIGH, reduce confidence accordingly
4. If final_confidence <0.5, always recommend HOLD
5. monitoring section is MANDATORY - traders need to know what to watch
6. Keep final_reasoning to 2-3 sentences maximum
7. Be specific with numbers (prices, percentages, timeframes)
</critical_rules>
"""


class ReflectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.3
        )

    def execute(self, state: AgentState) -> AgentState:
        tech = state.get('technical', {})
        tech_recommendation = tech.get('recommendation', 'HOLD')
        tech_confidence = tech.get('confidence', 0.5)
        tech_entry = tech.get('entry_level', 0)
        tech_stop = tech.get('stop_loss', 0)
        tech_target = tech.get('take_profit', 0)
        tech_key_signals = tech.get('key_signals', [])
        tech_reasoning = tech.get('reasoning', 'No reasoning provided')
        tech_summary = tech.get('recommendation_summary', 'No summary provided')
        tech_watchlist = tech.get('watch_list', {})
        tech_confidence_breakdown = tech.get('confidence_breakdown', {})

        news = state.get('news', {})
        news_sentiment = news.get('overall_sentiment', 0.5)
        news_label = news.get('sentiment_label', 'NEUTRAL')
        news_confidence = news.get('confidence', 0.5)
        news_key_events = news.get('key_events', [])
        news_event_summary = news.get('event_summary', {})
        news_risk_flags = news.get('risk_flags', [])
        news_reasoning = news.get('reasoning', 'No reasoning provided')
        news_summary = news.get('recommendation_summary', 'No summary provided')
        news_watch = news.get('what_to_watch', [])
        news_invalidation = news.get('invalidation', 'Not specified')

        tech_key_signals_formatted = '\n'.join([f"  - {signal}" for signal in tech_key_signals])
        
        tech_watchlist_formatted = json.dumps(tech_watchlist, indent=2) if tech_watchlist else "No watch list provided"
        
        tech_confidence_breakdown_formatted = json.dumps(tech_confidence_breakdown, indent=2) if tech_confidence_breakdown else "No breakdown provided"
        news_key_events_formatted = '\n'.join([
            f"  - {event.get('title', 'Unknown')} ({event.get('type', 'Unknown')}) - {event.get('impact', 'Unknown')}"
            for event in news_key_events[:5]  # Limit to top 5 events
        ]) if news_key_events else "No key events"
        
        news_event_summary_formatted = json.dumps(news_event_summary, indent=2) if news_event_summary else "No summary"
        news_risk_flags_formatted = '\n'.join([f"  - {flag}" for flag in news_risk_flags]) if news_risk_flags else "No risk flags"
        news_watch_formatted = '\n'.join([f"  - {item}" for item in news_watch]) if news_watch else "Nothing specified"

  
        full_prompt = SYSTEM_PROMPT + "\n\n" + REFLECTION_PROMPT.format(
            tech_recommendation=tech_recommendation,
            tech_confidence=f"{tech_confidence:.2%}",
            tech_entry=tech_entry if tech_entry else "N/A",
            tech_stop=tech_stop if tech_stop else "N/A",
            tech_target=tech_target if tech_target else "N/A",
            tech_key_signals=tech_key_signals_formatted,
            tech_reasoning=tech_reasoning,
            tech_summary=tech_summary,
            tech_watchlist=tech_watchlist_formatted,
            tech_confidence_breakdown=tech_confidence_breakdown_formatted,
            news_sentiment=f"{news_sentiment:.2%}",
            news_label=news_label,
            news_confidence=f"{news_confidence:.2%}",
            news_key_events=news_key_events_formatted,
            news_event_summary=news_event_summary_formatted,
            news_risk_flags=news_risk_flags_formatted,
            news_reasoning=news_reasoning,
            news_summary=news_summary,
            news_watch=news_watch_formatted,
            news_invalidation=news_invalidation
        )

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=2500
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
            
            answer_json = answer_json.replace('"', '"').replace('"', '"')
            answer_json = answer_json.replace(''', "'").replace(''', "'")
            
            first_brace = answer_json.find('{')
            last_brace = answer_json.rfind('}')
            if first_brace != -1 and last_brace != -1:
                answer_json = answer_json[first_brace:last_brace+1]

            reflection_data = json.loads(answer_json)
            reflection_data['thinking'] = thinking

            state['reflection'] = reflection_data

            dm = DataManager()
            dm.save_reflection_analysis(data=reflection_data)

            print("✅ Reflection agent completed successfully")

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Reflection agent parsing error: {e}")
            print(f"Response preview: {response[:500]}")

            # Fallback: Create minimal reflection output
            state['reflection'] = {
                'recommendation': tech_recommendation,
                'confidence': min(tech_confidence, news_confidence) * 0.8,
                'agreement_analysis': {
                    'alignment_status': 'UNKNOWN',
                    'alignment_score': 0.5,
                    'explanation': 'Parsing error - using fallback analysis'
                },
                'blind_spots': {
                    'technical_missed': ['Unable to analyze due to parsing error'],
                    'news_missed': ['Unable to analyze due to parsing error']
                },
                'risk_assessment': {
                    'primary_risk': f'Analysis error: {str(e)[:100]}',
                    'risk_level': 'HIGH',
                    'risk_score': 0.8
                },
                'monitoring': {
                    'watch_next_24h': ['Re-run analysis'],
                    'invalidation_trigger': 'N/A'
                },
                'confidence_calculation': {
                    'starting_confidence': min(tech_confidence, news_confidence),
                    'alignment_bonus': 0.0,
                    'risk_penalty': -0.2,
                    'confidence': min(tech_confidence, news_confidence) * 0.8,
                    'reasoning': 'Fallback due to parsing error'
                },
                'reasoning': f'Reflection analysis failed due to parsing error. Defaulting to conservative HOLD recommendation. Error: {str(e)[:100]}',
                'thinking': f'Error occurred during analysis: {str(e)}'
            }

        return state


if __name__ == "__main__":
    # Test with sample state
    agent = ReflectionAgent()
    test_state = AgentState({
        'technical': {
            'recommendation': 'BUY',
            'confidence': 0.72,
            'timeframe': '3-5 days',
            'key_signals': [
                "Price breaking above EMA50 resistance at $145.20",
                "Volume surge of 1.8x average (institutional interest)",
                "MACD crossover indicating upward trend continuation"
            ],
            'entry_level': 145.50,
            'stop_loss': 142.00,
            'take_profit': 155.00,
            'reasoning': "Strong bullish setup with volume confirmation",
            'confidence_breakdown': {
                'trend_strength': 0.75,
                'momentum_confirmation': 0.80,
                'volume_quality': 0.85,
                'risk_reward': 0.60
            },
            'recommendation_summary': 'Enter long at $145.50, stop at $142, target $155. Good R/R ratio.',
            'watch_list': {
                'confirmation_signals': ["Volume stays above 1.5x", "Price holds EMA50"],
                'invalidation_signals': ["Break below $142"]
            }
        },
        'news': {
            'overall_sentiment': 0.65,
            'sentiment_label': 'NEUTRAL-BULLISH',
            'confidence': 0.62,
            'key_events': [
                {'title': 'Visa partners with Solana', 'type': 'PARTNERSHIP', 'impact': 'BULLISH'},
                {'title': 'Network slowdown reported', 'type': 'SECURITY', 'impact': 'BEARISH'}
            ],
            'event_summary': {
                'actionable_catalysts': 2,
                'hype_noise': 1,
                'critical_risks': 1
            },
            'risk_flags': ['Network reliability concerns'],
            'reasoning': "Positive partnerships offset by technical issues",
            'recommendation_summary': 'Cautiously bullish - institutional adoption vs network concerns',
            'what_to_watch': ['Visa partnership launch', 'Network stability'],
            'invalidation': 'Major network outage or partnership delay'
        }
    })

    result = agent.execute(test_state)
    print("\n===== REFLECTION AGENT OUTPUT =====")
    reflection = result.get('reflection', {})
    print(json.dumps(reflection, indent=2))