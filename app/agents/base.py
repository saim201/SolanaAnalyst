
from abc import ABC, abstractmethod
from typing import TypedDict, Literal


class AgentState(TypedDict, total=False):
    indicators_analysis: str
    news_analysis: str
    reflection_analysis: str
    portfolio_analysis: str

    # Trading decision 
    decision: Literal['buy', 'sell', 'hold']
    confidence: float
    action: float
    reasoning: str

    # Technical analysis 
    recommendation: Literal['BUY', 'SELL', 'HOLD']
    timeframe: str
    key_signals: list
    entry_level: float
    stop_loss: float
    take_profit: float

    # Risk management 
    risk_approved: bool
    position_size: float
    max_loss: float
    risk_reward: float
    risk_reasoning: str
    risk_warnings: list


class BaseAgent(ABC):
    def __init__(self, model: str = "claude-3-5-haiku-20241022", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature

        

    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        pass

    def __call__(self, state: AgentState) -> AgentState:
        return self.execute(state)
