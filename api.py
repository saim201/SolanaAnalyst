from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.trading_agents import TradingGraph
from agents.db_fetcher import DataQuery
from database.config import get_db_session
from database.models import AgentAnalysis, TradeDecision

app = FastAPI(
    title="Solana Trading Agent API",
    description="AI-powered trading analysis backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://localhost:5174",
        "https://solscanapp.netlify.app",  
        ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TradeAnalysisResponse(BaseModel):
    decision: str
    confidence: float
    action: float
    reasoning: str
    onchain_analysis: str
    news_analysis: str
    reflection_analysis: str
    timestamp: str

class MarketDataResponse(BaseModel):
    price_data: str
    txn_data: str
    news_data: str

class PortfolioStatusResponse(BaseModel):
    cash: float
    sol_held: float
    price: float
    net_worth: float
    roi: float

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Solana Trading Agent API",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "trading-agent"
    }



@app.post("/api/sol/analyse", response_model=TradeAnalysisResponse)
def analyze_trade():
    db = None
    try:
        run_id = str(uuid.uuid4())

        graph = TradingGraph()
        result = graph.run()

        db = get_db_session()

        agent_analysis = AgentAnalysis(
            run_id=run_id,
            onchain_analysis=result.get('onchain_analysis', ''),
            news_analysis=result.get('news_analysis', ''),
            reflection_analysis=result.get('reflection_analysis', ''),
            timestamp=datetime.now()
        )
        db.add(agent_analysis)
        db.flush()  # Flush to get the analysis.id

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
            onchain_analysis=result.get('onchain_analysis', ''),
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


@app.get("/api/trades/history")
def get_trades_history(limit: int = 10):
    db = None
    try:
        db = get_db_session()
        trades = db.query(TradeDecision).order_by(TradeDecision.timestamp.desc()).limit(limit).all()
        trades_list = [
            {
                "id": trade.id,
                "decision": trade.decision,
                "confidence": trade.confidence,
                "action": trade.action,
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
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")
    finally:
        if db:
            db.close()


@app.get("/api/market/data", response_model=MarketDataResponse)
def get_market_data(days: int = 30):
    try:
        with DataQuery() as dq:
            price_data = dq.get_price_data(days=days)
            txn_data = dq.get_transaction_data(days=days)
            news_data = dq.get_news_data(days=days)

        return MarketDataResponse(
            price_data=price_data,
            txn_data=txn_data,
            news_data=news_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")



@app.get("/api/portfolio/status")
def get_portfolio_status():
    try:
        return {
            "cash": 500000,
            "sol_held": 3900.0,
            "price": 127.30,
            "net_worth": 1000000,
            "roi": 0.0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
