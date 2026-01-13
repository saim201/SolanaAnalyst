from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum


class Confidence(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class TrendAnalysis(BaseModel):
    direction: str
    strength: str
    detail: str


class MomentumAnalysis(BaseModel):
    direction: str
    strength: str
    detail: str


class VolumeAnalysis(BaseModel):
    quality: str
    ratio: float
    detail: str


class Analysis(BaseModel):
    trend: TrendAnalysis
    momentum: MomentumAnalysis
    volume: VolumeAnalysis


class TradeSetup(BaseModel):
    viability: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    support: float
    resistance: float
    current_price: float
    timeframe: str


class ActionPlan(BaseModel):
    for_buyers: str
    for_sellers: str
    if_holding: str
    avoid: str


class WatchList(BaseModel):
    bullish_signals: List[str]
    bearish_signals: List[str]


class ConfidenceReasoning(BaseModel):
    supporting: str
    concerns: str


class TechnicalAnalysisResponse(BaseModel):
    timestamp: str
    recommendation_signal: str
    confidence: Confidence
    market_condition: str
    thinking: str
    analysis: Analysis
    trade_setup: TradeSetup
    action_plan: ActionPlan
    watch_list: WatchList
    invalidation: List[str]
    confidence_reasoning: ConfidenceReasoning


class MarketFearGreed(BaseModel):
    score: int
    classification: str
    social: Optional[float] = None
    whales: Optional[float] = None
    trends: Optional[float] = None
    sentiment: str
    confidence: float
    interpretation: str


class NewsSentiment(BaseModel):
    sentiment: str
    confidence: float


class CombinedSentiment(BaseModel):
    sentiment: str
    confidence: float


class KeyEvent(BaseModel):
    title: str
    type: str
    impact: str
    source: str
    url: str
    published_at: str


class SentimentAnalysisResponse(BaseModel):
    recommendation_signal: str
    market_condition: str
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


class AgentAlignment(BaseModel):
    technical_says: str
    sentiment_says: str
    alignment_score: float
    synthesis: str


class BlindSpots(BaseModel):
    technical_missed: str
    sentiment_missed: str
    critical_insight: str


class Monitoring(BaseModel):
    watch_next_24h: List[str]
    invalidation_triggers: List[str]


class CalculatedMetrics(BaseModel):
    bayesian_confidence: float
    risk_level: str
    confidence_deviation: float


class ReflectionAnalysisResponse(BaseModel):
    recommendation_signal: str
    market_condition: str
    confidence: Confidence
    timestamp: str
    agent_alignment: AgentAlignment
    blind_spots: BlindSpots
    primary_risk: str
    monitoring: Monitoring
    calculated_metrics: CalculatedMetrics
    final_reasoning: str
    thinking: str


class FinalVerdict(BaseModel):
    summary: str
    technical_says: str
    sentiment_says: str
    reflection_says: str
    my_decision: str


class TradeSetupOutput(BaseModel):
    status: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    position_size: str
    timeframe: str
    setup_explanation: str


class ActionPlanOutput(BaseModel):
    for_new_traders: str
    for_current_holders: str
    entry_conditions: List[str]
    exit_conditions: List[str]


class WhatToMonitor(BaseModel):
    critical_next_48h: List[str]
    daily_checks: List[str]
    exit_immediately_if: List[str]


class RiskAssessment(BaseModel):
    main_risk: str
    why_this_position_size: str
    what_kills_this_trade: List[str]


class TraderAnalysisResponse(BaseModel):
    recommendation_signal: str
    market_condition: str
    confidence: Confidence
    timestamp: str
    final_verdict: FinalVerdict
    trade_setup: TradeSetupOutput
    action_plan: ActionPlanOutput
    what_to_monitor: WhatToMonitor
    risk_assessment: RiskAssessment
    thinking: str


class TradeAnalysisResponse(BaseModel):
    technical_analysis: Dict
    sentiment_analysis: Dict
    reflection_analysis: Dict
    trader_analysis: Dict
    timestamp: str


class TradeDecisionResponse(BaseModel):
    id: int
    decision: str
    confidence: float
    action: float
    reasoning: str
    timestamp: str


class TradeHistoryResponse(BaseModel):
    trades: List[TradeDecisionResponse]
    total_trades: int
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str
    checks: Dict = {}


class StatusResponse(BaseModel):
    status: str
    service: str
    version: str


class RefreshDataResponse(BaseModel):
    status: str
    message: str
    timestamp: str


class TechnicalDataResponse(BaseModel):
    currentPrice: float
    priceChange24h: float
    ema20: float
    ema50: float
    support: float
    resistance: float
    volume_current: float
    volume_average: float
    volume_ratio: float
    rsi: float
    macd_line: float
    macd_signal: float
    timestamp: str
    bb_upper: float | None = None
    bb_lower: float | None = None
    atr: float | None = None
    support1: float | None = None
    resistance1: float | None = None


class TickerResponse(BaseModel):
    lastPrice: float
    priceChangePercent: float
    openPrice: float
    highPrice: float
    lowPrice: float
    volume: float
    quoteVolume: float
    timestamp: str
