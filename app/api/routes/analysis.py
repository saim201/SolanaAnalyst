
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
import uuid
import re
import json
import asyncio
from typing import AsyncGenerator

from app.api.schemas import TradeAnalysisResponse
from app.agents.pipeline import TradingGraph
from app.database.config import get_db_session
from app.database.models import TechnicalAnalyst, NewsAnalyst, ReflectionAnalyst, TraderAnalyst
from app.data.refresh_manager import RefreshManager
from app.utils.progress_tracker import ProgressTracker

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


@router.get("/sol/analyse/stream")
async def analyse_trade_stream():
    """
    Streaming endpoint for real-time analysis progress updates using SSE.
    Sends progress events as the analysis pipeline executes.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for analysis progress"""
        db = None
        progress_events = []

        def progress_callback(step: str, status: str, message: str):
            """Callback to capture progress events"""
            event_data = {
                "step": step,
                "status": status,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            progress_events.append(event_data)

        try:
            # Create progress tracker with callback
            tracker = ProgressTracker(callback=progress_callback)

            # Step 1: Refresh market data
            yield f"data: {json.dumps({'step': 'refresh_data', 'status': 'started', 'message': 'Fetching latest market data from Binance and news sources...', 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)  # Allow event to be sent

            try:
                await asyncio.to_thread(RefreshManager.refresh_all_data)
                yield f"data: {json.dumps({'step': 'refresh_data', 'status': 'completed', 'message': 'Market data refreshed successfully', 'timestamp': datetime.now().isoformat()})}\n\n"
            except Exception as refresh_err:
                yield f"data: {json.dumps({'step': 'refresh_data', 'status': 'warning', 'message': f'Data refresh partial, proceeding with existing data', 'timestamp': datetime.now().isoformat()})}\n\n"

            await asyncio.sleep(0.1)

            # Step 2: Run trading graph with progress tracking
            graph = TradingGraph(progress_tracker=tracker)

            # Execute graph in thread and stream progress events
            result_container = {}

            def run_graph():
                result_container['result'] = graph.run()

            # Start graph execution in background
            import threading
            graph_thread = threading.Thread(target=run_graph)
            graph_thread.start()

            # Stream progress events as they arrive
            last_event_count = 0
            while graph_thread.is_alive():
                await asyncio.sleep(0.2)  # Check for new events every 200ms

                # Send any new events that were captured
                if len(progress_events) > last_event_count:
                    for event in progress_events[last_event_count:]:
                        yield f"data: {json.dumps(event)}\n\n"
                    last_event_count = len(progress_events)

            # Wait for thread to complete
            graph_thread.join()

            # Send any remaining events
            if len(progress_events) > last_event_count:
                for event in progress_events[last_event_count:]:
                    yield f"data: {json.dumps(event)}\n\n"

            # Step 3: Prepare and send final result
            result = result_container.get('result', {})
            db = get_db_session()
            timestamp = datetime.now()

            # Sanitize all text fields
            sanitized_result = sanitize_dict(result)

            final_response = TradeAnalysisResponse(
                technical_analysis=sanitized_result.get('technical', {}),
                news_analysis=sanitized_result.get('news', {}),
                reflection_analysis=sanitized_result.get('reflection', {}),
                trader_analysis=sanitized_result.get('trader', {}),
                timestamp=timestamp.isoformat()
            )

            # Send completion event with full result
            yield f"data: {json.dumps({'step': 'complete', 'status': 'completed', 'message': 'Analysis complete', 'result': final_response.model_dump(), 'timestamp': datetime.now().isoformat()})}\n\n"

        except Exception as e:
            # Send error event
            error_event = {
                "step": "error",
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"

            if db:
                db.rollback()

        finally:
            if db:
                db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


