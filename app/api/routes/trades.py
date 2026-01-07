
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
        
        confidence_obj = last_trade.confidence if isinstance(last_trade.confidence, dict) else {"score": 0.5, "reasoning": ""}
        confidence_score = confidence_obj.get("score", 0.5)

        final_verdict = last_trade.final_verdict if isinstance(last_trade.final_verdict, dict) else {}
        reasoning = final_verdict.get("summary", "No reasoning available")

        return {
            "id": last_trade.id,
            "decision": last_trade.recommendation_signal,
            "confidence": confidence_score,
            "action": 0.0,
            "reasoning": reasoning,
            "timestamp": last_trade.timestamp if isinstance(last_trade.timestamp, str) else last_trade.timestamp.isoformat()
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
        limit = min(max(limit, 1), 100)  # Ensure 1-100
        
        db = get_db_session()
        trades = (
            db.query(TraderAnalyst)
            .order_by(TraderAnalyst.timestamp.desc())
            .limit(limit)
            .all()
        )

        trades_list = []
        for trade in trades:
            confidence_obj = trade.confidence if isinstance(trade.confidence, dict) else {"score": 0.5, "reasoning": ""}
            confidence_score = confidence_obj.get("score", 0.5)

            final_verdict = trade.final_verdict if isinstance(trade.final_verdict, dict) else {}
            reasoning = final_verdict.get("summary", "No reasoning available")

            trades_list.append({
                "id": trade.id,
                "decision": trade.recommendation_signal,
                "confidence": confidence_score,
                "action": 0.0,
                "reasoning": reasoning,
                "timestamp": trade.timestamp if isinstance(trade.timestamp, str) else trade.timestamp.isoformat()
            })

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
