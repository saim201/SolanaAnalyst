
from fastapi import APIRouter, HTTPException
from datetime import datetime
from sqlalchemy import desc

from app.api.schemas import RefreshDataResponse, TechnicalDataResponse
from app.data.refresh_manager import RefreshManager
from app.database.config import get_db_session
from app.database.models import TickerModel, IndicatorsModel

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


@router.get("/sol/technical_data", response_model=TechnicalDataResponse)
def get_technical_data():
    db = None
    try:
        db = get_db_session()

        ticker = db.query(TickerModel).order_by(desc(TickerModel.timestamp)).first()
        if not ticker:
            raise HTTPException(status_code=404, detail="No ticker data found")

        indicators = db.query(IndicatorsModel).order_by(desc(IndicatorsModel.timestamp)).first()
        if not indicators:
            raise HTTPException(status_code=404, detail="No indicators data found")

        macd_status = "Neutral"
        if indicators.macd_line and indicators.macd_signal:
            if indicators.macd_line > indicators.macd_signal:
                macd_status = "Bullish"
            elif indicators.macd_line < indicators.macd_signal:
                macd_status = "Bearish"



        return TechnicalDataResponse(
            currentPrice=ticker.lastPrice,
            priceChange24h=ticker.priceChangePercent,
            ema50=indicators.ema50 or 0.0,
            ema200=indicators.ema200 or 0.0,
            support=indicators.support1 or 0.0,
            resistance=indicators.resistance1 or 0.0,
            volume_current=ticker.volume / 1_000_000_000,  # Convert to billions
            volume_average=indicators.volume_ma20 / 1_000_000_000 if indicators.volume_ma20 else 0.0,
            volume_ratio=indicators.volume_ratio or 0.0,
            rsi=indicators.rsi14 or 0.0,
            macd_line=indicators.macd_line or 0.0,
            macd_signal=indicators.macd_signal or 0.0,
            timestamp=datetime.now().isoformat(),
            ema20=indicators.ema20,
            bb_upper=indicators.bb_upper,
            bb_lower=indicators.bb_lower,
            atr=indicators.atr,
            support1=indicators.support1,
            resistance1=indicators.resistance1,
            pivot_weekly=indicators.pivot_weekly
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch technical data: {str(e)}")
    finally:
        if db:
            db.close()
