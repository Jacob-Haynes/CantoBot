"""Configuration management for the Cantonese AI Tutor Bot."""

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    telegram_bot_token: str
    google_api_key: str
    allowed_user_id: int
    gemini_model: str
    db_path: str
    log_level: int
    health_check_port: int

    def __init__(self) -> None:
        # Load environment variables from .env file
        load_dotenv()

        # Required configuration
        self.telegram_bot_token: str = self._get_required_env("TELEGRAM_BOT_TOKEN")
        self.google_api_key: str = self._get_required_env("GOOGLE_API_KEY")

        # Parse allowed user ID
        user_id_str: str = self._get_required_env("ALLOWED_USER_ID")
        try:
            self.allowed_user_id: int = int(user_id_str)
        except ValueError:
            raise ValueError(f"ALLOWED_USER_ID must be an integer, got: {user_id_str}")

        # Optional configuration with defaults
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.db_path: str = os.getenv("DB_PATH", "data/cantonese_tutor.db")

        # Parse log level
        log_level_str: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_level: int = getattr(logging, log_level_str, logging.INFO)

        # Parse health check port
        health_check_port_str: str = os.getenv("HEALTH_CHECK_PORT", "8080")
        try:
            self.health_check_port: int = int(health_check_port_str)
        except ValueError:
            raise ValueError(f"HEALTH_CHECK_PORT must be an integer, got: {health_check_port_str}")

        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get a required environment variable or raise an error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"Missing required environment variable: {key}\n"
                f"Please set it in your .env file or environment.\n"
                f"See .env.example for reference."
            )
        return value
