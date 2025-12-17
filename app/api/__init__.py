
from fastapi import FastAPI
from app.api.middleware import setup_middleware
from app.api.routes import create_routes


def create_app() -> FastAPI:
    app = FastAPI(
        title="Solana Trading Agent API",
        description="AI-powered trading analysis backend",
        version="1.0.0"
    )
    
    setup_middleware(app)
    
    routes = create_routes()
    app.include_router(routes)
    
    return app
