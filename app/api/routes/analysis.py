
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import uuid
import re
from typing import Optional

from app.api.schemas import TradeAnalysisResponse
from app.agents.pipeline import TradingGraph
from app.database.config import get_db_session
from app.database.models import TechnicalAnalyst, SentimentAnalyst, ReflectionAnalyst, TraderAnalyst
from app.data.refresh_manager import RefreshManager
from app.utils.progress_tracker import ProgressTracker
from app.utils.progress_store import progress_store

router = APIRouter(prefix="/api", tags=["analysis"])


def sanitise_text(text):
    if isinstance(text, str):
        return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    return text


def sanitise_dict(data):
    if isinstance(data, dict):
        return {k: sanitise_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitise_dict(item) for item in data]
    elif isinstance(data, str):
        return sanitise_text(data)
    return data


@router.get("/sol/latest", response_model=TradeAnalysisResponse)
def get_latest_analysis():
    db = None
    try:
        db = get_db_session()

        technical = db.query(TechnicalAnalyst).order_by(TechnicalAnalyst.created_at.desc()).first()
        sentiment = db.query(SentimentAnalyst).order_by(SentimentAnalyst.created_at.desc()).first()
        reflection = db.query(ReflectionAnalyst).order_by(ReflectionAnalyst.created_at.desc()).first()
        trader = db.query(TraderAnalyst).order_by(TraderAnalyst.created_at.desc()).first()

        if not technical or not sentiment or not reflection or not trader:
            raise HTTPException(status_code=404, detail="No analysis data found in database")

        technical_data = {
            "timestamp": technical.timestamp if technical.timestamp else technical.created_at.isoformat(),
            "recommendation_signal": technical.recommendation_signal,
            "confidence": technical.confidence,
            "market_condition": technical.market_condition,
            "thinking": technical.thinking,
            "analysis": technical.analysis,
            "trade_setup": technical.trade_setup,
            "action_plan": technical.action_plan,
            "watch_list": technical.watch_list,
            "invalidation": technical.invalidation,
            "confidence_reasoning": technical.confidence_reasoning,
        }

        sentiment_data = {
            "timestamp": sentiment.timestamp if sentiment.timestamp else sentiment.created_at.isoformat(),
            "recommendation_signal": sentiment.recommendation_signal,
            "market_condition": sentiment.market_condition,
            "confidence": sentiment.confidence,
            "market_fear_greed": sentiment.market_fear_greed,
            "news_sentiment": sentiment.news_sentiment,
            "combined_sentiment": sentiment.combined_sentiment,
            "key_events": sentiment.key_events or [],
            "risk_flags": sentiment.risk_flags or [],
            "what_to_watch": sentiment.what_to_watch or [],
            "invalidation": sentiment.invalidation,
            "suggested_timeframe": sentiment.suggested_timeframe,
            "thinking": sentiment.thinking
        }

        reflection_data = {
            "timestamp": reflection.timestamp if reflection.timestamp else reflection.created_at.isoformat(),
            "recommendation_signal": reflection.recommendation_signal,
            "market_condition": reflection.market_condition,
            "confidence": reflection.confidence,
            "agent_alignment": reflection.agent_alignment,
            "blind_spots": reflection.blind_spots,
            "primary_risk": reflection.primary_risk,
            "monitoring": reflection.monitoring,
            "calculated_metrics": reflection.calculated_metrics,
            "final_reasoning": reflection.final_reasoning,
            "thinking": reflection.thinking
        }

        trader_data = {
            "timestamp": trader.timestamp if trader.timestamp else trader.created_at.isoformat(),
            "recommendation_signal": trader.recommendation_signal,
            "market_condition": trader.market_condition,
            "confidence": trader.confidence,
            "final_verdict": trader.final_verdict,
            "trade_setup": trader.trade_setup,
            "action_plan": trader.action_plan,
            "what_to_monitor": trader.what_to_monitor,
            "risk_assessment": trader.risk_assessment,
            "thinking": trader.thinking
        }

        latest_timestamp = max(technical.created_at, sentiment.created_at, reflection.created_at, trader.created_at)

        return TradeAnalysisResponse(
            technical_analysis=technical_data,
            sentiment_analysis=sentiment_data,
            reflection_analysis=reflection_data,
            trader_analysis=trader_data,
            timestamp=latest_timestamp.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest analysis: {str(e)}")
    finally:
        if db:
            db.close()


@router.post("/sol/analyse")
def analyse_trade(job_id: Optional[str] = Query(None)):
    db = None
    if not job_id:
        job_id = str(uuid.uuid4())

    try:
        def progress_callback(step: str, status: str, message: str):
            progress_store.add_progress(job_id, step, status, message)

        tracker = ProgressTracker(callback=progress_callback)

        progress_store.add_progress(job_id, "refresh_data", "started",
                                   "Fetching latest market data ...")
        try:
            RefreshManager.refresh_all_data()
            progress_store.add_progress(job_id, "refresh_data", "completed",
                                       "Market data refreshed successfully")
        except Exception as refresh_err:
            progress_store.add_progress(job_id, "refresh_data", "warning",
                                       "Data refresh partial, proceeding with existing data")
            print(f"Data refresh failed, proceeding with existing data: {str(refresh_err)}")

        graph = TradingGraph(progress_tracker=tracker)
        result = graph.run()

        db = get_db_session()
        timestamp = datetime.now()

        sanitized_result = sanitise_dict(result)

        progress_store.add_progress(job_id, "complete", "completed", "Analysis complete")

        try:
            progress_store.cleanup_old_progress(days=1)
        except:
            pass  # Don't fail if cleanup fails

        return TradeAnalysisResponse(
            technical_analysis = sanitized_result.get('technical', {}),
            sentiment_analysis = sanitized_result.get('sentiment', {}),
            reflection_analysis = sanitized_result.get('reflection', {}),
            trader_analysis = sanitized_result.get('trader', {}),
            timestamp = timestamp.isoformat()
        )

    except Exception as e:
        progress_store.add_progress(job_id, "error", "error", f"Analysis failed: {str(e)}")

        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if db:
            db.close()


@router.get("/sol/analyse/progress/{job_id}")
def get_analysis_progress(job_id: str):
    progress = progress_store.get_progress(job_id)

    # Check if analysis is complete
    is_complete = any(p.get('step') == 'complete' and p.get('status') == 'completed' for p in progress)
    has_error = any(p.get('step') == 'error' and p.get('status') == 'error' for p in progress)

    status = 'completed' if is_complete else ('error' if has_error else 'running')

    return {
        "job_id": job_id,
        "status": status,
        "progress": progress
    }

