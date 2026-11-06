"""Настройки приложения из переменных окружения."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_CORS = ("http://localhost:3000", "http://localhost:5173")


@dataclass(frozen=True)
class Settings:
    data_file: Path | None = None
    anthropic_api_key: str | None = None
    model: str = DEFAULT_MODEL
    cors_origins: tuple[str, ...] = DEFAULT_CORS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        data_file = env.get("UNISPACE_DATA_FILE", "").strip()
        origins = env.get("UNISPACE_CORS_ORIGINS", "")
        parsed = tuple(o.strip() for o in origins.split(",") if o.strip())
        return cls(
            data_file=Path(data_file) if data_file else None,
            anthropic_api_key=env.get("ANTHROPIC_API_KEY", "").strip() or None,
            model=env.get("UNISPACE_MODEL", "").strip() or DEFAULT_MODEL,
            cors_origins=parsed or DEFAULT_CORS,
        )
