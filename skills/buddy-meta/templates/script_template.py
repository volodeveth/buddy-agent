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


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: {{SCRIPT_NAME}} <args>"}))
        sys.exit(1)

    try:
        # === GENERATED CODE BELOW ===
        {{GENERATED_CODE}}
        # === GENERATED CODE ABOVE ===
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
