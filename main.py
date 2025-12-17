
import sys
import uvicorn
from app.api import create_app
from app.config import settings
from app.utils.logger import logger


def main():
    logger.info("Starting Solana Trading Agent API...")
    logger.info(f"API Host: {settings.API_HOST}")
    logger.info(f"API Port: {settings.API_PORT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")

    app = create_app()

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)
