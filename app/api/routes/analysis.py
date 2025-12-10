
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid

from app.api.schemas import TradeAnalysisResponse
from app.agents.pipeline import TradingGraph
from app.database.config import get_db_session
from app.database.models import TechnicalAnalyst, NewsAnalyst, ReflectionAnalyst, RiskAnalyst, TraderAnalyst
from app.data.refresh_manager import RefreshManager

router = APIRouter(prefix="/api", tags=["analysis"])


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

        return TradeAnalysisResponse(
            technical_analysis = result.get('technical', {}),
            news_analysis = result.get('news', {}),
            reflection_analysis = result.get('reflection', {}),
            trader_analysis = result.get('trader', {}),
            timestamp = timestamp.isoformat()
        )

    except Exception as e:
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if db:
            db.close()
