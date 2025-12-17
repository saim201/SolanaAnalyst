
from fastapi import APIRouter
from app.api.routes import health, analysis, trades, market

def create_routes() -> APIRouter:
    router = APIRouter()
    
    router.include_router(health.router)
    router.include_router(analysis.router)
    router.include_router(trades.router)
    router.include_router(market.router)
    
    return router
