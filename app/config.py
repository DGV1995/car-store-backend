"""
app/config.py — Centralized application configuration via Pydantic BaseSettings.

Reads environment variables and/or a ``.env`` file to provide typed,
validated settings for the entire application. Import the singleton
``settings`` instance and consume its fields directly.

Usage:
    from app.config import settings

    api_key = settings.deepseek_api_key
    model = settings.deepseek_model
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All fields are automatically populated from the corresponding
    environment variable. Supports loading from a ``.env`` file
    located at the project root.

    Attributes:
        deepseek_api_key: API key for DeepSeek (required).
            Reads from ``DEEPSEEK_API_KEY``.
        deepseek_model: Model identifier for DeepSeek.
            Reads from ``DEEPSEEK_MODEL``; defaults to
            ``"deepseek/deepseek-v4-flash"``.
    """

    deepseek_api_key: str = ""
    """DeepSeek API key. Required for AI chat functionality.
    Read from the ``DEEPSEEK_API_KEY`` environment variable."""

    deepseek_model: str = "deepseek/deepseek-v4-flash"
    """DeepSeek model identifier.
    Read from the ``DEEPSEEK_MODEL`` environment variable.
    Defaults to ``"deepseek/deepseek-v4-flash"``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton instance — all consumers share the same settings object.
settings = Settings()
