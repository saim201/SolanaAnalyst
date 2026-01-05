# Pydantic schemas for API request/response validation.

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum



class TechnicalConfidence(BaseModel):
    """Confidence for technical analysis"""
    analysis_confidence: float = Field(..., ge=0.0, le=1.0)
    setup_quality: float = Field(..., ge=0.0, le=1.0)
    interpretation: str


class SentimentConfidence(BaseModel):
    """Confidence for sentiment analysis"""
    analysis_confidence: float = Field(..., ge=0.0, le=1.0)
    signal_strength: float = Field(..., ge=0.0, le=1.0)
    interpretation: str


class ReflectionConfidence(BaseModel):
    """Confidence for reflection analysis"""
    analysis_confidence: float = Field(..., ge=0.0, le=1.0)
    final_confidence: float = Field(..., ge=0.0, le=1.0)
    interpretation: str


# ============================================================================
# AGENT RESPONSE SCHEMAS (Simplified - use Dict for nested objects)
# ============================================================================

class TechnicalAnalysisResponse(BaseModel):
    """Technical analysis response - complete agent output"""
    timestamp: str
    recommendation: str  # BUY, SELL, HOLD, WAIT
    confidence: TechnicalConfidence
    market_condition: str  # TRENDING, RANGING, VOLATILE, QUIET
    summary: str
    thinking: List[str]
    analysis: Dict[str, Any]  # {trend, momentum, volume}
    trade_setup: Dict[str, Any]  # {viability, entry, stop_loss, etc.}
    action_plan: Dict[str, Any]  # {primary, alternative, if_in_position, avoid}
    watch_list: Dict[str, List[str]]  # {next_24h, next_48h}
    invalidation: List[str]
    confidence_reasoning: Dict[str, Any]  # {supporting, concerns, assessment}

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-04T10:00:00Z",
                "recommendation": "WAIT",
                "confidence": {
                    "analysis_confidence": 0.85,
                    "setup_quality": 0.25,
                    "interpretation": "High confidence in WAIT analysis, poor setup quality"
                },
                "market_condition": "QUIET",
                "summary": "Market in consolidation with dead volume..."
            }
        }


class SentimentAnalysisResponse(BaseModel):
    """Sentiment analysis response - complete agent output"""
    timestamp: str
    signal: str  # STRONG_BULLISH, BULLISH, SLIGHTLY_BULLISH, NEUTRAL, etc.
    confidence: SentimentConfidence
    market_fear_greed: Dict[str, Any]  # {score, classification, social, whales, trends, interpretation}
    news_sentiment: Dict[str, Any]  # {score, label, catalysts_count, risks_count}
    key_events: List[Dict[str, Any]]  # [{title, type, impact, source, url, published_at}]
    risk_flags: List[str]
    summary: str
    what_to_watch: List[str]
    invalidation: str
    suggested_timeframe: str
    thinking: str

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-04T10:00:00Z",
                "signal": "SLIGHTLY_BULLISH",
                "confidence": {
                    "analysis_confidence": 0.85,
                    "signal_strength": 0.65,
                    "interpretation": "High confidence in bullish sentiment"
                },
                "market_fear_greed": {
                    "score": 55,
                    "classification": "Neutral",
                    "social": 98.5,
                    "whales": 26.5,
                    "trends": 88.5,
                    "interpretation": "Retail excitement without institutional backing"
                }
            }
        }


class ReflectionAnalysisResponse(BaseModel):
    """Reflection analysis response - complete agent output"""
    timestamp: str
    recommendation: str  # BUY, SELL, HOLD, WAIT
    confidence: ReflectionConfidence
    agreement_analysis: Dict[str, Any]  # {alignment_status, alignment_score, technical_view, sentiment_view, synthesis}
    blind_spots: Dict[str, Any]  # {technical_missed, sentiment_missed, critical_insight}
    risk_assessment: Dict[str, Any]  # {risk_level, primary_risk, secondary_risks}
    monitoring: Dict[str, Any]  # {watch_next_24h, invalidation_triggers}
    timeframe_reconciliation: Optional[Dict[str, Any]] = None  # {technical_timeframe, sentiment_timeframe, reconciled_timeframe, reasoning}
    reasoning: str
    thinking: str

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-04T10:00:00Z",
                "recommendation": "WAIT",
                "confidence": {
                    "analysis_confidence": 0.85,
                    "final_confidence": 0.28,
                    "interpretation": "High confidence in synthesis, low trade opportunity"
                }
            }
        }


# ============================================================================
# EXISTING SCHEMAS (kept for backward compatibility with current routes)
# ============================================================================

class TradeAnalysisResponse(BaseModel):
    """Response for /sol/latest endpoint - returns all agent outputs"""
    technical_analysis: Dict
    news_analysis: Dict
    reflection_analysis: Dict
    trader_analysis: Dict
    timestamp: str


class TradeDecisionResponse(BaseModel):
    """Response for /lastTrade endpoint"""
    id: int
    decision: str
    confidence: float
    action: float
    reasoning: str
    timestamp: str


class TradeHistoryResponse(BaseModel):
    """Response for /trades/history endpoint"""
    trades: List[TradeDecisionResponse]
    total_trades: int
    timestamp: str


class HealthResponse(BaseModel):
    """Response for health check endpoint"""
    status: str
    timestamp: str
    service: str
    checks: Dict = {}


class StatusResponse(BaseModel):
    """Response for status endpoint"""
    status: str
    service: str
    version: str


class RefreshDataResponse(BaseModel):
    """Response for refresh data endpoint"""
    status: str
    message: str
    timestamp: str


class TechnicalDataResponse(BaseModel):
    """Response for /sol/technical_data endpoint"""
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
    """Response for /sol/ticker endpoint"""
    lastPrice: float
    priceChangePercent: float
    openPrice: float
    highPrice: float
    lowPrice: float
    volume: float
    quoteVolume: float
    timestamp: str
