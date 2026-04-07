"""Shared test fixtures for Buddy Agent tests."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_config(tmp_dir):
    config = {
        "owner_telegram_id": "123456",
        "pin_hash": "$2b$12$test_hash_value",
        "whitelist_paths": [str(tmp_dir / "workspace")],
        "blacklist_commands": ["rm -rf /"],
        "sensitive_file_patterns": ["*.env", "*.key", "*.pem"],
        "max_pin_attempts": 3,
        "lockout_minutes": 15,
        "max_file_size_mb": 100,
        "audit_log_path": "data/audit.jsonl",
        "meta_skill_rules": {
            "max_script_lines": 800,
            "max_generated_priority": 40,
            "forbidden_imports": ["subprocess", "shutil", "ctypes"],
            "allowed_network_domains": ["api.privatbank.ua"],
        }
    }
    config_path = tmp_dir / "security_config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    (tmp_dir / "workspace").mkdir()
    return config_path


@pytest.fixture
def sample_contacts(tmp_dir):
    contacts = {
        "contacts": [
            {
                "name": "Ірина Дорош",
                "nickname": ["Ірина", "Іра"],
                "email": "iryna@example.com",
                "telegram": "123456",
                "viber": "",
                "role": "дружина",
                "notes": "test contact"
            }
        ]
    }
    path = tmp_dir / "contacts.json"
    path.write_text(json.dumps(contacts, ensure_ascii=False), encoding="utf-8")
    return path
