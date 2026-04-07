"""Tests for buddy-scheduler/scheduler.py."""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-scheduler"
sys.path.insert(0, str(SKILL_PATH))

import scheduler


@pytest.fixture(autouse=True)
def tmp_reminders(tmp_dir):
    with patch.object(scheduler, "REMINDERS_PATH", tmp_dir / "reminders.json"):
        yield


class TestAddReminder:
    def test_adds(self):
        r = scheduler.add_reminder("Test", "2026-12-31T10:00:00")
        assert r["status"] == "added" and len(r["reminder"]["id"]) == 8

    def test_recurring(self):
        r = scheduler.add_reminder("Daily", "2026-04-07T09:00:00", "daily")
        assert r["reminder"]["recurring"] == "daily"


class TestListReminders:
    def test_empty(self):
        assert scheduler.list_reminders()["count"] == 0

    def test_active_only(self):
        scheduler.add_reminder("A", "2026-12-31T10:00:00")
        scheduler.add_reminder("B", "2026-12-31T11:00:00")
        rems = scheduler.load_reminders()
        rems[1]["status"] = "cancelled"
        scheduler.save_reminders(rems)
        assert scheduler.list_reminders()["count"] == 1


class TestCancelReminder:
    def test_cancel(self):
        rid = scheduler.add_reminder("Cancel", "2026-12-31T10:00:00")["reminder"]["id"]
        assert scheduler.cancel_reminder(rid)["status"] == "cancelled"

    def test_not_found(self):
        assert scheduler.cancel_reminder("nope")["status"] == "not_found"


class TestCheckDue:
    def test_triggers_past(self):
        scheduler.add_reminder("Overdue", (datetime.now() - timedelta(minutes=5)).isoformat())
        assert scheduler.check_due()["count"] == 1

    def test_skips_future(self):
        scheduler.add_reminder("Future", (datetime.now() + timedelta(hours=1)).isoformat())
        assert scheduler.check_due()["count"] == 0

    def test_recurring_reschedules(self):
        scheduler.add_reminder("Daily", (datetime.now() - timedelta(minutes=5)).isoformat(), "daily")
        scheduler.check_due()
        rems = scheduler.load_reminders()
        assert rems[0]["status"] == "active"
        assert datetime.fromisoformat(rems[0]["trigger_at"]) > datetime.now()


class TestCalcNext:
    def test_daily(self):
        assert scheduler._calc_next_occurrence(datetime(2026, 4, 6, 9), "daily") == datetime(2026, 4, 7, 9)

    def test_monthly_end(self):
        r = scheduler._calc_next_occurrence(datetime(2026, 1, 31, 9), "monthly")
        assert r.month == 2 and r.day == 28
