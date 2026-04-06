#!/usr/bin/env python3
"""Scheduler — manages reminders stored in reminders.json."""

import sys
import io
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Kyiv timezone: UTC+2 (winter) / UTC+3 (summer)
# Simple approach: use system local time
REMINDERS_PATH = Path(__file__).parent / "reminders.json"


def load_reminders() -> list:
    if not REMINDERS_PATH.exists():
        return []
    with open(REMINDERS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("reminders", [])


def save_reminders(reminders: list):
    with open(REMINDERS_PATH, "w", encoding="utf-8") as f:
        json.dump({"reminders": reminders}, f, ensure_ascii=True, indent=2)


def add_reminder(text: str, trigger_at: str, recurring: str = None) -> dict:
    """Add a new reminder.

    Args:
        text: Reminder text
        trigger_at: ISO format datetime string (e.g. "2026-03-29T08:00:00")
        recurring: Optional cron-like expression (e.g. "daily", "weekly:monday", "weekdays")
    """
    reminders = load_reminders()
    reminder = {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "trigger_at": trigger_at,
        "recurring": recurring,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    reminders.append(reminder)
    save_reminders(reminders)
    return {"status": "added", "reminder": reminder}


def list_reminders(show_all: bool = False) -> dict:
    """List active reminders (or all if show_all=True)."""
    reminders = load_reminders()
    if not show_all:
        reminders = [r for r in reminders if r.get("status") == "active"]
    return {"status": "ok", "count": len(reminders), "reminders": reminders}


def cancel_reminder(reminder_id: str) -> dict:
    """Cancel a reminder by ID."""
    reminders = load_reminders()
    for r in reminders:
        if r["id"] == reminder_id:
            r["status"] = "cancelled"
            save_reminders(reminders)
            return {"status": "cancelled", "reminder": r}
    return {"status": "not_found", "id": reminder_id}


def check_due() -> dict:
    """Check for reminders that are due now. Returns list of triggered reminders."""
    reminders = load_reminders()
    now = datetime.now()
    triggered = []

    for r in reminders:
        if r.get("status") != "active":
            continue
        try:
            trigger_time = datetime.fromisoformat(r["trigger_at"])
            # Strip timezone info for comparison (both become naive local time)
            if trigger_time.tzinfo is not None:
                trigger_time = trigger_time.replace(tzinfo=None)
        except (ValueError, KeyError):
            continue

        if trigger_time <= now:
            triggered.append(r)

            if r.get("recurring"):
                # Reschedule recurring reminder
                next_time = _calc_next_occurrence(trigger_time, r["recurring"])
                r["trigger_at"] = next_time.isoformat()
            else:
                r["status"] = "completed"

    if triggered:
        save_reminders(reminders)

    return {"status": "ok", "triggered": triggered, "count": len(triggered)}


def _calc_next_occurrence(from_time: datetime, recurring: str) -> datetime:
    """Calculate next occurrence for recurring reminders."""
    recurring = recurring.lower().strip()

    if recurring == "daily":
        return from_time + timedelta(days=1)
    elif recurring == "weekdays":
        next_day = from_time + timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekends
            next_day += timedelta(days=1)
        return next_day
    elif recurring.startswith("weekly"):
        return from_time + timedelta(weeks=1)
    elif recurring == "monthly":
        import calendar
        year = from_time.year + (from_time.month // 12)
        month = (from_time.month % 12) + 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(from_time.day, max_day)
        return from_time.replace(year=year, month=month, day=day)
    else:
        # Default: daily
        return from_time + timedelta(days=1)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: scheduler.py <command> [args]",
            "commands": {
                "add": "scheduler.py add <text> <trigger_at_iso> [recurring]",
                "list": "scheduler.py list [all]",
                "cancel": "scheduler.py cancel <reminder_id>",
                "check": "scheduler.py check"
            }
        }))
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: scheduler.py add <text> <trigger_at> [recurring]"}))
            sys.exit(1)
        text = sys.argv[2]
        trigger_at = sys.argv[3]
        recurring = sys.argv[4] if len(sys.argv) > 4 else None
        result = add_reminder(text, trigger_at, recurring)

    elif cmd == "list":
        show_all = len(sys.argv) > 2 and sys.argv[2] == "all"
        result = list_reminders(show_all)

    elif cmd == "cancel":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: scheduler.py cancel <reminder_id>"}))
            sys.exit(1)
        result = cancel_reminder(sys.argv[2])

    elif cmd == "check":
        result = check_due()

    else:
        result = {"error": f"Unknown command: {cmd}"}

    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
