"""
API routes package - registers all route modules.
"""
from fastapi import APIRouter
from app.api.routes import health, analysis, trades, market, portfolio

def create_routes() -> APIRouter:
    """Create and register all API routes"""
    router = APIRouter()
    
    # Include root and health routes
    router.include_router(health.router)
    
    # Include resource-specific routes
    router.include_router(analysis.router)
    router.include_router(trades.router)
    router.include_router(market.router)
    router.include_router(portfolio.router)
    
    return router
