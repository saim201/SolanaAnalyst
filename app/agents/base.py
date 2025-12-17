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




class AgreementAnalysis(TypedDict):
    alignment_status: str
    alignment_score: float
    explanation: str

class BlindSpots(TypedDict):
    technical_missed: List[str]
    news_missed: List[str]

class RiskAssessment(TypedDict):
    primary_risk: str
    risk_level: str
    risk_score: float

class Monitoring(TypedDict):
    watch_next_24h: List[str]
    invalidation_trigger: str

class ConfidenceCalculation(TypedDict):
    starting_confidence: float
    alignment_bonus: float
    risk_penalty: float
    confidence: float
    reasoning: str

class ReflectionOutput(TypedDict):
    recommendation: str
    confidence: float
    agreement_analysis: AgreementAnalysis
    blind_spots: BlindSpots
    risk_assessment: RiskAssessment
    monitoring: Monitoring
    confidence_calculation: ConfidenceCalculation
    reasoning: str
    thinking: str





class AgentSynthesis(TypedDict):
    technical_weight: float
    news_weight: float
    reflection_weight: float
    weighted_confidence: float
    agreement_summary: str
    technical_contribution: str
    news_contribution: str
    reflection_contribution: str

class ExecutionPlan(TypedDict):
    entry_timing: str
    position_size: str
    entry_price_target: float
    stop_loss: float
    take_profit: float
    timeframe: str
    risk_reward_ratio: str

class RiskManagement(TypedDict):
    max_loss_per_trade: str
    primary_risk: str
    secondary_risks: List[str]
    exit_conditions: List[str]
    monitoring_checklist: List[str]

class TraderOutput(TypedDict):
    decision: Literal['BUY', 'SELL', 'HOLD']
    confidence: float
    reasoning: str
    agent_synthesis: AgentSynthesis
    execution_plan: ExecutionPlan
    risk_management: RiskManagement
    thinking: str


class AgentState(TypedDict, total=False):
    technical: Optional[technicalOutput]
    news: Optional[NewsOutput]
    reflection: Optional[ReflectionOutput]
    trader: Optional[TraderOutput]



class BaseAgent(ABC):
    def __init__(self, model: str = "claude-3-5-haiku-20241022", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        pass

    def __call__(self, state: AgentState) -> AgentState:
        return self.execute(state)
