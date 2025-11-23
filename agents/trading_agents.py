from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import llm
import config
from agents.db_fetcher import DataQuery



class TradingState(TypedDict):
    # Input data
    price_data: str
    txn_data: str
    news_data: str
    trading_history: str
    current_state: str

    # Agent outputs
    onchain_analysis: str
    news_analysis: str
    reflection_analysis: str

    # Final decision
    reasoning: str
    decision: Literal['buy', 'sell', 'hold']
    confidence: float
    action: float  # -1.0 to 1.0


# Enhanced Prompt Templates
ONCHAIN_PROMPT = """You are an expert Solana (SOL) on-chain analyst.

MARKET DATA:
{price_data}

TRANSACTION METRICS:
{txn_data}

TASK: Analyze technical indicators (price trends, moving averages, MACD) and on-chain metrics (transaction volume, unique addresses, gas usage).

Provide a focused analysis in 2-3 sentences covering:
1. Current price trend and technical signals
2. On-chain activity interpretation
3. Short-term market direction

Keep it concise and actionable."""

NEWS_PROMPT = """You are an expert Solana (SOL) news analyst.

RECENT NEWS:
{news_data}

TASK: Analyze news sentiment and market impact.

Provide a focused analysis in 2-3 sentences covering:
1. Overall sentiment (bullish/bearish/neutral)
2. Key catalysts or risks
3. Likely market reaction

Keep it concise and actionable."""

REFLECTION_PROMPT = """You are an expert trading performance analyst for Solana (SOL).

RECENT TRADING PERFORMANCE:
{trading_history}

TASK: Reflect on recent trades and strategy effectiveness.

Provide a focused analysis in 2-3 sentences covering:
1. What worked well or poorly
2. Current strategy assessment
3. Recommended approach (aggressive/conservative)

Keep it concise and actionable."""

TRADER_PROMPT = """You are an expert Solana (SOL) trader making the final decision.

CURRENT PORTFOLIO:
{current_state}

ANALYSIS FROM YOUR TEAM:

📊 ON-CHAIN ANALYST:
{onchain_analysis}

📰 NEWS ANALYST:
{news_analysis}

🔍 REFLECTION ANALYST:
{reflection_analysis}

TASK: Synthesize all analyses and make a clear trading decision.

Respond in EXACTLY this format:

REASONING: [1-2 sentence explanation of your decision]
DECISION: [buy/sell/hold]
CONFIDENCE: [0.0 to 1.0]
ACTION: [-1.0 to 1.0, where -1=sell all, 0=hold, 1=buy all]

Be decisive and clear."""


class TradingGraph:
    def __init__(self):
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

    def _onchain_analyst(self, state: TradingState) -> TradingState:
        prompt = ONCHAIN_PROMPT.format(
            price_data=state['price_data'],
            txn_data=state['txn_data']
        )

        analysis = llm(prompt, config.MODELS['onchain']).strip()

        print("\n📊 ON-CHAIN ANALYST:")
        print(analysis)

        state['onchain_analysis'] = analysis
        return state

    def _news_analyst(self, state: TradingState) -> TradingState:
        """News analysis using fast model"""
        if not state['news_data'] or state['news_data'] == "No news available":
            analysis = "No significant news to report."
        else:
            prompt = NEWS_PROMPT.format(news_data=state['news_data'])
            analysis = llm(prompt, config.MODELS['news']).strip()

        print("\n📰 NEWS ANALYST:")
        print(analysis)

        state['news_analysis'] = analysis
        return state

    def _reflection_analyst(self, state: TradingState) -> TradingState:
        """Reflection analysis using fast model"""
        if not state['trading_history']:
            analysis = "No trading history yet. Starting with balanced approach."
        else:
            prompt = REFLECTION_PROMPT.format(
                trading_history=state['trading_history']
            )
            analysis = llm(prompt, config.MODELS['reflection']).strip()

        print("\n🔍 REFLECTION ANALYST:")
        print(analysis)

        state['reflection_analysis'] = analysis
        return state

    def _trader(self, state: TradingState) -> TradingState:
        """Final decision using best model"""
        prompt = TRADER_PROMPT.format(
            current_state=state['current_state'],
            onchain_analysis=state['onchain_analysis'],
            news_analysis=state['news_analysis'],
            reflection_analysis=state['reflection_analysis']
        )

        response = llm(prompt, config.MODELS['trader']).strip()

        # Parse response
        reasoning = ""
        decision = "hold"
        confidence = 0.5
        action = 0.0

        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('REASONING:'):
                reasoning = line.replace('REASONING:', '').strip()
            elif line.startswith('DECISION:'):
                decision = line.replace('DECISION:', '').strip().lower()
            elif line.startswith('CONFIDENCE:'):
                try:
                    confidence = float(line.replace('CONFIDENCE:', '').strip())
                except:
                    confidence = 0.5
            elif line.startswith('ACTION:'):
                try:
                    action = float(line.replace('ACTION:', '').strip())
                except:
                    action = 0.0

        print("\n💼 TRADER DECISION:")
        print(f"Reasoning: {reasoning}")
        print(f"Decision: {decision.upper()}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Action: {action:.2f}")

        state['reasoning'] = reasoning
        state['decision'] = decision
        state['confidence'] = confidence
        state['action'] = action

        return state

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(TradingState)

        # Add nodes
        workflow.add_node("onchain", self._onchain_analyst)
        workflow.add_node("news", self._news_analyst)
        workflow.add_node("reflection", self._reflection_analyst)
        workflow.add_node("trader", self._trader)

        # Define edges
        workflow.set_entry_point("onchain")
        workflow.add_edge("onchain", "news")
        workflow.add_edge("news", "reflection")
        workflow.add_edge("reflection", "trader")
        workflow.add_edge("trader", END)

        return workflow

    def run(self, price_data: str = None, txn_data: str = None, news_data: str = None,
            trading_history: str = "", current_state: str = "Starting position") -> TradingState:

        if price_data is None or txn_data is None or news_data is None:
            with DataQuery() as dq:
                price_data = dq.get_price_data(days=30)
                txn_data = dq.get_transaction_data(days=30)
                news_data = dq.get_news_data(days=30)

        print("\n" + "="*80)
        print("🤖 TRADING SYSTEM")
        print("="*80)

        initial_state: TradingState = {
            'price_data': price_data,
            'txn_data': txn_data,
            'news_data': news_data,
            'trading_history': trading_history,
            'current_state': current_state,
            'onchain_analysis': '',
            'news_analysis': '',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0
        }

        final_state = self.app.invoke(initial_state)

        print("="*80)

        return final_state
