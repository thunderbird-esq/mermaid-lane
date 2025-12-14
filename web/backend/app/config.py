"""
Configuration management for IPTV Web Backend.
Uses pydantic-settings for environment variable loading.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    app_name: str = "IPTV Web"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS Configuration
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    stream_rate_limit_per_minute: int = 20
    
    # Data Sources (iptv-org API)
    iptv_api_base: str = "https://iptv-org.github.io/api"
    
    # Cache Configuration
    cache_ttl_seconds: int = 3600  # 1 hour
    epg_cache_days: int = 7
    
    # Database
    database_path: str = "data/iptv_cache.db"
    
    # Pydantic V2 configuration
    model_config = SettingsConfigDict(env_prefix="IPTV_", env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
