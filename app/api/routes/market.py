"""
Market data endpoints.
"""
from fastapi import APIRouter, HTTPException

from app.api.schemas import MarketDataResponse
from app.agents.db_fetcher import DataQuery

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/market/data", response_model=MarketDataResponse)
def get_market_data(days: int = 30):
    """
    Get market data including price, indicators, and news.
    
    Args:
        days: Number of days of historical data to retrieve (default: 30, max: 90)
    """
    try:
        # Validate days parameter
        days = min(max(days, 1), 90)  # Ensure 1-90
        
        with DataQuery() as dq:
            price_data = dq.get_indicators_data(days=days)
            # FIX: Changed from undefined 'txn_data' to 'indicators_data'
            indicators_data = dq.get_indicators_data(days=days)
            news_data = dq.get_news_data(days=days)

        return MarketDataResponse(
            price_data=str(price_data),
            indicators=str(indicators_data),
            news_data=str(news_data)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market data: {str(e)}"
        )
