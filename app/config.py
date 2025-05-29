"""
Application settings management using Pydantic.
Loads configuration from environment variables and .env file.

Author: João Machete
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """

    # App settings
    APP_NAME: Optional[str] = os.getenv("APP_NAME", "GitScape")
    APP_DESCRIPTION: Optional[str] = os.getenv("APP_DESCRIPTION", "Git repository analysis and digest generation tool")
    APP_VERSION: Optional[str] = os.getenv("APP_VERSION", "0.1.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a settings instance that will be imported by other modules
settings = Settings()
