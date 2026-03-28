---
name: buddy-scheduler
description: Set reminders, schedule tasks, manage recurring jobs.
trigger:
  - on_intent: set_reminder, cancel_reminder, list_reminders
  - on_heartbeat
priority: 50
tools:
  - shell
  - send_message
  - file_read
  - file_write
---

## Reminder Types

### One-time: "Нагадай о 15:00 зателефонувати Олегу"
### Recurring: "Щопонеділка о 9:00 нагадуй про стендап"
### Relative: "Нагадай через 2 години про зустріч"

## Time Parsing
- Ukrainian expressions: "о 15:00", "через 2 години", "завтра о 10:00"
- Convert to UTC, display in Europe/Kyiv

## Security
- Setting: MEDIUM (confirm)
- Canceling: SAFE
- Listing: SAFE
