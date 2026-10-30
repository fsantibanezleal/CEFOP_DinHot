"""Config from environment (stdlib; no extra deps for the dormant lane). Only used when the backend is active."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()  # the single source (T4)


@dataclass
class Settings:
    """Read from the environment when instantiated (not at import), so a test or a process can set DATA_DIR."""
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "dev"))
    app_host: str = field(default_factory=lambda: os.getenv("APP_HOST", "127.0.0.1"))
    app_port: int = field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))
    dev_origins: str = field(default_factory=lambda: os.getenv("DEV_ORIGINS", "http://localhost:5173"))
    prod_origins: str = field(default_factory=lambda: os.getenv("PROD_ORIGINS", ""))
    data_dir: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data/derived"))


def origins(s: Settings) -> list[str]:
    raw = s.dev_origins if s.app_env == "dev" else s.prod_origins
    return [o.strip() for o in raw.split(",") if o.strip()]
