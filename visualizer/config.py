"""Configuration for the visualizer application."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
DATABASES_CONFIG_PATH = PROJECT_ROOT / "databases.json"

_default_db = PROJECT_ROOT / "examples" / "pdf_ingestion" / "db" / "progress.db"


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.db_path: str = os.getenv("DB_PATH", str(_default_db))
        self.secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me-at-least-32b")
        self.sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "")
        self.mailer_enabled: bool = os.getenv("MAILER_ENABLED", "false").lower() in (
            "true",
            "1",
            "yes",
        )

    @property
    def default_db_path(self) -> Path:
        return Path(self.db_path)


settings = Settings()
