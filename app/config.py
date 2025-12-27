
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # API Keys
    ANTHROPIC_API_KEY: str
    COINGECKO_API_KEY: Optional[str] = None
    SOLSCAN_API_KEY: Optional[str] = None
    HELIUS_API_KEY: Optional[str] = None

    # Database
    DATABASE_URL: str

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = int(os.getenv("PORT", "8000"))  # Render uses PORT env variable
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Environment detection - AWS Lambda sets AWS_EXECUTION_ENV
    IS_LAMBDA: bool = bool(os.getenv("AWS_EXECUTION_ENV"))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
