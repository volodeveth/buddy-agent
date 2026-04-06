#!/usr/bin/env python3
"""Shared environment loader for all buddy skills.

Reads .env file and sets missing environment variables.
Used by skills that need API keys, SMTP credentials, etc.
"""

import os
from pathlib import Path


def _find_env_file() -> Path | None:
    """Search for .env file in known locations."""
    candidates = [
        Path(__file__).parent.parent.parent / ".env",
        Path.home() / ".openclaw" / "workspace" / ".env",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_env() -> None:
    """Load .env file if key environment variables are missing.

    Reads the first .env file found in candidate locations and sets
    any variables not already present in os.environ.
    """
    if os.environ.get("OPENROUTER_API_KEY") and os.environ.get("TELEGRAM_BOT_TOKEN"):
        return

    env_path = _find_env_file()
    if env_path is None:
        return

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val:
                os.environ.setdefault(key, val)
