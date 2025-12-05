"""
API package - FastAPI application factory.
"""
from fastapi import FastAPI
from app.api.middleware import setup_middleware
from app.api.routes import create_routes


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI instance
    """
    app = FastAPI(
        title="Solana Trading Agent API",
        description="AI-powered trading analysis backend",
        version="1.0.0"
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Register routes
    routes = create_routes()
    app.include_router(routes)
    
    return app
