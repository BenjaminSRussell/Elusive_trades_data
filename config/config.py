"""
Centralized configuration for the Fugitive Data Pipeline.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "fugitive_evidence"
    POSTGRES_USER: str = "fugitive_admin"
    POSTGRES_PASSWORD: str = "changeme_in_production"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9093"
    KAFKA_TOPIC_PDF_URLS: str = "pdf_urls"
    KAFKA_TOPIC_HTML_CONTENT: str = "html_content"
    KAFKA_TOPIC_FORUM_TEXT: str = "forum_text"

    # Splash Configuration
    SPLASH_URL: str = "http://localhost:8050"

    # NLP Configuration
    NLP_MODEL_PATH: str = "./phase3_nlp/models/custom_ner"
    BATCH_SIZE: int = 32

    # Scraping Configuration
    JOHNSTONE_USERNAME: str = ""
    JOHNSTONE_PASSWORD: str = ""
    CARRIER_USERNAME: str = ""
    CARRIER_PASSWORD: str = ""
    GRAINGER_USERNAME: str = ""
    GRAINGER_PASSWORD: str = ""

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    TEMP_DIR: Path = BASE_DIR / "temp"
    LOG_DIR: Path = BASE_DIR / "logs"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Create directories if they don't exist
settings.TEMP_DIR.mkdir(exist_ok=True)
settings.LOG_DIR.mkdir(exist_ok=True)
