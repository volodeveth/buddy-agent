"""Tests for buddy-security/audit_log.py."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-security"
sys.path.insert(0, str(SKILL_PATH))

import audit_log


class TestLogAction:
    def test_creates_entry(self, tmp_dir):
        log_path = tmp_dir / "audit.jsonl"
        with patch.object(audit_log, "AUDIT_PATH", log_path):
            entry = audit_log.log_action("file_read", "/test.txt", "SAFE", "approved")
        assert entry["action"] == "file_read"
        assert "timestamp" in entry
        parsed = json.loads(log_path.read_text().strip())
        assert parsed["action"] == "file_read"

    def test_appends(self, tmp_dir):
        log_path = tmp_dir / "audit.jsonl"
        with patch.object(audit_log, "AUDIT_PATH", log_path):
            audit_log.log_action("a1", "t1", "SAFE", "approved")
            audit_log.log_action("a2", "t2", "MEDIUM", "confirmed")
        assert len(log_path.read_text().strip().split("\n")) == 2

    def test_creates_parent(self, tmp_dir):
        log_path = tmp_dir / "nested" / "dir" / "audit.jsonl"
        with patch.object(audit_log, "AUDIT_PATH", log_path):
            audit_log.log_action("test", "target", "SAFE", "approved")
        assert log_path.exists()
