import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    # App settings
    APP_NAME: str = "FastAPI Cloud Run Example"
    APP_DESCRIPTION: str = "A sample FastAPI application for Google Cloud Run"
    APP_VERSION: str = "0.1.0"

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a settings instance that will be imported by other modules
settings = Settings()