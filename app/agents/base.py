from abc import ABC, abstractmethod
from typing import TypedDict, Literal, Dict, List, Optional


class TrendAnalysis(TypedDict):
    direction: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    strength: Literal['STRONG', 'MODERATE', 'WEAK']
    detail: str


class MomentumAnalysis(TypedDict):
    direction: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    strength: Literal['STRONG', 'MODERATE', 'WEAK']
    detail: str


class VolumeAnalysis(TypedDict):
    quality: Literal['STRONG', 'ACCEPTABLE', 'WEAK', 'DEAD']
    ratio: float
    detail: str


class Analysis(TypedDict):
    trend: TrendAnalysis
    momentum: MomentumAnalysis
    volume: VolumeAnalysis


class TradeSetup(TypedDict):
    viability: Literal['VALID', 'WAIT', 'INVALID']
    entry: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward: Optional[float]
    support: float
    resistance: float
    current_price: float
    timeframe: str


class ActionPlan(TypedDict):
    for_buyers: str
    for_sellers: str
    if_holding: str
    avoid: str


class WatchList(TypedDict):
    bullish_signals: List[str]
    bearish_signals: List[str]


class ConfidenceReasoning(TypedDict):
    supporting: List[str]
    concerns: List[str]


class TechnicalConfidence(TypedDict):
    analysis_confidence: float
    setup_quality: float
    interpretation: str


class technicalOutput(TypedDict):
    timestamp: str
    recommendation_signal: Literal['BUY', 'SELL', 'HOLD', 'WAIT']
    confidence: TechnicalConfidence
    market_condition: Literal['TRENDING', 'RANGING', 'VOLATILE', 'QUIET']
    summary: str
    thinking: List[str]
    analysis: Analysis
    trade_setup: TradeSetup
    action_plan: ActionPlan
    watch_list: WatchList
    invalidation: List[str]
    confidence_reasoning: ConfidenceReasoning


class MarketFearGreed(TypedDict):
    score: float
    classification: str
    social: Optional[float]
    whales: Optional[float]
    trends: Optional[float]
    interpretation: str


class NewsSentiment(TypedDict):
    score: float
    label: str
    catalysts_count: int
    risks_count: int


class KeyEvent(TypedDict):
    title: str
    published_at: str
    url: str
    type: str
    impact: str
    source: str


class SentimentConfidence(TypedDict):
    analysis_confidence: float
    signal_strength: float
    interpretation: str


class SentimentOutput(TypedDict):
    signal: str
    confidence: SentimentConfidence
    market_fear_greed: MarketFearGreed
    news_sentiment: NewsSentiment
    key_events: List[KeyEvent]
    risk_flags: List[str]
    summary: str
    what_to_watch: List[str]
    invalidation: str
    suggested_timeframe: str
    thinking: str


class AgreementAnalysis(TypedDict):
    alignment_status: Literal['ALIGNED', 'PARTIAL', 'CONFLICTED']
    alignment_score: float
    technical_view: str
    sentiment_view: str
    synthesis: str


class BlindSpots(TypedDict):
    technical_missed: List[str]
    sentiment_missed: List[str]
    critical_insight: str


class RiskAssessment(TypedDict):
    primary_risk: str
    risk_level: Literal['LOW', 'MEDIUM', 'HIGH']
    secondary_risks: List[str]


class Monitoring(TypedDict):
    watch_next_24h: List[str]
    invalidation_triggers: List[str]


class ReflectionConfidence(TypedDict):
    analysis_confidence: float
    final_confidence: float
    interpretation: str


class TimeframeReconciliation(TypedDict):
    technical_timeframe: str
    sentiment_timeframe: str
    reconciled_timeframe: str
    reasoning: str


class ReflectionOutput(TypedDict):
    recommendation_signal: Literal['BUY', 'SELL', 'HOLD', 'WAIT']
    confidence: ReflectionConfidence
    timestamp: str
    agreement_analysis: AgreementAnalysis
    blind_spots: BlindSpots
    risk_assessment: RiskAssessment
    monitoring: Monitoring
    timeframe_reconciliation: TimeframeReconciliation
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
    sentiment: Optional[SentimentOutput]
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
