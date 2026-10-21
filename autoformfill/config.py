"""Settings loaded from environment variables (or a .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL = "openai/gpt-oss-120b"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    model: str = DEFAULT_MODEL
    timeout_s: float = 30.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        key = os.getenv("GROQ_API_KEY", "").strip()
        if not key:
            raise ConfigError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        return cls(groq_api_key=key, model=os.getenv("GROQ_MODEL", DEFAULT_MODEL))
