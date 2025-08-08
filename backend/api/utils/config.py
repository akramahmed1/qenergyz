"""
Configuration Management

Application settings and environment configuration.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic Application Settings
    app_name: str = Field(default="Qenergyz ETRM API", env="APP_NAME")
    version: str = Field(default="1.0.0", env="VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Security Settings
    secret_key: str = Field(..., env="SECRET_KEY")
    encryption_key: Optional[str] = Field(None, env="ENCRYPTION_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    test_database_url: Optional[str] = Field(None, env="TEST_DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    query_timeout: int = Field(default=30, env="QUERY_TIMEOUT")
    
    # Cache Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=3600, env="RATE_LIMIT_PER_HOUR")
    
    # CORS Settings
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    cors_methods: list = Field(default=["*"], env="CORS_METHODS")
    cors_headers: list = Field(default=["*"], env="CORS_HEADERS")
    
    # Security
    allowed_hosts: list = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()