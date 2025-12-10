"""
Configuration settings using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Stack Auth
    stack_secret_server_key: str
    
    # Database
    database_url: str
    data_api_endpoint: Optional[str] = None
    
    # Polymarket
    polymarket_api_url: str = "https://api.polymarket.com"
    polymarket_api_key: Optional[str] = None
    
    # Server
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


# Global settings instance
settings = Settings()

