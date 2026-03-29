---
name: buddy-scheduler
description: Set reminders, schedule tasks, manage recurring jobs. Checks for due reminders on heartbeat.
trigger:
  - on_intent: set_reminder, cancel_reminder, list_reminders, schedule_task
  - on_heartbeat
priority: 50
tools:
  - exec
  - read
  - write
---

## Reminder Types

### One-time reminder
"Remind me at 15:00 to call Oleg"
-> Calculate ISO datetime, store via scheduler.py

### Recurring reminder
"Every Monday at 9:00 remind me about standup"
-> Store with recurring type: "weekly"

### Relative reminder
"Remind me in 2 hours about the meeting"
-> Calculate absolute time from now, store as one-time

## How to Use

### Add a reminder
Call exec:
```
python C:/Users/User/.openclaw/workspace/skills/buddy-scheduler/scheduler.py add "REMINDER_TEXT" "ISO_DATETIME" ["RECURRING_TYPE"]
```
RECURRING_TYPE: daily, weekdays, weekly, monthly (optional)

### List active reminders
```
python C:/Users/User/.openclaw/workspace/skills/buddy-scheduler/scheduler.py list
```

### Cancel a reminder
```
python C:/Users/User/.openclaw/workspace/skills/buddy-scheduler/scheduler.py cancel "REMINDER_ID"
```

### Check for due reminders (called on heartbeat)
```
python C:/Users/User/.openclaw/workspace/skills/buddy-scheduler/scheduler.py check
```

## Time Parsing Rules
- Understand Ukrainian time expressions: "о 15:00", "через 2 години", "завтра о 10:00"
- Convert relative time ("через 2 години") to absolute ISO datetime before calling scheduler.py
- User timezone: Europe/Kyiv (UTC+2 winter / UTC+3 summer)
- Current time: use system local time

## Security
- Setting a reminder: MEDIUM (ask user to confirm)
- Canceling a reminder: SAFE
- Listing reminders: SAFE
