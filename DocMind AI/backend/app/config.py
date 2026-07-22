import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "DocMind AI"
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = "supersecretkey_docmind_ai_development_jwt_token_key_12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Database Settings
    DB_TYPE: str = "sqlite"  # 'postgresql' or 'sqlite'
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "docmind"
    DATABASE_URL: str | None = None
    
    # Caching
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # File Storage
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    
    # AI Pipeline Configuration
    AI_FALLBACK_MODE: bool = True  # Fallback to simulated AI if weights/libraries fail to load
    CONFIDENCE_THRESHOLD: float = 0.60
    
    # Admin Settings
    ADMIN_EMAIL: str = "admin@docmind.ai"
    ADMIN_PASSWORD: str = "Admin@DocMind123"

    @property
    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DB_TYPE == "postgresql":
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        # Fallback to SQLite
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        return f"sqlite:///{BASE_DIR}/docmind.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "temp"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "enhanced"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "crops"), exist_ok=True)
