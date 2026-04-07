# Allowed Tools

## Always Available (SAFE)
- web_search: search the internet via DuckDuckGo
- file_read: read files in whitelisted directories
- send_message: send Telegram messages to owner
- memory_read: read from memory files
- memory_write: write to memory files

## With Confirmation (MEDIUM)
- file_write: create or edit files
- send_email: send email to contacts
- send_telegram: send Telegram messages to other users
- shell_safe: run whitelisted shell commands (git, npm, node, python)
- git_commit: commit changes
- git_push: push to remote
- set_reminder: create a reminder

## With PIN (CRITICAL)
- file_delete: delete files
- shell_exec: run arbitrary (but not blacklisted) shell commands
- deploy: deploy to Vercel/Railway
- send_as_owner: send messages impersonating the owner
- config_modify: change security or OpenClaw config
- whitelist_modify: add/remove directories from whitelist
- create_skill: create a new skill via buddy-meta. Ask user for PIN first (chat confirmation), then write request.json, then call exec with plain `python ...create_skill.py` (NO elevated flag, NO security parameter). See IDENTITY.md for full steps.
- update_skill: update an existing generated skill. Same flow as create_skill — PIN in chat, then write request.json, then plain exec. See IDENTITY.md.
