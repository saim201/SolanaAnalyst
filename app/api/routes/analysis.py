"""
Trading analysis endpoint.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid

from app.api.schemas import TradeAnalysisResponse
from app.agents.pipeline import TradingGraph
from app.database.config import get_db_session
from app.database.models import AgentAnalysis, TradeDecision
from app.data.refresh import RefreshManager

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/sol/analyse", response_model=TradeAnalysisResponse)
def analyse_trade():
    """
    Run full trading analysis cycle.
    
    1. Refreshes market data (price, indicators, news)
    2. Runs all agents (technical, news, reflection, trader)
    3. Saves analysis and decision to database
    4. Returns trading recommendation
    """
    db = None
    try:
        print("Refreshing market data for latest analysis...")
        try:
            RefreshManager.refresh_all_data(days=1)
        except Exception as refresh_err:
            print(f"Data refresh failed, proceeding with existing data: {str(refresh_err)}")

        run_id = str(uuid.uuid4())

        graph = TradingGraph()
        result = graph.run()

        db = get_db_session()

        # Save agent analysis
        agent_analysis = AgentAnalysis(
            run_id=run_id,
            technical_analysis=result.get('technical_analysis', ''),
            news_analysis=result.get('news_analysis', ''),
            reflection_analysis=result.get('reflection_analysis', ''),
            timestamp=datetime.now()
        )
        db.add(agent_analysis)
        db.flush()  # Flush to get the analysis.id

        # Save trade decision
        trade_decision = TradeDecision(
            analysis_id=agent_analysis.id,
            decision=result.get('decision', 'hold'),
            confidence=float(result.get('confidence', 0.5)),
            action=float(result.get('action', 0.0)),
            reasoning=result.get('reasoning', ''),
            timestamp=datetime.now()
        )
        db.add(trade_decision)
        db.commit()

        return TradeAnalysisResponse(
            decision=result.get('decision', 'hold'),
            confidence=float(result.get('confidence', 0.5)),
            action=float(result.get('action', 0.0)),
            reasoning=result.get('reasoning', ''),
            technical_analysis=result.get('technical_analysis', ''),
            news_analysis=result.get('news_analysis', ''),
            reflection_analysis=result.get('reflection_analysis', ''),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if db:
            db.close()
