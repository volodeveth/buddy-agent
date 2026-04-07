#!/usr/bin/env python3
"""File Validator — checks if a file path is within whitelist and determines security level."""

import sys
import io
import json
import os
import fnmatch
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent  # skills/buddy-files -> project root
CONFIG_PATH = PROJECT_ROOT / "skills" / "buddy-security" / "security_config.json"

# System directories that must NEVER be accessed
BLOCKED_DIRS = [
    "C:/Windows", "C:/Program Files", "C:/Program Files (x86)",
    "C:/ProgramData", "C:/Recovery", "C:/System Volume Information",
]


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def normalize_path(path_str: str) -> str:
    """Normalize path for comparison (forward slashes, resolve)."""
    return str(Path(path_str).resolve()).replace("\\", "/")


def is_in_whitelist(path: str, whitelist: list[str]) -> bool:
    """Check if path is within any whitelisted directory."""
    norm_path = normalize_path(path).lower()
    for allowed in whitelist:
        norm_allowed = normalize_path(allowed).lower()
        if norm_path.startswith(norm_allowed):
            return True
    return False


def is_blocked(path: str) -> bool:
    """Check if path is in a system-blocked directory."""
    norm_path = normalize_path(path).lower()
    for blocked in BLOCKED_DIRS:
        if norm_path.startswith(blocked.lower()):
            return True
    return False


def is_sensitive(path: str, patterns: list[str]) -> bool:
    """Check if file matches sensitive patterns."""
    filename = Path(path).name
    for pattern in patterns:
        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
            return True
    return False


def validate(path: str, action: str = "read") -> dict:
    """Validate a file path and return security classification."""
    config = load_config()
    whitelist = config.get("whitelist_paths", [])
    sensitive_patterns = config.get("sensitive_file_patterns", [])
    max_size_mb = config.get("max_file_size_mb", 100)

    if is_blocked(path):
        return {
            "allowed": False,
            "level": "BLOCKED",
            "reason": f"System directory access is permanently blocked: {path}"
        }

    if is_sensitive(path, sensitive_patterns):
        return {
            "allowed": True,
            "level": "CRITICAL",
            "reason": f"Sensitive file pattern detected. PIN required.",
            "in_whitelist": is_in_whitelist(path, whitelist)
        }

    if action == "delete":
        return {
            "allowed": True,
            "level": "CRITICAL",
            "reason": "File deletion always requires PIN.",
            "in_whitelist": is_in_whitelist(path, whitelist)
        }

    if is_in_whitelist(path, whitelist):
        if action == "read":
            return {"allowed": True, "level": "SAFE", "reason": "Whitelisted path, read operation."}
        else:
            return {"allowed": True, "level": "MEDIUM", "reason": "Whitelisted path, write operation. Confirm with user."}

    return {
        "allowed": False,
        "level": "CRITICAL",
        "reason": f"Path outside whitelist. Request permission from user.",
        "in_whitelist": False
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: file_validator.py <path> [action: read|write|delete]"}))
        sys.exit(1)

    path = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "read"

    try:
        result = validate(path, action)
        result["path"] = path
        result["action"] = action
        print(json.dumps(result, ensure_ascii=True))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
