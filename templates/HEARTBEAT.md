# Heartbeat

Periodic health checks and scheduled task processing.

## On Every Heartbeat
1. Check for due reminders: `python skills/buddy-scheduler/scheduler.py check`
2. If any triggered, notify owner via Telegram with reminder text

## On Session Start
1. Run reminder check (same as above)
2. Verify API connectivity: confirm OPENROUTER_API_KEY is set
3. Check generated skills registry for any newly created skills

## Health Indicators
- Memory directory readable: `memory/` exists and contains MEMORY.md
- Audit log writable: `data/audit.jsonl` can be appended to
- Security config valid: `skills/buddy-security/security_config.json` parses as JSON
