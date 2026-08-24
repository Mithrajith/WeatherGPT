from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "WeatherGPT API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings (Default SQLite for local dev fallback, PostgreSQL in production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./weather_gpt.db"
    
    # Redis & Cache Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 1800  # 30 minutes
    
    # Security / Auth Settings
    SECRET_KEY: str = "weathergpt_super_secret_key_change_in_production_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # External IMD API Settings
    IMD_API_BASE_URL: str = "https://mausam.imd.gov.in/api"
    IMD_API_KEY: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
