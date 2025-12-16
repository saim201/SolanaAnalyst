"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any


class TradeAnalysisResponse(BaseModel):
    # decision: str
    # confidence: float
    # reasoning: str
    technical_analysis: Dict
    news_analysis: Dict
    reflection_analysis: Dict
    trader_analysis: Dict
    timestamp: str


class TechnicalAnalysisSchema(BaseModel):
    """Technical analysis nested output"""
    recommendation: str
    confidence: float
    confidence_breakdown: Optional[List[str]] = None
    timeframe: Optional[str] = None
    key_signals: Optional[List[str]] = None
    entry_level: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: str
    thinking: Optional[str] = None


class NewsAnalysisSchema(BaseModel):
    """News analysis nested output"""
    overall_sentiment: float
    sentiment_trend: str
    sentiment_breakdown: Optional[Dict[str, float]] = None
    recommendation: str
    confidence: float
    hold_duration: Optional[str] = None
    critical_events: Optional[List[str]] = None
    event_classification: Optional[Dict[str, int]] = None
    risk_flags: Optional[List[str]] = None
    time_sensitive_events: Optional[List[str]] = None
    reasoning: str
    thinking: Optional[str] = None


class ReflectionAnalysisSchema(BaseModel):
    """Reflection analysis nested output"""
    bull_case_summary: str
    bear_case_summary: str
    bull_strength: float
    bear_strength: float
    recommendation: str
    confidence: float
    primary_risk: Optional[str] = None
    monitoring_trigger: Optional[str] = None
    consensus_points: Optional[List[str]] = None
    conflict_points: Optional[List[str]] = None
    blind_spots: Optional[Any] = None  # Can be List or Dict
    reasoning: str


class TraderDecisionSchema(BaseModel):
    """Trader decision nested output"""
    decision: str
    confidence: float
    consensus_level: Optional[str] = None
    agreeing_agents: Optional[List[str]] = None
    disagreeing_agents: Optional[List[str]] = None
    primary_concern: Optional[str] = None
    reasoning: str
    thinking: Optional[str] = None


class NestedAnalysisResponse(BaseModel):
    """Full nested analysis response matching agent state structure"""
    technical: Optional[TechnicalAnalysisSchema] = None
    news: Optional[NewsAnalysisSchema] = None
    reflection: Optional[ReflectionAnalysisSchema] = None
    trader: Optional[TraderDecisionSchema] = None
    timestamp: str


class MarketDataResponse(BaseModel):
    """Response from market data endpoint"""
    price_data: str
    indicators: str
    news_data: str


class PortfolioStatusResponse(BaseModel):
    """Response from portfolio status endpoint"""
    cash: float
    sol_held: float
    price: float
    net_worth: float
    roi: float


class TradeDecisionResponse(BaseModel):
    """Response for a single trade decision"""
    id: int
    decision: str
    confidence: float
    action: float
    reasoning: str
    timestamp: str


class TradeHistoryResponse(BaseModel):
    """Response from trade history endpoint"""
    trades: List[TradeDecisionResponse]
    total_trades: int
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    service: str


class StatusResponse(BaseModel):
    """Root status response"""
    status: str
    service: str
    version: str


class RefreshDataResponse(BaseModel):
    """Response from data refresh endpoint"""
    status: str
    message: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str


class TechnicalDataResponse(BaseModel):
    """Response from technical data endpoint"""
    currentPrice: float
    priceChange24h: float
    ema50: float
    ema200: float
    support: float
    resistance: float
    volume_current: float
    volume_average: float
    volume_ratio: float
    rsi: float
    macd_line: float
    macd_signal: float
    timestamp: str
    # Additional indicators
    ema20: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    atr: Optional[float] = None
    support1: Optional[float] = None
    resistance1: Optional[float] = None
    pivot_weekly: Optional[float] = None
