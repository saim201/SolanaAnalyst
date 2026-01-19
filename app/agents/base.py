from abc import ABC, abstractmethod
from typing import TypedDict, Literal, Dict, List, Optional, Any



# SHARED TYPES
class Confidence(TypedDict):
    score: float  # 0.0 to 1.0
    reasoning: str  # 2-3 sentences explaining the confidence





# TECHNICAL AGENT OUTPUT
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
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
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
    supporting: str
    concerns: str


class TechnicalOutput(TypedDict):
    timestamp: str
    recommendation_signal: Literal['BUY', 'SELL', 'HOLD', 'WAIT']
    confidence: Confidence
    market_condition: Literal['TRENDING', 'RANGING', 'VOLATILE', 'QUIET']
    thinking: str
    analysis: Analysis
    trade_setup: TradeSetup
    action_plan: ActionPlan
    watch_list: WatchList
    invalidation: List[str]
    confidence_reasoning: ConfidenceReasoning




# SENTIMENT AGENT OUTPUT
class MarketFearGreed(TypedDict):
    score: int  # 0-100
    classification: str  # e.g., "Greed", "Fear", "Neutral"
    social: Optional[float]
    whales: Optional[float]
    trends: Optional[float]
    sentiment: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    confidence: float
    interpretation: str


class NewsSentiment(TypedDict):
    sentiment: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    confidence: float


class CombinedSentiment(TypedDict):
    sentiment: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    confidence: float


class KeyEvent(TypedDict):
    title: str
    type: str  # e.g., "PARTNERSHIP", "UPGRADE", etc.
    impact: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    source: str
    url: str
    published_at: str


class SentimentOutput(TypedDict):
    recommendation_signal: Literal['BUY', 'SELL', 'HOLD', 'WAIT']
    market_condition: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    confidence: Confidence
    timestamp: str
    market_fear_greed: MarketFearGreed
    news_sentiment: NewsSentiment
    combined_sentiment: CombinedSentiment
    key_events: List[KeyEvent]
    risk_flags: List[str]
    what_to_watch: List[str]
    invalidation: str
    suggested_timeframe: str
    thinking: str




# REFLECTION AGENT OUTPUT
class AgentAlignment(TypedDict):
    technical_says: str  # e.g., "BUY (72%)"
    sentiment_says: str  # e.g., "BULLISH (65%)"
    alignment_score: float  # 0.0 to 1.0
    synthesis: str


class BlindSpots(TypedDict):
    technical_missed: str
    sentiment_missed: str
    critical_insight: str


class Monitoring(TypedDict):
    watch_next_24h: List[str]
    invalidation_triggers: List[str]


class CalculatedMetrics(TypedDict):
    bayesian_confidence: float
    risk_level: Literal['LOW', 'MEDIUM', 'HIGH']
    confidence_deviation: float  # Difference between LLM and Bayesian


class ReflectionOutput(TypedDict):
    recommendation_signal: Literal['BUY', 'SELL', 'HOLD', 'WAIT']
    market_condition: Literal['ALIGNED', 'CONFLICTED', 'MIXED']
    confidence: Confidence
    timestamp: str
    agent_alignment: AgentAlignment
    blind_spots: BlindSpots
    primary_risk: str
    monitoring: Monitoring
    calculated_metrics: CalculatedMetrics  # Reference metrics for validation
    final_reasoning: str
    thinking: str




# TRADER AGENT OUTPUT
class FinalVerdict(TypedDict):
    technical_says: str
    sentiment_says: str
    reflection_says: str
    my_decision: str


class TradeSetupOutput(TypedDict):
    status: Literal['READY_TO_ENTER', 'WAIT_FOR_SETUP', 'HOLD_POSITION', 'EXIT_RECOMMENDED']
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    position_size: str
    timeframe: str
    setup_explanation: str


class ActionPlanOutput(TypedDict):
    for_new_traders: str
    for_current_holders: str
    entry_conditions: List[str]
    exit_conditions: List[str]


class WhatToMonitor(TypedDict):
    critical_next_48h: List[str]
    daily_checks: List[str]
    exit_immediately_if: List[str]


class RiskAssessment(TypedDict):
    main_risk: str
    why_this_position_size: str
    what_kills_this_trade: List[str]


class TraderOutput(TypedDict):
    recommendation_signal: Literal['BUY', 'SELL', 'HOLD', 'WAIT']
    market_condition: Literal['BULLISH', 'BEARISH', 'NEUTRAL', 'BULLISH_BUT_CAUTIOUS', 'BEARISH_BUT_WATCHING']
    confidence: Confidence
    timestamp: str
    final_verdict: FinalVerdict
    trade_setup: TradeSetupOutput
    action_plan: ActionPlanOutput
    what_to_monitor: WhatToMonitor
    risk_assessment: RiskAssessment
    thinking: str




# AGENT STATE
class AgentState(TypedDict, total=False):
    technical: Optional[TechnicalOutput]
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
