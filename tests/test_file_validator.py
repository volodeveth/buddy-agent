"""Tests for buddy-files/file_validator.py."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-files"
sys.path.insert(0, str(SKILL_PATH))

import file_validator


@pytest.fixture(autouse=True)
def mock_config(sample_config, tmp_dir):
    with patch.object(file_validator, "CONFIG_PATH", sample_config):
        yield


class TestIsInWhitelist:
    def test_path_in_whitelist(self, tmp_dir):
        assert file_validator.is_in_whitelist(str(tmp_dir / "workspace" / "f.txt"), [str(tmp_dir / "workspace")])

    def test_path_outside_whitelist(self, tmp_dir):
        assert not file_validator.is_in_whitelist("C:/Windows/cmd.exe", [str(tmp_dir / "workspace")])


class TestIsBlocked:
    def test_system_dir_blocked(self):
        assert file_validator.is_blocked("C:/Windows/System32/cmd.exe")

    def test_user_dir_not_blocked(self):
        assert not file_validator.is_blocked("D:/Projects/myapp/main.py")


class TestIsSensitive:
    def test_env_file(self):
        assert file_validator.is_sensitive(".env", ["*.env"])

    def test_normal_file(self):
        assert not file_validator.is_sensitive("main.py", ["*.env"])


class TestValidate:
    def test_whitelisted_read_is_safe(self, tmp_dir):
        r = file_validator.validate(str(tmp_dir / "workspace" / "f.txt"), "read")
        assert r["level"] == "SAFE" and r["allowed"] is True

    def test_whitelisted_write_is_medium(self, tmp_dir):
        assert file_validator.validate(str(tmp_dir / "workspace" / "f.txt"), "write")["level"] == "MEDIUM"

    def test_delete_is_critical(self, tmp_dir):
        assert file_validator.validate(str(tmp_dir / "workspace" / "f.txt"), "delete")["level"] == "CRITICAL"

    def test_sensitive_is_critical(self, tmp_dir):
        assert file_validator.validate(str(tmp_dir / "workspace" / ".env"), "read")["level"] == "CRITICAL"

    def test_blocked_not_allowed(self):
        r = file_validator.validate("C:/Windows/System32/cmd.exe", "read")
        assert r["allowed"] is False and r["level"] == "BLOCKED"
