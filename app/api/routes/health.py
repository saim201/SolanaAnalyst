from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.api.schemas import HealthResponse, StatusResponse
from app.database.config import get_db_session
from sqlalchemy import text
import requests

router = APIRouter()


@router.get("/", response_model=StatusResponse)
def root():
    return {
        "status": "online",
        "service": "Solana Trading Agent API",
        "version": "1.0.0"
    }


@router.get("/health", response_model=HealthResponse)
def health():
    """
    Comprehensive health check endpoint
    Verifies database connectivity and external API availability
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "trading-agent",
        "checks": {
            "database": "unknown",
            "binance_api": "unknown"
        }
    }

    # Check database connectivity
    try:
        db = get_db_session()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)[:100]}"
        health_status["status"] = "degraded"

    # Check Binance API connectivity
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/ping",
            timeout=5
        )
        if response.status_code == 200:
            health_status["checks"]["binance_api"] = "healthy"
        else:
            health_status["checks"]["binance_api"] = f"unhealthy: status {response.status_code}"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["binance_api"] = f"unhealthy: {str(e)[:100]}"
        health_status["status"] = "degraded"

    return health_status
