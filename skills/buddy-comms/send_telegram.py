#!/usr/bin/env python3
"""Send Telegram messages via Bot API directly (bypasses openclaw CLI)."""

import sys
import io
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent

_ENV_CANDIDATES = [
    PROJECT_ROOT / ".env",
    Path("D:/Myapps/buddy agent/.env"),
    Path.home() / ".openclaw" / "workspace" / ".env",
    Path.home() / ".openclaw" / "openclaw.json",
]


def _load_bot_token() -> str:
    """Load Telegram bot token from env or openclaw config."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        return token

    # Try .env files
    for env_path in _ENV_CANDIDATES[:-1]:
        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key == "TELEGRAM_BOT_TOKEN" and val:
                            return val

    # Try openclaw.json
    oc_config = Path.home() / ".openclaw" / "openclaw.json"
    if oc_config.exists():
        try:
            with open(oc_config, encoding="utf-8") as f:
                config = json.load(f)
            token = config.get("channels", {}).get("telegram", {}).get("botToken", "")
            if token:
                return token
        except (json.JSONDecodeError, KeyError):
            pass

    return ""


def send_telegram(chat_id: str, text: str) -> dict:
    """Send a message to a Telegram chat via Bot API."""
    token = _load_bot_token()
    if not token:
        return {"status": "error", "message": "Telegram bot token not found. Set TELEGRAM_BOT_TOKEN or check openclaw.json."}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode("utf-8")

    try:
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("ok"):
                return {"status": "success", "chat_id": chat_id, "message_id": result["result"]["message_id"]}
            else:
                return {"status": "error", "message": result.get("description", "Unknown Telegram API error")}
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body)
            return {"status": "error", "message": err.get("description", body)}
        except json.JSONDecodeError:
            return {"status": "error", "message": f"HTTP {e.code}: {body}"}
    except URLError as e:
        return {"status": "error", "message": f"Network error: {e.reason}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: send_telegram.py <chat_id> <message_text>"}))
        sys.exit(1)

    chat_id = sys.argv[1]
    text = sys.argv[2]

    result = send_telegram(chat_id, text)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
