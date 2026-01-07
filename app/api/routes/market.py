
from fastapi import APIRouter, HTTPException
from datetime import datetime
from sqlalchemy import desc

from app.api.schemas import RefreshDataResponse, TechnicalDataResponse, TickerResponse
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


@router.get("/sol/ticker", response_model=TickerResponse)
def get_ticker():
    db = None
    try:
        db = get_db_session()

        ticker = db.query(TickerModel).order_by(desc(TickerModel.timestamp)).first()
        if not ticker:
            raise HTTPException(status_code=404, detail="No ticker data found")

        return TickerResponse(
            lastPrice=ticker.lastPrice,
            priceChangePercent=ticker.priceChangePercent,
            openPrice=ticker.openPrice,
            highPrice=ticker.highPrice,
            lowPrice=ticker.lowPrice,
            volume=ticker.volume,
            quoteVolume=ticker.quoteVolume,
            timestamp=ticker.timestamp.isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch ticker data: {str(e)}")
    finally:
        if db:
            db.close()






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



        import math

        def safe_float(value, default=0.0):
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return default
            return float(value)

        return TechnicalDataResponse(
            currentPrice=safe_float(ticker.lastPrice),
            priceChange24h=safe_float(ticker.priceChangePercent),
            ema20=safe_float(indicators.ema20),
            ema50=safe_float(indicators.ema50),
            support=safe_float(indicators.support1),
            resistance=safe_float(indicators.resistance1),
            volume_current=safe_float(ticker.volume) / 1_000_000_000,
            volume_average=safe_float(indicators.volume_ma20) / 1_000_000_000,
            volume_ratio=safe_float(indicators.volume_ratio),
            rsi=safe_float(indicators.rsi14),
            macd_line=safe_float(indicators.macd_line),
            macd_signal=safe_float(indicators.macd_signal),
            timestamp=datetime.now().isoformat(),
            bb_upper=safe_float(indicators.bb_upper) if indicators.bb_upper else None,
            bb_lower=safe_float(indicators.bb_lower) if indicators.bb_lower else None,
            atr=safe_float(indicators.atr) if indicators.atr else None,
            support1=safe_float(indicators.support1) if indicators.support1 else None,
            resistance1=safe_float(indicators.resistance1) if indicators.resistance1 else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch technical data: {str(e)}")
    finally:
        if db:
            db.close()

