#!/usr/bin/env python3
"""PIN Gate — validates PIN codes for CRITICAL actions."""

import sys
import io
import json
import os
import bcrypt
from pathlib import Path
from datetime import datetime, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Paths relative to this script's location
SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent  # skills/buddy-security -> project root
CONFIG_PATH = SKILL_DIR / "security_config.json"
LOCKOUT_PATH = PROJECT_ROOT / "data" / "pin_lockout.json"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def check_lockout():
    """Return True if currently locked out."""
    if not LOCKOUT_PATH.exists():
        return False
    with open(LOCKOUT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    lockout_until = datetime.fromisoformat(data.get("lockout_until", "2000-01-01"))
    if datetime.now() < lockout_until:
        remaining = (lockout_until - datetime.now()).seconds // 60
        print(json.dumps({"status": "lockout", "minutes_remaining": remaining}))
        return True
    LOCKOUT_PATH.unlink(missing_ok=True)
    return False


def verify_pin(pin_input: str) -> bool:
    """Verify PIN against bcrypt hash from env or config."""
    pin_hash = os.environ.get("BUDDY_PIN_HASH", "")
    if not pin_hash or pin_hash == "$2b$12$...":
        config = load_config()
        pin_hash = config.get("pin_hash", "")
    if not pin_hash or pin_hash == "CHANGE_ME_USE_BCRYPT":
        print(json.dumps({"status": "error", "message": "PIN hash not configured"}))
        sys.exit(1)
    return bcrypt.checkpw(pin_input.encode("utf-8"), pin_hash.encode("utf-8"))


def record_failure():
    """Record a failed PIN attempt; lockout after max_attempts."""
    config = load_config()
    lockout_data = {"attempts": 0, "lockout_until": None}
    if LOCKOUT_PATH.exists():
        with open(LOCKOUT_PATH, encoding="utf-8") as f:
            lockout_data = json.load(f)

    lockout_data["attempts"] = lockout_data.get("attempts", 0) + 1

    if lockout_data["attempts"] >= config.get("max_pin_attempts", 3):
        lockout_minutes = config.get("lockout_minutes", 15)
        lockout_until = datetime.now() + timedelta(minutes=lockout_minutes)
        lockout_data["lockout_until"] = lockout_until.isoformat()
        lockout_data["attempts"] = 0

    LOCKOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCKOUT_PATH, "w", encoding="utf-8") as f:
        json.dump(lockout_data, f)

    return lockout_data


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Usage: pin_gate.py <pin_code>"}))
        sys.exit(1)

    pin_input = sys.argv[1]

    if check_lockout():
        sys.exit(1)

    try:
        if verify_pin(pin_input):
            LOCKOUT_PATH.unlink(missing_ok=True)
            print(json.dumps({"status": "approved"}))
            sys.exit(0)
        else:
            result = record_failure()
            config = load_config()
            attempts_left = config.get("max_pin_attempts", 3) - result.get("attempts", 0)
            if result.get("lockout_until"):
                print(json.dumps({"status": "lockout", "minutes_remaining": config.get("lockout_minutes", 15)}))
            else:
                print(json.dumps({"status": "denied", "attempts_remaining": max(0, attempts_left)}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
