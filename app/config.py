from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pydantic import model_validator
import os
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
    # Database settings
    database_url: str = "sqlite:///./knowledge_assistant.db"
    
    # Authentication settings
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Google Drive settings
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8002/api/v1/auth/google/callback"
    google_access_token: str = ""
    google_refresh_token: str = ""
    
    # Vector store settings
    embedding_model: str = "all-MiniLM-L6-v2"
    faiss_index_path: str = "./data/faiss_index.bin"
    
    # Celery settings
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None

    # Environment Configuration
    tokenizers_parallelism: bool = False

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }

    @model_validator(mode='before')
    def validate_settings(cls, values):
        # Load values from environment variables
        for field in cls.model_fields:
            env_val = os.getenv(field.upper())
            if env_val is not None:
                values[field] = env_val
        return values

settings = Settings() 