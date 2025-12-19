

from langgraph.graph import StateGraph, END
from app.agents.technical import TechnicalAgent
from app.agents.news import NewsAgent
from app.agents.reflection import ReflectionAgent
from app.agents.trader import TraderAgent
from app.agents.base import AgentState


class TradingGraph:

    def __init__(self):

        self.technical_agent = TechnicalAgent()
        self.news_agent = NewsAgent()
        self.reflection_agent = ReflectionAgent()
        self.trader_agent = TraderAgent()
        self.graph = self._build_graph()

        print("✅ All agents initialized successfully")
        print("="*80 + "\n")



    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("technical", self.technical_agent.execute)
        workflow.add_node("news", self.news_agent.execute)
        workflow.add_node("reflection", self.reflection_agent.execute)
        workflow.add_node("trader", self.trader_agent.execute)


        workflow.set_entry_point("technical")
        workflow.add_edge("technical", "news")
        workflow.add_edge("news", "reflection")
        workflow.add_edge("reflection", "trader")      
        workflow.add_edge("trader",END)

        return workflow.compile()



    def run(self) -> dict:
        initial_state = AgentState(
            technical=None,
            news=None,
            reflection=None,
            trader=None,
        )

        result = self.graph.invoke(initial_state)

        return {
            'technical': result.get('technical', {}),
            'news': result.get('news', {}),
            'reflection': result.get('reflection', {}),
            'trader': result.get('trader', {}),
        }


if __name__ == "__main__":
    pipeline = TradingGraph()
    result = pipeline.run()
    print("\n ------ Pipeline : \n", result)