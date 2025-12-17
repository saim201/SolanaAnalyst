
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
import re

from app.api.schemas import TradeAnalysisResponse
from app.agents.pipeline import TradingGraph
from app.database.config import get_db_session
from app.database.models import TechnicalAnalyst, NewsAnalyst, ReflectionAnalyst, TraderAnalyst
from app.data.refresh_manager import RefreshManager

router = APIRouter(prefix="/api", tags=["analysis"])


def sanitize_text(text):
    if isinstance(text, str):
        # Remove control characters except newline, carriage return, and tab
        return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    return text


def sanitize_dict(data):
    if isinstance(data, dict):
        return {k: sanitize_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    elif isinstance(data, str):
        return sanitize_text(data)
    return data


@router.get("/sol/latest", response_model=TradeAnalysisResponse)
def get_latest_analysis():
    db = None
    try:
        db = get_db_session()

        technical = db.query(TechnicalAnalyst).order_by(TechnicalAnalyst.created_at.desc()).first()
        news = db.query(NewsAnalyst).order_by(NewsAnalyst.created_at.desc()).first()
        reflection = db.query(ReflectionAnalyst).order_by(ReflectionAnalyst.created_at.desc()).first()
        trader = db.query(TraderAnalyst).order_by(TraderAnalyst.created_at.desc()).first()

        if not technical or not news or not reflection or not trader:
            raise HTTPException(status_code=404, detail="No analysis data found in database")

        # Convert DB models to dictionaries
        technical_data = {
            "timestamp": technical.timestamp if technical.timestamp else technical.created_at.isoformat(),
            "recommendation": technical.recommendation,
            "confidence": technical.confidence,
            "confidence_breakdown": technical.confidence_breakdown,
            "timeframe": technical.timeframe,
            "key_signals": technical.key_signals,
            "entry_level": technical.entry_level,
            "stop_loss": technical.stop_loss,
            "take_profit": technical.take_profit,
            "reasoning": technical.reasoning,
            "recommendation_summary": technical.recommendation_summary,
            "watch_list": technical.watch_list,
            "thinking": technical.thinking
        }

        news_data = {
            "timestamp": news.timestamp if news.timestamp else news.created_at.isoformat(),
            "overall_sentiment": news.overall_sentiment,
            "sentiment_label": news.sentiment_label,
            "confidence": news.confidence,
            "all_recent_news": news.all_recent_news,
            "key_events": news.key_events,
            "event_summary": news.event_summary,
            "risk_flags": news.risk_flags,
            "stance": news.stance,
            "suggested_timeframe": news.suggested_timeframe,
            "recommendation_summary": news.recommendation_summary,
            "what_to_watch": news.what_to_watch,
            "invalidation": news.invalidation,
            "thinking": news.thinking
        }

        reflection_data = {
            "timestamp": reflection.timestamp if reflection.timestamp else reflection.created_at.isoformat(),
            "recommendation": reflection.recommendation,
            "confidence": reflection.confidence,
            "agreement_analysis": reflection.agreement_analysis,
            "blind_spots": reflection.blind_spots,
            "risk_assessment": reflection.risk_assessment,
            "monitoring": reflection.monitoring,
            "confidence_calculation": reflection.confidence_calculation,
            "reasoning": reflection.reasoning,
            "thinking": reflection.thinking
        }

        trader_data = {
            "timestamp": trader.timestamp if trader.timestamp else trader.created_at.isoformat(),
            "decision": trader.decision,
            "confidence": trader.confidence,
            "reasoning": trader.reasoning,
            "agent_synthesis": trader.agent_synthesis,
            "execution_plan": trader.execution_plan,
            "risk_management": trader.risk_management,
            "thinking": trader.thinking
        }

        # Use the most recent timestamp
        latest_timestamp = max(technical.created_at, news.created_at, reflection.created_at, trader.created_at)

        return TradeAnalysisResponse(
            technical_analysis=technical_data,
            news_analysis=news_data,
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


@router.post("/sol/analyse", response_model=TradeAnalysisResponse)
def analyse_trade():
    db = None
    try:
        print("Refreshing market data for latest analysis...")
        try:
            RefreshManager.refresh_all_data()
        except Exception as refresh_err:
            print(f"Data refresh failed, proceeding with existing data: {str(refresh_err)}")

        run_id = str(uuid.uuid4())

        graph = TradingGraph()
        result = graph.run()

        db = get_db_session()
        timestamp = datetime.now()

        # Sanitize all text fields to remove control characters
        sanitized_result = sanitize_dict(result)

        return TradeAnalysisResponse(
            technical_analysis = sanitized_result.get('technical', {}),
            news_analysis = sanitized_result.get('news', {}),
            reflection_analysis = sanitized_result.get('reflection', {}),
            trader_analysis = sanitized_result.get('trader', {}),
            timestamp = timestamp.isoformat()
        )

    except Exception as e:
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if db:
            db.close()


