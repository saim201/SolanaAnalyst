
from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.api.schemas import RefreshDataResponse
from app.data.refresh_manager import RefreshManager

router = APIRouter(prefix="/api", tags=["market"])


@router.post("/market/refresh")
def refresh_market_data():
    try:
        print(" Market data refresh requested...")

        # Run RefreshManager to fetch and save all data
        success = RefreshManager.refresh_all_data()

        if success:
            return RefreshDataResponse(
                status="success",
                message="Market data refreshed successfully (candlesticks, ticker, news, indicators fetched and saved to DB)",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Some data sources failed to refresh. Check logs for details."
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Market data refresh failed: {str(e)}"
        )
