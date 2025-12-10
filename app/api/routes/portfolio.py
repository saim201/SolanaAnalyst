"""
Portfolio and data management endpoints.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.api.schemas import PortfolioStatusResponse, RefreshDataResponse
from app.data.refresh_manager import RefreshManager

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio/status", response_model=PortfolioStatusResponse)
def get_portfolio_status():
    """
    Get current portfolio status.
    
    TODO: Replace hardcoded values with real portfolio tracking from database
    """
    try:
        # NOTE: Currently returns hardcoded values
        # TODO: Implement real portfolio tracking from PortfolioState model
        return {
            "cash": 500000,
            "sol_held": 3900.0,
            "price": 127.30,
            "net_worth": 1000000,
            "roi": 0.0,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch portfolio: {str(e)}"
        )


@router.post("/refresh-data", response_model=RefreshDataResponse)
def refresh_market_data():
    """
    Manually trigger a data refresh cycle.
    
    Fetches latest price data, calculates indicators, and retrieves news.
    """
    try:
        print("🔄 Manual data refresh requested...")
        RefreshManager.refresh_all_data(days=1)
        return {
            "status": "success",
            "message": "Market data refreshed successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Data refresh failed: {str(e)}"
        )
