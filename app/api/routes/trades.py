"""
Trade history and decision endpoints.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.api.schemas import TradeDecisionResponse, TradeHistoryResponse
from app.database.config import get_db_session
from app.database.models import TraderAnalyst

router = APIRouter(prefix="/api", tags=["trades"])


@router.get("/lastTrade", response_model=TradeDecisionResponse)
def get_last_trade_decision():
    db = None
    try:
        db = get_db_session()
        last_trade = (
            db.query(TraderAnalyst)
            .order_by(TraderAnalyst.timestamp.desc())
            .first()
        )
        
        if not last_trade:
            raise HTTPException(status_code=404, detail="No trades found")
        
        return {
            "id": last_trade.id,
            "decision": last_trade.decision,
            "confidence": last_trade.confidence,
            "action": 0.0,  # TraderAnalyst doesn't have action field
            "reasoning": last_trade.reasoning,
            "timestamp": last_trade.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch the last trade decision: {str(e)}"
        )
    finally:
        if db:
            db.close()


@router.get("/trades/history", response_model=TradeHistoryResponse)
def get_trades_history(limit: int = 10):
    db = None
    try:
        # Validate limit parameter
        limit = min(max(limit, 1), 100)  # Ensure 1-100
        
        db = get_db_session()
        trades = (
            db.query(TraderAnalyst)
            .order_by(TraderAnalyst.timestamp.desc())
            .limit(limit)
            .all()
        )

        trades_list = [
            {
                "id": trade.id,
                "decision": trade.decision,
                "confidence": trade.confidence,
                "action": 0.0,  # TraderAnalyst doesn't have action field
                "reasoning": trade.reasoning,
                "timestamp": trade.timestamp.isoformat()
            }
            for trade in trades
        ]

        return {
            "trades": trades_list,
            "total_trades": len(trades_list),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch history: {str(e)}"
        )
    finally:
        if db:
            db.close()
