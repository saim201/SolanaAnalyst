from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from agents.llm import llm
from agents.formatter import LLMDataFormatter
from agents.db_fetcher import DataQuery
from database.config import get_db_session
from database.models import TradeDecision


def fetch_trade_history_from_db(limit: int = 10) -> str:
    try:
        db = get_db_session()
        trades = db.query(TradeDecision).order_by(TradeDecision.timestamp.desc()).limit(limit).all()
        db.close()

        if not trades:
            return "No trading history yet. Starting fresh."

        trades = list(reversed(trades))

        history_text = "TRADE HISTORY:\n"
        for i, trade in enumerate(trades, 1):
            history_text += f"{i}. [{trade.timestamp.strftime('%Y-%m-%d %H:%M')}] {trade.decision.upper()} (Confidence: {trade.confidence*100:.0f}%, Action: {trade.action:.2f}) - {trade.reasoning}\n"

        return history_text
    except Exception as e:
        print(f"Error fetching trade history: {str(e)}")
        return "No trading history yet. Starting fresh."


class TradingState(TypedDict):
    indicators_analysis: str
    news_analysis: str
    reflection_analysis: str
    
    reasoning: str
    decision: Literal['buy', 'sell', 'hold']
    confidence: float
    action: float


TECHNICAL_PROMPT = """You are an expert Solana technical analyst specializing in swing trading (3-7 day holds).

{indicators_data}

ANALYSIS REQUIRED:
1. Price Action: Analyze the current price relative to key moving averages (EMA20, EMA50, EMA200)
2. Momentum: Interpret RSI and MACD signals (divergences, extreme readings)
3. Volatility: Assess Bollinger Bands position and ATR for risk management
4. Support/Resistance: Identify key price levels traders are watching
5. Trend: Determine overall trend direction from the 90-day daily candles

PROVIDE YOUR ANALYSIS IN 3-4 SENTENCES covering:
- Current market structure (uptrend, downtrend, consolidation)
- Key technical signals (bullish or bearish indicators)
- Risk/reward assessment using support/resistance levels"""

NEWS_PROMPT = """You are an expert crypto news analyst for Solana trading decisions.

{news_data}

TASK: Analyze recent news sentiment and market catalysts.

PROVIDE YOUR ANALYSIS IN 2-3 SENTENCES covering:
- Overall sentiment from recent news (positive, negative, neutral)
- Major catalysts or events affecting Solana
- Sentiment strength (weak, moderate, strong)"""

REFLECTION_PROMPT = """You are a trading strategy review agent.

RECENT TRADES:
{trading_history}

TASK: Review recent trading decisions and identify patterns.

PROVIDE ANALYSIS IN 2-3 SENTENCES covering:
- Recent decision accuracy (correct/incorrect bias)
- Confidence calibration assessment
- Pattern recognition from trade history"""

FINAL_DECISION_PROMPT = """You are a senior Solana trading strategist making swing trading decisions.

TECHNICAL ANALYSIS:
{indicators_analysis}

NEWS & SENTIMENT:
{news_analysis}

TRADING STRATEGY REVIEW:
{reflection_analysis}

MAKE YOUR DECISION:
1. Decision: Choose BUY, SELL, or HOLD
2. Confidence: Rate 0-1 (0=uncertain, 1=very confident)
3. Action: Rate -1 to 1 (-1=strong sell, 0=neutral, 1=strong buy)
4. Reasoning: Explain your decision in 2-3 sentences

FORMAT YOUR RESPONSE EXACTLY AS:
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0.0-1.0]
ACTION: [-1.0 to 1.0]
REASONING: [Your explanation]"""


def technical_agent(state: TradingState) -> TradingState:
    llm_data = LLMDataFormatter.format_for_technical_agent()

    current_snapshot = llm_data["current_snapshot"]
    intraday_4h = llm_data["intraday_4h"]
    daily_candles = llm_data["daily_candles"]
    indicators = llm_data["indicators"]

    full_technical_data = f"""TIMESTAMP: {llm_data["timestamp"]}

CURRENT PRICE SNAPSHOT (24h):
Price: ${current_snapshot.get("price", "N/A")}
24h Change: {current_snapshot.get("price_change_24h_percent", "N/A")}%
24h High: ${current_snapshot.get("high_24h", "N/A")}
24h Low: ${current_snapshot.get("low_24h", "N/A")}
24h Volume: {current_snapshot.get("volume_24h", "N/A")}

INTRADAY CANDLES (4h - Entry Timing):
{str(intraday_4h)}

DAILY CANDLES (90-day Swing Trading Window):
Last 7 Days (DETAIL):
{str(daily_candles.get("last_7d_detail", []))}

Days 8-30 (WEEKLY Summary):
{str(daily_candles.get("days_8_30_weekly", []))}

Days 31-90 (MONTHLY Summary):
{str(daily_candles.get("days_31_90_monthly", []))}

TECHNICAL INDICATORS (Latest):
Trend (EMAs): {str(indicators.get("daily", {}).get("trend", {}))}
Momentum (RSI/MACD): {str(indicators.get("daily", {}).get("momentum", {}))}
Volatility (BB/ATR): {str(indicators.get("daily", {}).get("volatility", {}))}
Volume: {str(indicators.get("daily", {}).get("volume", {}))}
Support/Resistance (3 levels): {str(indicators.get("daily", {}).get("support_resistance", {}))}
Fibonacci Levels: {str(indicators.get("daily", {}).get("fibonacci", {}))}
Pivot Points: {str(indicators.get("daily", {}).get("pivot_points", {}))}

INTRADAY MOMENTUM (4h - Entry Confirmation):
EMAs: {str(indicators.get("intraday_4h", {}).get("momentum", {}))}
Volatility: {str(indicators.get("intraday_4h", {}).get("volatility", {}))}"""

    analysis = llm(
        TECHNICAL_PROMPT.format(indicators_data=full_technical_data),
        model="claude-3-5-haiku-20241022",
        temperature=0.3,
        max_tokens=500
    )

    state["indicators_analysis"] = analysis
    return state


def news_agent(state: TradingState) -> TradingState:
    llm_data = LLMDataFormatter.format_for_news_agent()

    articles = llm_data.get("articles", [])
    articles_count = llm_data.get("articles_count", 0)

    if articles_count == 0:
        news_summary = "No recent news articles found (last 7 days)"
    else:
        articles_text = "\n".join([
            f"- {a['title']} (Sentiment: {a['sentiment']}, Source: {a['source']}, Published: {a['published_at']})"
            for a in articles[:10]
        ])
        news_summary = f"Recent News Articles ({articles_count} total):\n{articles_text}"

    analysis = llm(
        NEWS_PROMPT.format(news_data=news_summary),
        model="claude-3-5-haiku-20241022",
        temperature=0.3,
        max_tokens=300
    )

    state['news_analysis'] = analysis
    return state


def reflection_agent(state: TradingState) -> TradingState:
    llm_data = LLMDataFormatter.format_for_reflection_agent()

    trades = llm_data.get("trades", [])
    trades_count = llm_data.get("trades_count", 0)

    if trades_count == 0:
        trading_history = "No trading history yet. Starting fresh."
    else:
        trades_text = "\n".join([
            f"{i}. [{t['timestamp']}] {t['decision'].upper()} (Confidence: {t['confidence']*100:.0f}%, Action: {t['action']:.2f}) - {t['reasoning']}"
            for i, t in enumerate(trades, 1)
        ])
        trading_history = f"TRADE HISTORY ({trades_count} trades):\n{trades_text}"

    analysis = llm(
        REFLECTION_PROMPT.format(trading_history=trading_history),
        model="claude-3-5-haiku-20241022",
        temperature=0.3,
        max_tokens=300
    )

    state['reflection_analysis'] = analysis
    return state


def trader_agent(state: TradingState) -> TradingState:
    response = llm(
        FINAL_DECISION_PROMPT.format(
            indicators_analysis=state['indicators_analysis'],
            news_analysis=state['news_analysis'],
            reflection_analysis=state['reflection_analysis']
        ),
        model="claude-sonnet-4-5-20250929",
        temperature=0.0,
        max_tokens=400
    )
    
    lines = response.strip().split('\n')
    decision_line = [l for l in lines if 'DECISION:' in l]
    confidence_line = [l for l in lines if 'CONFIDENCE:' in l]
    action_line = [l for l in lines if 'ACTION:' in l]
    reasoning_line = [l for l in lines if 'REASONING:' in l]
    
    try:
        decision = decision_line[0].split(':')[1].strip().lower() if decision_line else 'hold'
        confidence = float(confidence_line[0].split(':')[1].strip()) if confidence_line else 0.5
        action = float(action_line[0].split(':')[1].strip()) if action_line else 0.0
        reasoning = reasoning_line[0].split(':', 1)[1].strip() if reasoning_line else response
    except (ValueError, IndexError):
        decision = 'hold'
        confidence = 0.5
        action = 0.0
        reasoning = response
    
    decision = 'buy' if 'buy' in decision else 'sell' if 'sell' in decision else 'hold'
    confidence = max(0.0, min(1.0, confidence))
    action = max(-1.0, min(1.0, action))
    
    state['decision'] = decision
    state['confidence'] = confidence
    state['action'] = action
    state['reasoning'] = reasoning
    
    return state


class TradingGraph:
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(TradingState)
        
        workflow.add_node("technical", technical_agent)
        workflow.add_node("news", news_agent)
        workflow.add_node("reflection", reflection_agent)
        workflow.add_node("trader", trader_agent)
        
        workflow.set_entry_point("technical")
        
        workflow.add_edge("technical", "news")
        workflow.add_edge("news", "reflection")
        workflow.add_edge("reflection", "trader")
        workflow.add_edge("trader", END)
        
        return workflow.compile()
    
    def run(self):
        initial_state = {
            'indicators_analysis': '',
            'news_analysis': '',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }
        
        result = self.graph.invoke(initial_state)
        
        return {
            'decision': result['decision'],
            'confidence': result['confidence'],
            'action': result['action'],
            'reasoning': result['reasoning'],
            'indicators_analysis': result['indicators_analysis'],
            'news_analysis': result['news_analysis'],
            'reflection_analysis': result['reflection_analysis'],
        }
