# Heartbeat (every 30 minutes)

## Always
1. Check buddy-scheduler for due reminders
   - If any are due: send Telegram notification
   - If recurring: reschedule next occurrence
2. Check for pending long-running tasks
   - If completed: notify result
   - If failed: notify error, suggest retry

## Daily (21:00 Kyiv time)
3. Create daily summary in memory/YYYY-MM-DD.md:
   - Conversations summary
   - Actions taken (from audit log)
   - Reminders triggered
   - Files created/modified
   - Emails/messages sent

## Weekly (Sunday 21:00)
4. Create weekly digest:
   - Key decisions made
   - Projects worked on
   - Upcoming reminders for next week
