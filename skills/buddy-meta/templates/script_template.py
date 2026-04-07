#!/usr/bin/env python3
"""{{DESCRIPTION}}"""

import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# GENERATED SKILL: {{SKILL_NAME}}
# Created: {{CREATED_AT}}
# Purpose: {{PURPOSE}}

SKILL_DIR = Path(__file__).parent.resolve()


def _read_args() -> dict:
    """Read args from args.json file (primary) or sys.argv[1] (fallback).
    The bot writes args.json to SKILL_DIR before calling the script.
    This avoids Windows CLI quoting issues with JSON."""
    args_file = SKILL_DIR / "args.json"
    if args_file.exists():
        try:
            data = json.loads(args_file.read_text(encoding="utf-8"))
            args_file.unlink()
            return data
        except (json.JSONDecodeError, OSError):
            pass
    if len(sys.argv) > 1:
        try:
            return json.loads(sys.argv[1])
        except json.JSONDecodeError:
            pass
    return {}


def main():
    args = _read_args()
    if not args:
        print(json.dumps({"error": "No args. Write args.json to skill dir or pass JSON as argv[1]"}))
        sys.exit(1)

    try:
        # === GENERATED CODE BELOW ===
        {{GENERATED_CODE}}
        # === GENERATED CODE ABOVE ===
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=True))
        sys.exit(1)


if __name__ == "__main__":
    main()
