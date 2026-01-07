
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
import re
from datetime import datetime, timezone
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.database.data_manager import DataManager

#(Technical 50%, News 35%, Reflection 15%)

SYSTEM_PROMPT = """You are the CHIEF TRADING OFFICER making final decisions on SOLANA (SOL/USDT) swing trades.

You have 20 years of experience synthesizing multi-analyst inputs into profitable trading decisions. Your specialty is crypto swing trading where both technical timing and news catalysts matter.

Your role:
- Synthesize 3 expert analyses: Technical, News, Reflection
- Weight their inputs appropriately (Technical 40%, News 30%, Reflection 30%)
- Make clear BUY/SELL/HOLD decisions with specific execution plans
- Explain HOW you weighed each analyst's opinion
- Identify when to override one analyst based on others

Your philosophy:
- Technical analysis drives TIMING (when to enter/exit)
- News analysis drives CONVICTION (catalysts that justify the trade)
- Reflection analysis catches BLIND SPOTS (what everyone missed)
- HOLD is not failure - it's discipline when edge is unclear
- Position sizing reflects uncertainty (lower confidence = smaller size)

You are decisive, risk-aware, and always explain your reasoning clearly.
"""


TRADER_PROMPT = """
<technical_analysis>
Technical Recommendation: {tech_recommendation}
TechnicalConfidence: {tech_confidence:.2%}
Technical Timeframe: {tech_timeframe}

Entry: ${tech_entry} | Stop: ${tech_stop} | Target: ${tech_target}

Technical Summary: {tech_summary}

Analysis:
{tech_analysis}

Action Plan:
{tech_action_plan}

Watch List:
{tech_watchlist}
</technical_analysis>

<sentiment_analysis>
Sentiment: {sentiment_score:.2%} ({sentiment_label})
News Confidence: {sentiment_confidence:.2%}

Key Events:
{sentiment_key_events}

Risk Flags:
{sentiment_risk_flags}

News Reasoning: {news_reasoning}

News Summary: {sentiment_summary}

What to Watch: {sentiment_watch}

Invalidation: {sentiment_invalidation}
</sentiment_analysis>

<reflection_analysis>
Reflection Recommendation: {reflection_recommendation}
Reflection Confidence: {reflection_confidence:.2%}

Agreement Analysis:
{reflection_agreement}

Blind Spots Found:
{reflection_blindspots}

Risk Assessment:
{reflection_risk}

Monitoring Plan:
{reflection_monitoring}

Reflection Reasoning: {reflection_reasoning}
</reflection_analysis>


<decision_framework>
YOUR RESPONSE MUST USE THIS EXACT FORMAT:

<thinking>

PHASE 1: CONSENSUS CHECK
Look at the three recommendations:
- Technical says: {tech_recommendation} (confidence: {tech_confidence:.0%})
- News says: {sentiment_label} (confidence: {sentiment_confidence:.0%})
- Reflection says: {reflection_recommendation} (confidence: {reflection_confidence:.0%})

Do they agree or conflict?
- ALL 3 ALIGN (same direction) = STRONG CONSENSUS
- 2 OUT OF 3 ALIGN = MODERATE CONSENSUS  
- ALL DISAGREE = NO CONSENSUS → likely HOLD

Write 2-3 sentences describing the consensus situation and what it means.
Example: "Technical recommends BUY with high confidence (0.72), News is BULLISH (0.65), but Reflection urges HOLD (0.57) due to volume concerns. This is MODERATE CONSENSUS - two analysts favor long, one is cautious. The disagreement centers on whether weak volume invalidates the bullish setup."


PHASE 2: WEIGHTED CONFIDENCE CALCULATION
Calculate the weighted average using crypto swing trading weights:
- Technical weight: 40% (timing is critical for swing trades)
- News weight: 30% (crypto overreacts to news/catalysts)
- Reflection weight: 30% (synthesis + blind spot detection)

Formula: (0.40 × {tech_confidence}) + (0.30 × {sentiment_confidence}) + (0.30 × {reflection_confidence})

Show your calculation step-by-step.
Example: "(0.40 × 0.72) + (0.30 × 0.65) + (0.30 × 0.57) = 0.36 + 0.23 + 0.09 = 0.68"

Write 1-2 sentences explaining what this weighted confidence means.


PHASE 3: ANALYSE EACH ANALYST'S CONTRIBUTION
Go through each analyst and explain:

A) TECHNICAL ANALYST:
- What's their strongest signal? (volume, momentum, support/resistance?)
- Did they provide valid entry/stop/target levels?
- What did they miss that other analysts caught?
- How much do you trust their recommendation? (High/Medium/Low)

B) NEWS ANALYST:
- Are there real catalysts (partnerships, upgrades) or just hype?
- Any critical risk flags (hacks, regulatory, network issues)?
- How credible are the news sources?
- Does news support or contradict the technical setup?

C) REFLECTION ANALYST:
- What blind spots did they identify?
- Is their risk assessment valid?
- Did they find something both Technical and News missed?
- Should their caution override the bullish/bearish case?

Write 2-3 sentences for EACH analyst explaining your assessment.


PHASE 4: RESOLVE CONFLICTS & DECIDE DIRECTION
If analysts disagree, resolve it:
- Which analyst has stronger evidence?
- Does Technical's chart setup override News concerns? Or vice versa?
- Is Reflection's caution justified by real risks?
- What's the path of least regret?

Based on the weighted confidence and conflict resolution:
- If weighted confidence ≥0.65 and 2+ analysts agree → BUY/SELL
- If weighted confidence 0.50-0.65 and moderate consensus → BUY/SELL with caution
- If weighted confidence <0.50 OR no consensus → HOLD

Write 2-3 sentences explaining your final direction decision.
Example: "Technical and News both point bullish with strong evidence (chart breakout + institutional catalysts). Reflection's volume concern is valid but not a dealbreaker - we can manage this with reduced position size. Weighted confidence of 0.68 justifies a BUY decision with 50% position sizing."


PHASE 5: BUILD EXECUTION PLAN
Now that you've decided on direction, create the execution plan:

ENTRY TIMING:
- Should we enter NOW or WAIT for a better setup?
- If wait, what are the conditions? (price level, volume confirmation, time window)
- Be specific: "Enter within 2-4h if price dips to $184" or "Wait for volume >1.5x"

POSITION SIZE:
- Based on confidence: >0.75 = 70-100%, 0.65-0.75 = 50-70%, 0.50-0.65 = 30-50%, <0.50 = 0% (HOLD)
- Adjust for risks: if Reflection flags high risk, reduce by 20%

PRICE LEVELS:
- Use Technical's entry/stop/target if they're valid
- If Technical has no levels but recommends BUY/SELL → HOLD instead (can't trade without levels)
- Validate: Is stop within 5% of entry? Is R/R ratio >1.5:1?

TIMEFRAME:
- Review Technical's suggested timeframe ({tech_timeframe})
- Adjust based on conviction: High confidence (>0.75) = hold full duration, Medium confidence (0.50-0.75) = shorter hold or take profits early
- Consider news catalysts: If time-sensitive event coming (partnership launch, upgrade), update the timeframe accordingly
- Specify exact days: "3-5 days" or "Hold until $198 target OR 5 days maximum, whichever comes first"

Write 3-4 sentences detailing the exact execution plan.

</thinking>


<answer>
{{
  "decision": "BUY|SELL|HOLD",
  "confidence": 0.68,
  "reasoning": "Technical breakout + institutional catalysts (CME, Ondo Finance) create compelling bullish case with 0.68 weighted confidence. Weak volume concern from Reflection is managed via 50% position sizing. Entry at $184 offers 1.8:1 R/R with clear invalidation at $176.",
  
  "agent_synthesis": {{
    "technical_weight": 0.50,
    "news_weight": 0.35,
    "reflection_weight": 0.15,
    "weighted_confidence": 0.68,
    "agreement_summary": "Technical (BUY, 0.72) and News (BULLISH, 0.65) strongly align on bullish direction due to chart breakout above EMA50 and major institutional partnerships (CME futures, Ondo tokenization). Reflection (HOLD, 0.57) provides valuable caution, flagging weak volume (0.82x) and network reliability risks that Technical/News underweighted. The core disagreement is risk tolerance: Tech/News see opportunity, Reflection sees insufficient conviction. Weighted analysis (0.68) favors the bullish case but incorporates Reflection's risk management via reduced position size.",
    "technical_contribution": "Provides clear entry/stop/target levels with strong chart setup (EMA50 breakout, MACD positive). Most reliable for TIMING the trade. Trust level: HIGH - signals are clear and actionable.",
    "news_contribution": "Identifies genuine institutional catalysts (not hype) - CME and Ondo partnerships are material positives. Balances with liquidity concerns. Trust level: MEDIUM-HIGH - sources credible but slightly dated.",
    "reflection_contribution": "Critical blind spot detection: caught weak volume issue that Technical mentioned but didn't emphasize enough. Risk assessment is valid and prevents overconfidence. Trust level: MEDIUM - sometimes overly cautious but provides necessary balance."
  }},
  
  "execution_plan": {{
    "entry_timing": "Enter within next 2-4 hours if price dips to $182-184 (EMA20 support zone). If price stays above $186, wait for either: (1) volume surge above 1.5x to confirm rally, OR (2) pullback to support. Do NOT chase at current price - patience is key.",
    "position_size": "50%",
    "entry_price_target": 184.00,
    "stop_loss": 176.00,
    "take_profit": 198.00,
    "timeframe": "3-5 days",
    "risk_reward_ratio": "1.75:1"
  }},
  
  "risk_management": {{
    "max_loss_per_trade": "2%",
    "primary_risk": "Weak volume (0.82x average) means rally lacks institutional conviction and could reverse sharply on any negative catalyst",
    "secondary_risks": [
      "Network reliability concerns from recent 2-hour outage",
      "Price 8% above EMA50 - technically extended",
      "Declining TVL suggests ecosystem weakness"
    ],
    "exit_conditions": [
      "IMMEDIATE EXIT: Break and close below $176 (invalidates setup)",
      "24H EXIT: Volume stays <1.0x for 48 hours straight (no conviction)",
      "PROFIT TAKE: Hit $198 target OR 48 hours passed with no momentum"
    ],
    "monitoring_checklist": [
      "Volume MUST surge above 1.5x within 48h to validate bullish thesis",
      "Price MUST hold $184 (EMA20) on any pullback",
      "Watch for Visa/Ondo partnership implementation news",
      "Monitor Solana network status for any new outages",
      "Track buy pressure - needs to stay above 50%"
    ]
  }}
}}
</answer>

</decision_framework>

<critical_rules>
1. If NO CONSENSUS (all 3 disagree) → MUST return HOLD
2. If weighted_confidence <0.50 → MUST return HOLD
3. If Technical has NO entry/stop/target but recommends BUY/SELL → MUST return HOLD
4. If News has critical risk_flags like "exchange delisting" or "SEC lawsuit" → MUST return HOLD
5. Position size MUST match confidence: <0.50=0%, 0.50-0.65=30-50%, 0.65-0.75=50-70%, >0.75=70-100%
6. agent_synthesis.agreement_summary MUST be 4-6 sentences explaining how all 3 analysts align or conflict
7. Always show the weighted confidence calculation in thinking
8. Be specific with entry_timing - include conditions and price levels
9. monitoring_checklist is MANDATORY - traders need to know what to watch
10. If decision is HOLD, set entry_price_target, stop_loss, take_profit to null
</critical_rules>
"""

class TraderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.2  # Low temp for consistent decision-making
        )

    def execute(self, state: AgentState) -> AgentState:
        technical = state.get('technical', {})
        tech_recommendation = technical.get('recommendation_signal', 'HOLD')

        tech_confidence_obj = technical.get('confidence', {})
        if isinstance(tech_confidence_obj, dict):
            tech_confidence = tech_confidence_obj.get('setup_quality', 0.5)
        else:
            tech_confidence = float(tech_confidence_obj) if tech_confidence_obj else 0.5

        trade_setup = technical.get('trade_setup', {})
        tech_timeframe = trade_setup.get('timeframe', 'N/A')
        tech_entry = trade_setup.get('entry')
        tech_stop = trade_setup.get('stop_loss')
        tech_target = trade_setup.get('take_profit')

        tech_summary = technical.get('summary', 'No summary provided')
        tech_watchlist = technical.get('watch_list', {})
        tech_analysis = technical.get('analysis', {})
        tech_action_plan = technical.get('action_plan', {})

        # Format for prompt
        tech_watchlist_formatted = json.dumps(tech_watchlist, indent=2) if tech_watchlist else "No watch list provided"
        tech_analysis_formatted = json.dumps(tech_analysis, indent=2) if tech_analysis else "No analysis provided"
        tech_action_plan_formatted = json.dumps(tech_action_plan, indent=2) if tech_action_plan else "No action plan provided"

        sentiment = state.get('sentiment', {})
        # Use new SentimentAgent schema
        sentiment_signal = sentiment.get('signal', 'NEUTRAL')

        # Handle nested confidence object from Sentiment agent
        sentiment_confidence_obj = sentiment.get('confidence', {})
        if isinstance(sentiment_confidence_obj, dict):
            sentiment_confidence = sentiment_confidence_obj.get('signal_strength', 0.5)
        else:
            sentiment_confidence = float(sentiment_confidence_obj) if sentiment_confidence_obj else 0.5
        sentiment_market_fear_greed = sentiment.get('market_fear_greed', {})
        sentiment_news_data = sentiment.get('news_sentiment', {})
        sentiment_score = float(sentiment_news_data.get('score', 0.5))
        sentiment_label = sentiment_news_data.get('label', 'NEUTRAL')
        sentiment_key_events = sentiment.get('key_events', [])
        sentiment_risk_flags = sentiment.get('risk_flags', [])
        sentiment_summary = sentiment.get('summary', 'No summary provided')
        sentiment_watch = sentiment.get('what_to_watch', [])
        sentiment_invalidation = sentiment.get('invalidation', 'Not specified')

        # Format CFGI data for context
        cfgi_score = sentiment_market_fear_greed.get('score', 50)
        cfgi_classification = sentiment_market_fear_greed.get('classification', 'Neutral')
        cfgi_interpretation = sentiment_market_fear_greed.get('interpretation', 'No CFGI data')
        sentiment_key_events_formatted = '\n'.join([
            f"  - {event.get('title', 'Unknown')} ({event.get('type', 'Unknown')}) - {event.get('impact', 'Unknown')}: {event.get('reasoning', 'No reasoning')}"
            for event in sentiment_key_events[:5] # top 5 only
        ]) if sentiment_key_events else "No key events"
        sentiment_risk_flags_formatted = '\n'.join([f"  - {flag}" for flag in sentiment_risk_flags]) if sentiment_risk_flags else "No risk flags"
        sentiment_watch_formatted = '\n'.join([f"  - {item}" for item in sentiment_watch]) if sentiment_watch else "Nothing specified"

        reflection = state.get('reflection', {})
        reflection_recommendation = reflection.get('recommendation_signal', 'HOLD')

        # Handle nested confidence object from Reflection agent
        reflection_confidence_obj = reflection.get('confidence', {})
        if isinstance(reflection_confidence_obj, dict):
            reflection_confidence = reflection_confidence_obj.get('final_confidence', 0.5)
        else:
            reflection_confidence = float(reflection_confidence_obj) if reflection_confidence_obj else 0.5
        agreement_analysis = reflection.get('agreement_analysis', {})
        reflection_agreement = json.dumps(agreement_analysis, indent=2) if agreement_analysis else "No agreement analysis"
        blind_spots = reflection.get('blind_spots', {})
        reflection_blindspots = json.dumps(blind_spots, indent=2) if blind_spots else "No blind spots identified"        
        risk_assessment = reflection.get('risk_assessment', {})
        reflection_risk = json.dumps(risk_assessment, indent=2) if risk_assessment else "No risk assessment"
        monitoring = reflection.get('monitoring', {})
        reflection_monitoring = json.dumps(monitoring, indent=2) if monitoring else "No monitoring plan"
        reflection_reasoning = reflection.get('final_reasoning', 'No reflection analysis available')


        full_prompt = SYSTEM_PROMPT + "\n\n" + TRADER_PROMPT.format(
            tech_recommendation=tech_recommendation,
            tech_confidence=tech_confidence,
            tech_timeframe=tech_timeframe,
            tech_entry=tech_entry if tech_entry else "N/A",
            tech_stop=tech_stop if tech_stop else "N/A",
            tech_target=tech_target if tech_target else "N/A",
            tech_summary=tech_summary,
            tech_analysis=tech_analysis_formatted,
            tech_action_plan=tech_action_plan_formatted,
            tech_watchlist=tech_watchlist_formatted,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            sentiment_confidence=sentiment_confidence,
            sentiment_key_events=sentiment_key_events_formatted,
            sentiment_risk_flags=sentiment_risk_flags_formatted,
            news_reasoning=sentiment_summary,
            sentiment_summary=sentiment_summary,
            sentiment_watch=sentiment_watch_formatted,
            sentiment_invalidation=sentiment_invalidation,
            reflection_recommendation=reflection_recommendation,
            reflection_confidence=reflection_confidence,
            reflection_agreement=reflection_agreement,
            reflection_blindspots=reflection_blindspots,
            reflection_risk=reflection_risk,
            reflection_monitoring=reflection_monitoring,
            reflection_reasoning=reflection_reasoning
        )

        response = llm(
            full_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=3000
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

            answer_json = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', answer_json)

            trader_data = json.loads(answer_json)
            decision = trader_data.get('decision', 'HOLD').upper()
            if decision not in ['BUY', 'SELL', 'HOLD']:
                print(f"⚠️  Invalid decision '{decision}', defaulting to HOLD")
                decision = 'HOLD'

            confidence = float(trader_data.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1

            trader_data['thinking'] = thinking
            trader_data['decision'] = decision
            trader_data['confidence'] = confidence
            trader_data['timestamp'] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            state['trader'] = trader_data

            with DataManager() as dm:
                dm.save_trader_decision(
                    timestamp=datetime.now(),
                    data=trader_data
                )


        except (json.JSONDecodeError, ValueError) as e:
            print(f"  Trader agent parsing error: {e}")
            print(f"Response preview: {response[:500]}")

            fallback_decision = reflection_recommendation if reflection_recommendation in ['BUY', 'SELL', 'HOLD'] else 'HOLD'
            fallback_confidence = reflection_confidence * 0.8  # Reduce confidence due to error

            state['trader'] = {
                'decision': fallback_decision,
                'confidence': fallback_confidence,
                'reasoning': f"Trader synthesis failed. Defaulting to Reflection recommendation: {reflection_reasoning[:200]}",
                'agent_synthesis': {
                    'technical_weight': 0.50,
                    'news_weight': 0.35,
                    'reflection_weight': 0.15,
                    'weighted_confidence': fallback_confidence,
                    'agreement_summary': f"Parsing error occurred. Using Reflection as fallback.",
                    'technical_contribution': 'Unable to assess due to parsing error',
                    'news_contribution': 'Unable to assess due to parsing error',
                    'reflection_contribution': 'Used as fallback decision'
                },
                'execution_plan': {
                    'entry_timing': 'Wait for valid analysis',
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
                    'exit_conditions': ['Re-run analysis'],
                    'monitoring_checklist': ['Generate new analysis']
                },
                'thinking': f'Error occurred: {str(e)}'
            }

            print(f"  FALLBACK DECISION: {fallback_decision} ({fallback_confidence:.0%})")

        return state

  
if __name__ == "__main__":


    agent = TraderAgent()
    test_state = AgentState()

    test_state['technical'] = {
        'timestamp': '2025-01-02T15:30:00Z',
        'recommendation_signal': 'BUY',
        'confidence': {
            'analysis_confidence': 0.85,
            'setup_quality': 0.65,
            'interpretation': 'High confidence in analysis, good trade setup'
        },
        'market_condition': 'TRENDING',
        'summary': 'Strong bullish setup with volume confirmation and favorable risk/reward ratio.',
        'thinking': [
            "Market story: Price breaking above EMA50 resistance with institutional volume",
            "Volume assessment: 1.8x average confirms breakout strength",
            "Risk analysis: Support at $142.50 provides clear invalidation level"
        ],
        'analysis': {
            'trend': {
                'direction': 'BULLISH',
                'strength': 'STRONG',
                'detail': 'Price breaking above EMA50 resistance at $145.20 with MACD crossover'
            },
            'momentum': {
                'direction': 'BULLISH',
                'strength': 'MODERATE',
                'detail': 'RSI at 68 (healthy range, not overbought) with upward momentum'
            },
            'volume': {
                'quality': 'STRONG',
                'ratio': 1.8,
                'detail': 'Volume surge of 1.8x average indicates institutional interest'
            }
        },
        'trade_setup': {
            'viability': 'VALID',
            'entry': 145.50,
            'stop_loss': 142.00,
            'take_profit': 155.00,
            'risk_reward': 3.2,
            'support': 142.50,
            'resistance': 145.20,
            'current_price': 145.50,
            'timeframe': '3-7 days'
        },
        'action_plan': {
            'primary': 'Enter long at $145.50',
            'alternative': 'Wait for pullback to $144',
            'if_in_position': 'Hold with trailing stop at $142',
            'avoid': "Don't chase above $147"
        },
        'watch_list': {
            'next_24h': ["Daily volume stays >1.5x average", "RSI maintains above 60", "Price holds above $144 support"],
            'next_48h': ["Break above $147 resistance", "Volume confirms continuation", "MACD stays positive"]
        },
        'invalidation': [
            "Break below $142 (stop loss)",
            "Volume drops below 0.8x average for 12h",
            "RSI falls below 50 with negative MACD"
        ],
        'confidence_reasoning': {
            'supporting': ["Strong volume confirmation", "Clear trend with MACD crossover", "Favorable R:R of 3.2:1"],
            'concerns': ["RSI at 68 leaves limited upside room", "Need sustained volume to confirm breakout"],
            'assessment': "High probability setup with strong technical confirmation and manageable risk"
        },
        'thinking': 'Analyzed price action and indicators. Volume confirms institutional interest.'
    }

    test_state['sentiment'] = {
        'signal': 'SLIGHTLY_BULLISH',
        'recommendation_signal': 'HOLD',
        'confidence': {
            'analysis_confidence': 0.80,
            'signal_strength': 0.62,
            'interpretation': 'High confidence in analysis, moderate bullish signal'
        },
        'market_fear_greed': {
            'score': 55,
            'classification': 'Neutral',
            'social': 98.5,
            'whales': 26.5,
            'trends': 88.5,
            'interpretation': 'Retail excitement without institutional backing'
        },
        'news_sentiment': {
            'score': 0.62,
            'label': 'SLIGHTLY_BULLISH',
            'catalysts_count': 2,
            'risks_count': 1
        },
        'all_recent_news': [
            {'title': 'Ondo Finance Tokenized Stocks on Solana', 'published_at': '2025-12-15T15:49:41', 'url': 'https://www.coindesk.com/business/2025/12/15/ondo-finance-to-offer-tokenized-u-s-stocks-etfs-on-solana-early-next-year', 'source': 'CoinDesk'},
            {'title': 'CME Group Solana Futures', 'published_at': '2025-12-15T16:07:00', 'url': 'https://www.coindesk.com/markets/2025/12/15/cme-group-expands-crypto-derivatives-with-spot-quoted-xrp-and-solana-futures', 'source': 'CoinDesk'}
        ],
        'key_events': [
            {'title': 'Ondo Finance Tokenized Stocks on Solana', 'published_at': '2025-12-15T15:49:41', 'url': 'https://www.coindesk.com/business/2025/12/15/ondo-finance-to-offer-tokenized-u-s-stocks-etfs-on-solana-early-next-year', 'type': 'PARTNERSHIP', 'source_credibility': 'REPUTABLE', 'news_age_hours': 12, 'impact': 'BULLISH', 'reasoning': "Expanding Solana's real-world asset tokenization capabilities"},
            {'title': 'CME Group Solana Futures', 'published_at': '2025-12-15T16:07:00', 'url': 'https://www.coindesk.com/markets/2025/12/15/cme-group-expands-crypto-derivatives-with-spot-quoted-xrp-and-solana-futures', 'type': 'PARTNERSHIP', 'source_credibility': 'REPUTABLE', 'news_age_hours': 12, 'impact': 'BULLISH', 'reasoning': 'Institutional derivatives product increases SOL legitimacy'},
            {'title': 'Solana Liquidity Challenges', 'published_at': '2025-12-10T05:03:08', 'url': 'https://decrypt.co/351743/solana-liquidity-plummets-bear-level-500m-liquidation-overhang', 'type': 'ECOSYSTEM', 'source_credibility': 'REPUTABLE', 'news_age_hours': 120, 'impact': 'BEARISH', 'reasoning': 'Declining Total Value Locked and memecoin demand weakness'}
        ],
        'risk_flags': ['Declining Total Value Locked', 'Liquidity challenges in ecosystem'],
        'summary': "News presents a cautiously bullish 0.62 sentiment. CME futures and Ondo Finance partnerships provide strong institutional validation, offsetting recent liquidity concerns. Traders should maintain positions but with reduced size, watching for network stability and further institutional adoption signals.",
        'what_to_watch': ['Ondo Finance tokenization launch details', 'CME Solana futures trading volume', 'Total Value Locked trend'],
        'invalidation': "Sustained decline in TVL below current levels OR failure to generate meaningful institutional product adoption.",
        'suggested_timeframe': '3-5 days',
        'thinking': 'Analyzed news events and sentiment. Institutional catalysts are positive.',
        'timestamp': '2025-01-02T15:30:00Z'
    }

    test_state['reflection'] = {
        'recommendation_signal': 'HOLD',
        'confidence': {
            'analysis_confidence': 0.80,
            'final_confidence': 0.57,
            'interpretation': 'High confidence in synthesis, moderate final confidence due to risks'
        },
        'agreement_analysis': {
            'alignment_status': 'PARTIAL',
            'alignment_score': 0.75,
            'explanation': "Technical and news both show bullish potential, but with significant reservations."
        },
        'blind_spots': {
            'technical_missed': [
                "Network reliability risks",
                "Potential security vulnerabilities"
            ],
            'news_missed': [
                "Strong momentum signals",
                "Institutional volume interest"
            ]
        },
        'risk_assessment': {
            'primary_risk': "Network infrastructure concerns could rapidly undermine bullish momentum",
            'risk_level': 'MEDIUM',
            'risk_score': 0.55
        },
        'monitoring': {
            'watch_next_24h': [
                "Institutional partnership implementation details",
                "Network performance metrics",
                "Volume confirmation above 1.5x average"
            ],
            'invalidation_triggers': ["Sustained network performance issues", "Partnership delay announcements"]
        },
        'reasoning': "Technical momentum and institutional catalysts (CME, Ondo Finance) create a compelling bullish setup. However, ecosystem liquidity challenges require caution. Key success factors: volume sustains, TVL stabilizes, institutional products gain adoption.",
        'thinking': 'Synthesized technical and news analyses. Found alignment but with caution.'
    }

    result = agent.execute(test_state)

    if result.get('trader'):
        trader = result['trader']
        print("\n" + "="*70)
        print("TRADER AGENT OUTPUT")
        print("="*70)
        print(trader)
    else:
        print("\nTEST FAILED: No trader output")

