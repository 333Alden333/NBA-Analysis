"""Application configuration."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment or defaults."""

    db_path: str = os.getenv("HERMES_DB_PATH", "data/hermes.db")
    nba_api_min_delay: float = float(os.getenv("NBA_API_MIN_DELAY", "1.0"))
    nba_api_max_delay: float = float(os.getenv("NBA_API_MAX_DELAY", "2.0"))
    nba_api_max_retries: int = int(os.getenv("NBA_API_MAX_RETRIES", "3"))
    seasons: list[str] = field(
        default_factory=lambda: ["2022-23", "2023-24", "2024-25"]
    )


settings = Settings()
