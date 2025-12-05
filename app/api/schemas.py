"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class TradeAnalysisResponse(BaseModel):
    """Response from analysis endpoint"""
    decision: str
    confidence: float
    action: float
    reasoning: str
    technical_analysis: str
    news_analysis: str
    reflection_analysis: str
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
