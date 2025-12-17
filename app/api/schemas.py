"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel
from typing import List, Dict


class TradeAnalysisResponse(BaseModel):
    technical_analysis: Dict
    news_analysis: Dict
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
    ema20: float | None = None
    bb_upper: float | None = None
    bb_lower: float | None = None
    atr: float | None = None
    support1: float | None = None
    resistance1: float | None = None
    pivot_weekly: float | None = None


class TickerResponse(BaseModel):
    lastPrice: float
    priceChangePercent: float
    openPrice: float
    highPrice: float
    lowPrice: float
    volume: float
    quoteVolume: float
    timestamp: str
