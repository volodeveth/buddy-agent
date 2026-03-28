# Boot Sequence

On every startup:

1. Check OpenRouter API connection (ping with minimal request)
2. Check Telegram bot connection (getMe)
3. Load today's reminders from buddy-scheduler
4. Check for pending/incomplete tasks from previous session
5. Load today's and yesterday's memory notes
6. Send startup message to Telegram:
   "Buddy online. [N] нагадувань на сьогодні. [M] незавершених задач."
7. If any reminders are overdue (missed while offline), send them immediately

On error during boot:
- API connection failed: "Buddy partially online. AI unavailable, check OpenRouter API key."
- Telegram failed: log locally, retry every 60 seconds
- Non-critical error: boot anyway, report the issue
