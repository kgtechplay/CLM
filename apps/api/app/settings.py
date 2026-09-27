"""Load API and LLM settings from apps/api/.env."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    app_env = os.getenv("APP_ENV", "development")
    allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
    llm_enabled = _bool("LLM_ENABLED", False)
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip() or "https://api.openai.com/v1"
    openai_chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    openai_moderation_model = os.getenv("OPENAI_MODERATION_MODEL", "omni-moderation-latest").strip()
    openai_timeout_seconds = _float("OPENAI_TIMEOUT_SECONDS", 20)
    openai_temperature = _float("OPENAI_TEMPERATURE", 0.4)
    openai_max_tokens = _int("OPENAI_MAX_TOKENS", 280)
    moderation_enabled = _bool("LLM_MODERATION_ENABLED", True)
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    admin_password = os.getenv("Admin_Password", "").strip()
    admin_token_ttl_seconds = _int("ADMIN_TOKEN_TTL_SECONDS", 28800)
    safety_profile_cache_ttl_seconds = _int("SAFETY_PROFILE_CACHE_TTL_SECONDS", 300)

    @property
    def llm_ready(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
