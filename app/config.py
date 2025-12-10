
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://postgres:1122@localhost:5432/CryptoAnalyst"

    # API Keys
    ANTHROPIC_API_KEY: str
    COINGECKO_API_KEY: Optional[str] = None
    SOLSCAN_API_KEY: Optional[str] = None

    # Scheduler
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_HOUR: int = 0
    SCHEDULER_MINUTE: int = 0

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Load settings
settings = Settings()
