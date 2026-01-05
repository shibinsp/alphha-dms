from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings
import secrets
import os


def _get_secure_key(env_var: str, default_length: int = 32) -> str:
    """Get key from environment or generate secure random key for development."""
    key = os.environ.get(env_var)
    if key and key not in ["your-super-secret-key-change-in-production", "your-32-byte-encryption-key-here"]:
        return key
    # Generate secure random key for development
    return secrets.token_urlsafe(default_length)


class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "Alphha DMS"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./data/alphha.db"

    # Security - Keys generated securely if not provided in environment
    SECRET_KEY: str = _get_secure_key("SECRET_KEY", 32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Password Policy
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30

    # Session
    SESSION_IDLE_TIMEOUT_MINUTES: int = 30

    # Redis/Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".png", ".jpg", ".jpeg", ".gif", ".tiff",
        ".csv", ".txt"
    ]

    # Encryption - Key generated securely if not provided in environment
    ENCRYPTION_KEY: str = _get_secure_key("ENCRYPTION_KEY", 32)

    # OCR
    TESSERACT_PATH: Optional[str] = None
    OCR_LANGUAGES: str = "eng+ara"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Logging
    LOG_LEVEL: str = "INFO"

    # Mistral AI
    MISTRAL_API_KEY: Optional[str] = "Jh5S3cDgj09pyJgXzUXiOGxWukB8BSY2"
    MISTRAL_MODEL: str = "mistral-small-latest"

    # SMTP Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@alphha.io"
    SMTP_FROM_NAME: str = "Alphha DMS"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Module-level settings instance for convenience
settings = get_settings()
