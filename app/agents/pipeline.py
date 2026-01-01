

from langgraph.graph import StateGraph, END
from app.agents.technical import TechnicalAgent
from app.agents.sentiment import SentimentAgent
from app.agents.reflection import ReflectionAgent
from app.agents.trader import TraderAgent
from app.agents.base import AgentState
from typing import Optional
from app.utils.progress_tracker import ProgressTracker


class TradingGraph:

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):

        self.progress_tracker = progress_tracker
        self.technical_agent = TechnicalAgent()
        self.sentiment_agent = SentimentAgent()  # Renamed from news_agent
        self.reflection_agent = ReflectionAgent()
        self.trader_agent = TraderAgent()
        self.graph = self._build_graph()



    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("technical", self._execute_technical)
        workflow.add_node("sentiment", self._execute_sentiment)
        workflow.add_node("reflection", self._execute_reflection)
        workflow.add_node("trader", self._execute_trader)


        workflow.set_entry_point("technical")
        workflow.add_edge("technical", "sentiment")
        workflow.add_edge("sentiment", "reflection")
        workflow.add_edge("reflection", "trader")
        workflow.add_edge("trader",END)

        return workflow.compile()

    def _execute_technical(self, state: AgentState) -> AgentState:
        if self.progress_tracker:
            self.progress_tracker.start_technical()
        result = self.technical_agent.execute(state)
        if self.progress_tracker:
            self.progress_tracker.complete_technical()
        return result

    def _execute_sentiment(self, state: AgentState) -> AgentState:
        if self.progress_tracker:
            self.progress_tracker.start_sentiment()
        result = self.sentiment_agent.execute(state)
        if self.progress_tracker:
            self.progress_tracker.complete_sentiment()
        return result

    def _execute_reflection(self, state: AgentState) -> AgentState:
        if self.progress_tracker:
            self.progress_tracker.start_reflection()
        result = self.reflection_agent.execute(state)
        if self.progress_tracker:
            self.progress_tracker.complete_reflection()
        return result

    def _execute_trader(self, state: AgentState) -> AgentState:
        if self.progress_tracker:
            self.progress_tracker.start_trader()
        result = self.trader_agent.execute(state)
        if self.progress_tracker:
            self.progress_tracker.complete_trader()
        return result



    def run(self) -> dict:
        initial_state = AgentState(
            technical=None,
            sentiment=None,
            reflection=None,
            trader=None,
        )

        result = self.graph.invoke(initial_state)

        return {
            'technical': result.get('technical', {}),
            'sentiment': result.get('sentiment', {}),
            'reflection': result.get('reflection', {}),
            'trader': result.get('trader', {}),
        }


if __name__ == "__main__":
    pipeline = TradingGraph()
    result = pipeline.run()
    print("\n ------ Pipeline : \n", result)