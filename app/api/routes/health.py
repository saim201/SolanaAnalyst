"""
Health check and status endpoints.
"""
from fastapi import APIRouter
from datetime import datetime
from app.api.schemas import HealthResponse, StatusResponse

router = APIRouter()


@router.get("/", response_model=StatusResponse)
def root():
    """Root status endpoint"""
    return {
        "status": "online",
        "service": "Solana Trading Agent API",
        "version": "1.0.0"
    }


@router.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "trading-agent"
    }
