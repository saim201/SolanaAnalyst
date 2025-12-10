from abc import ABC, abstractmethod
from typing import TypedDict, Literal, Dict, List, Optional



class technicalOutput(TypedDict):
    recommendation: Literal['BUY', 'SELL', 'HOLD']
    confidence: float
    confidence_breakdown: List[str]
    timeframe: str
    key_signals: List[str]
    entry_level: float
    stop_loss: float
    take_profit: float
    reasoning: str
    thinking: str

class NewsOutput(TypedDict):
    overall_sentiment: float
    sentiment_trend: str
    sentiment_breakdown: Dict[str, float]  # Fixed: Dict with category scores
    recommendation: str
    confidence: float
    hold_duration: str
    critical_events: List[str]
    event_classification: Dict[str, int]  # Fixed: Dict with catalyst counts
    risk_flags: List[str]
    time_sensitive_events: List[str]
    reasoning: str
    thinking: str


class ReflectionOutput(TypedDict):
    bull_case_summary: str
    bear_case_summary: str
    bull_strength: float
    bear_strength: float
    recommendation: str
    confidence: float
    primary_risk: str
    monitoring_trigger: str
    consensus_points: List[str]
    conflict_points: List[str]
    blind_spots: List[str]
    reasoning: str


class RiskOutput(TypedDict):
    approved: Literal['YES', 'NO']
    position_size_percent: float
    position_size_usd: float
    max_loss_usd: float
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward_ratio: float
    validation_details: Dict[str, bool]
    warnings: List[str]
    reasoning: str
    # Portfolio context
    total_balance: float
    current_risk_percent: float
    open_positions: int
    # Institutional additions
    kelly_multiplier: float
    volatility_adjustment: float
    correlation_penalty: float
    final_size_calculation: Dict[str, float]


class TraderOutput(TypedDict):
    decision: Literal['BUY', 'SELL', 'HOLD']
    confidence: float
    consensus_level: str
    agreeing_agents: List[str]
    disagreeing_agents: List[str]
    primary_concern: str
    reasoning: str
    thinking: str


class AgentState(TypedDict, total=False):

    technical: Optional[technicalOutput]
    news: Optional[NewsOutput]
    reflection: Optional[ReflectionOutput]
    risk: Optional[RiskOutput]
    trader: Optional[TraderOutput]
    portfolio: Dict

    recommendation: Optional[Literal['BUY', 'SELL', 'HOLD']]
    confidence: Optional[float]
    timeframe: Optional[str]
    key_signals: Optional[List[str]]
    entry_level: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reasoning: Optional[str]
    decision: Optional[Literal['buy', 'sell', 'hold']]
    action: Optional[float]
    risk_approved: Optional[bool]
    position_size: Optional[float]
    max_loss: Optional[float]
    risk_reward: Optional[float]
    risk_reasoning: Optional[str]
    risk_warnings: Optional[List[str]]
    indicators_analysis: Optional[str]
    news_analysis: Optional[str]
    reflection_analysis: Optional[str]
    portfolio_analysis: Optional[str]


class BaseAgent(ABC):
    def __init__(self, model: str = "claude-3-5-haiku-20241022", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        pass

    def __call__(self, state: AgentState) -> AgentState:
        return self.execute(state)
