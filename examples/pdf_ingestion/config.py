"""Configuration for the PDF ingestion example."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.pdf_path: str = os.getenv("PDF_PATH", "assets/big.pdf")
        self.output_path: str = os.getenv("OUTPUT_PATH") or str(
            Path(self.pdf_path).with_suffix(".txt")
        )
        self.pipetree_host: str = os.getenv("PIPETREE_HOST", "https://pipetree.io")
        self.pipetree_api_key: str = os.getenv("PIPETREE_API_KEY", "")


settings = Settings()
