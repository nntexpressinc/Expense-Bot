"""
Configuration settings for Expenses Bot
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    USE_WEBHOOK: bool = False
    MINIAPP_URL: str = ""
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    SQL_ECHO: bool = False
    
    # Redis
    REDIS_URL: str
    REDIS_PASSWORD: str = ""
    
    # Security
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    JWT_SECRET: str = ""
    
    # Application
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    
    # Features
    ENABLE_NOTIFICATIONS: bool = True
    ENABLE_REPORTS: bool = True
    ENABLE_WEBHOOKS: bool = False
    MAX_TRANSFER_AMOUNT: float = 1000000.0
    MIN_TRANSACTION_AMOUNT: float = 0.01
    
    # External Services
    EXCHANGE_RATE_API_KEY: str = ""
    EXCHANGE_RATE_API_URL: str = "https://api.exchangerate-api.com/v4/latest/"
    
    # Monitoring
    SENTRY_DSN: str = ""
    PROMETHEUS_PORT: int = 9090
    
    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    
    # Reports
    REPORTS_DIR: str = "./reports"
    REPORTS_RETENTION_DAYS: int = 30
    
    # Localization
    DEFAULT_LANGUAGE: str = "ru"
    SUPPORTED_LANGUAGES: str = "ru,en,uz"
    
    @property
    def supported_languages_list(self) -> List[str]:
        """Parse supported languages from comma-separated string"""
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES.split(",") if lang.strip()]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_PERIOD: int = 60
    
    # Admin
    ADMIN_USER_IDS: str = ""
    
    @property
    def admin_ids(self) -> List[int]:
        """Parse admin IDs from comma-separated string"""
        if not self.ADMIN_USER_IDS:
            return []
        return [int(uid.strip()) for uid in self.ADMIN_USER_IDS.split(",") if uid.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
