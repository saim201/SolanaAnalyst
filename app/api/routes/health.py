from fastapi import APIRouter
from datetime import datetime
from app.api.schemas import HealthResponse, StatusResponse

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
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "trading-agent"
    }
