"""
Centralized logging configuration.
"""
import logging
from app.config import settings


def setup_logger(name: str) -> logging.Logger:
    """
    Setup and return a configured logger.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# Create module-level logger
logger = setup_logger(__name__)
