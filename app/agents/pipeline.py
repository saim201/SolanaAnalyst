"""

OPTIMIZED FLOW (v2.0):
1. Technical Agent: Analyzes indicators with 6-step chain-of-thought (Haiku)
2. News Agent: Classifies events (REGULATORY/PARTNERSHIP/SECURITY) (Haiku)
3. Reflection Agent: Bull vs Bear debate to detect blind spots (Haiku)
4. Trader Agent: Aggregates analyses into final decision (Haiku)
5. Risk Management: HARD-CODED GATES validate trade (NO LLM)
6. Portfolio Agent: Tracks performance (Haiku)

"""


from langgraph.graph import StateGraph, END
from app.agents.technical import TechnicalAgent
from app.agents.news import NewsAgent
from app.agents.reflection import ReflectionAgent
from app.agents.risk_management import RiskManagementAgent
from app.agents.trader import TraderAgent
from app.agents.portfolio import PortfolioAgent
from app.agents.base import AgentState


class TradingGraph:

    def __init__(self):
        print("\n" + "="*80)
        print("🚀 INITIALIZING OPTIMIZED TRADING PIPELINE v2.0")
        print("="*80)

        self.technical_agent = TechnicalAgent()
        self.news_agent = NewsAgent()
        self.reflection_agent = ReflectionAgent()
        self.trader_agent = TraderAgent()
        self.risk_agent = RiskManagementAgent()
        self.portfolio_agent = PortfolioAgent()
        self.graph = self._build_graph()

        print("✅ All agents initialized successfully")
        print("="*80 + "\n")



    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("technical", self.technical_agent.execute)
        workflow.add_node("news", self.news_agent.execute)
        workflow.add_node("reflection", self.reflection_agent.execute)
        workflow.add_node("trader", self.trader_agent.execute)
        workflow.add_node("risk", self.risk_agent.execute)
        workflow.add_node("portfolio", self.portfolio_agent.execute)


        # CRITICAL: Trader runs BEFORE risk management in this design
        workflow.set_entry_point("technical")
        workflow.add_edge("technical", "news")
        workflow.add_edge("news", "reflection")
        workflow.add_edge("reflection", "trader")
        workflow.add_edge("trader", "risk")  # Risk validates trader decision
        workflow.add_edge("risk", "portfolio")
        workflow.add_edge("portfolio", END)

        return workflow.compile()



    def run(self) -> dict:
        initial_state = {
            'indicators_analysis': '',
            'news_analysis': '',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
            'risk_approved': False,
            'position_size': 0.0,
            'max_loss': 0.0,
            'risk_reward': 0.0,
            'risk_reasoning': '',
            'risk_warnings': [],
            'portfolio_analysis': '',
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
            'risk_approved': result.get('risk_approved', False),
            'position_size': result.get('position_size', 0.0),
            'max_loss': result.get('max_loss', 0.0),
            'risk_reward': result.get('risk_reward', 0.0),
            'risk_reasoning': result.get('risk_reasoning', ''),
            'risk_warnings': result.get('risk_warnings', []),
            'portfolio_analysis': result.get('portfolio_analysis', ''),
        }


if __name__ == "__main__":
    pipeline = TradingGraph()
    result = pipeline.run()
    print("\n ------ Pipeline : \n", result)