"""Tests for buddy-utils/env_loader.py."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-utils"
sys.path.insert(0, str(SKILL_PATH))

import env_loader


class TestLoadEnv:
    def test_loads_from_file(self, tmp_dir):
        (tmp_dir / ".env").write_text("TEST_XYZ=hello\n")
        with patch.object(env_loader, "_find_env_file", return_value=tmp_dir / ".env"):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TEST_XYZ", None)
                os.environ.pop("OPENROUTER_API_KEY", None)
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
                env_loader.load_env()
                assert os.environ.get("TEST_XYZ") == "hello"

    def test_skips_if_keys_set(self, tmp_dir):
        (tmp_dir / ".env").write_text("NEW=val\n")
        with patch.object(env_loader, "_find_env_file", return_value=tmp_dir / ".env"):
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "x", "TELEGRAM_BOT_TOKEN": "y"}):
                env_loader.load_env()
                assert os.environ.get("NEW") is None

    def test_no_overwrite(self, tmp_dir):
        (tmp_dir / ".env").write_text("EX=new\n")
        with patch.object(env_loader, "_find_env_file", return_value=tmp_dir / ".env"):
            with patch.dict(os.environ, {"EX": "old"}, clear=False):
                os.environ.pop("OPENROUTER_API_KEY", None)
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
                env_loader.load_env()
                assert os.environ["EX"] == "old"
