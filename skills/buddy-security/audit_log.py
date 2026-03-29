#!/usr/bin/env python3
"""Audit Logger — logs every action to a JSONL file."""

import sys
import io
import json
import os
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent  # skills/buddy-security -> project root
AUDIT_PATH = PROJECT_ROOT / "data" / "audit.jsonl"


def log_action(action: str, target: str, level: str, decision: str,
               pin_used: bool = False, initiated_by: str = "user_message",
               original_message: str = "", execution_result: str = "pending"):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "target": target,
        "security_level": level,
        "decision": decision,
        "pin_used": pin_used,
        "initiated_by": initiated_by,
        "original_message": original_message,
        "execution_result": execution_result
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def main():
    if len(sys.argv) < 5:
        print(json.dumps({"error": "Usage: audit_log.py <action> <target> <level> <decision> [pin_used] [original_message] [result]"}))
        sys.exit(1)

    action = sys.argv[1]
    target = sys.argv[2]
    level = sys.argv[3]
    decision = sys.argv[4]
    pin_used = sys.argv[5].lower() == "true" if len(sys.argv) > 5 else False
    original_message = sys.argv[6] if len(sys.argv) > 6 else ""
    result = sys.argv[7] if len(sys.argv) > 7 else "pending"

    entry = log_action(action, target, level, decision, pin_used, "user_message", original_message, result)
    print(json.dumps(entry, ensure_ascii=False))


if __name__ == "__main__":
    main()
