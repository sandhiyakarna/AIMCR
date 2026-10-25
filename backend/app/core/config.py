import os
from typing import Any
from pydantic import field_validator, model_validator

# Disable Hugging Face telemetry and online checking to speed up imports
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AIMCR"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "AIMCR_SECRET_KEY_FOR_JWT_SECURITY_DO_NOT_USE_IN_PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # SQLite default dynamically resolved relative to project backend root
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'aimcr.db').replace('\\', '/')}"
    )
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def adjust_database_url(cls, v: Any) -> Any:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    
    # AI/ML Configurations
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_API_BASE: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"
    
    # Background processing: 'background_tasks' (FastAPI default) or 'celery'
    WORKER_BACKEND: str = os.getenv("WORKER_BACKEND", "background_tasks")
    
    # Reports storage directory (configurable, defaults to <project>/backend/reports)
    REPORTS_DIR: str = os.getenv(
        "REPORTS_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports")
    )
    
    # CORS allowed origins (comma-separated in env var)
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000"
    )
    
    # File upload constraints
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))  # 50 MB default
    ALLOWED_MIME_TYPES: str = os.getenv(
        "ALLOWED_MIME_TYPES",
        "application/json,text/plain,text/csv,application/octet-stream"
    )
    
    @model_validator(mode="after")
    def sync_ollama_urls(self) -> "Settings":
        if self.OLLAMA_BASE_URL:
            self.OLLAMA_API_BASE = self.OLLAMA_BASE_URL
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
