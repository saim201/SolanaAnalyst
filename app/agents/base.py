from abc import ABC, abstractmethod
from typing import TypedDict, Literal, Dict, List, Optional



class ConfidenceBreakdown(TypedDict):
    trend_strength: float
    momentum_confirmation: float
    volume_quality: float
    risk_reward: float
    final_adjusted: float

class WatchList(TypedDict):
    confirmation_signals: List[str]
    invalidation_signals: List[str]
    key_levels_24_48h: List[str]
    time_based_triggers: List[str]

class technicalOutput(TypedDict):
    recommendation: Literal['BUY', 'SELL', 'HOLD']
    confidence: float
    timeframe: str
    key_signals: List[str]
    entry_level: float
    stop_loss: float
    take_profit: float
    reasoning: str
    confidence_breakdown: ConfidenceBreakdown
    recommendation_summary: str
    watch_list: WatchList
    thinking: str

class NewsItem(TypedDict):
    title: str
    published_at: str
    url: str
    source: str

class KeyEvent(TypedDict):
    title: str
    published_at: str
    url: str
    type: str
    source_credibility: str
    news_age_hours: int
    impact: str
    reasoning: str

class EventSummary(TypedDict):
    actionable_catalysts: int
    hype_noise: int
    critical_risks: int

class NewsOutput(TypedDict):
    overall_sentiment: float
    sentiment_label: str
    confidence: float
    all_recent_news: List[NewsItem]
    key_events: List[KeyEvent]
    event_summary: EventSummary
    risk_flags: List[str]
    stance: str
    suggested_timeframe: str
    recommendation_summary: str
    what_to_watch: List[str]
    invalidation: str
    thinking: str


class BlindSpots(TypedDict):
    bull_missing: List[str]
    bear_missing: List[str]

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
    blind_spots: BlindSpots
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



class BaseAgent(ABC):
    def __init__(self, model: str = "claude-3-5-haiku-20241022", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        pass

    def __call__(self, state: AgentState) -> AgentState:
        return self.execute(state)
