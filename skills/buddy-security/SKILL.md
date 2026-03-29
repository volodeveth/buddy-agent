---
name: buddy-security
description: Security enforcement for all Buddy Agent actions. Classifies every action into SAFE/MEDIUM/CRITICAL and enforces appropriate confirmation.
trigger: always
priority: 100
tools:
  - exec
  - read
  - write
---

## Core Rule

Before EVERY action, classify it and enforce the appropriate security level.
NEVER skip this step. NEVER execute a CRITICAL action without PIN.
NEVER execute a MEDIUM action without user confirmation.

## Action Classification

### SAFE (execute without asking):
- Answer a question or have a conversation
- Search the web
- Search memory (recall facts, search history)
- Read files in whitelisted directories (D:/BuddyWorkspace, D:/Projects, D:/Documents)
- List tasks, reminders, contacts
- Generate text/code (show to user, don't save yet)

### MEDIUM (ask user "Виконати? Так/Ні"):
- Create or edit files in whitelisted directories
- Send an email to a known contact
- Git commit and push
- Set or cancel a reminder
- Delete a memory entry
- Install an npm/pip package

### CRITICAL (require PIN code, 60-second timeout):
- Delete any file
- Execute shell commands (except whitelisted: git, npm, node, python)
- Deploy to any platform (Vercel, Railway)
- Access files outside whitelisted directories
- Modify security_config.json or OpenClaw config
- Any operation on sensitive files (*.env, *.key, *.pem, *secret*, *credential*)

## How to request confirmation (MEDIUM)

Ask user: "Дія: [опис]\nЦіль: [що буде змінено]\nВиконати? (Так/Ні)"
Wait for response. Proceed only if user confirms.

## How to request PIN (CRITICAL)

Ask user: "⚠️ CRITICAL: [опис дії]\nЦіль: [що буде змінено]\nВведіть PIN (60 секунд):"
Then validate by calling exec tool:
```
python C:/Users/User/.openclaw/workspace/skills/buddy-security/pin_gate.py "USER_PIN_HERE"
```
- `{"status": "approved"}` → execute action
- `{"status": "denied", "attempts_remaining": N}` → "Невірний PIN. Залишилось спроб: N"
- `{"status": "lockout", "minutes_remaining": N}` → "Акаунт заблоковано на N хвилин"

## Audit Logging

After every action, log it by calling exec:
```
python C:/Users/User/.openclaw/workspace/skills/buddy-security/audit_log.py "ACTION" "TARGET" "LEVEL" "DECISION"
```

## Anti-Spoofing Rules

- Bot CANNOT self-approve actions
- Bot CANNOT execute during lockout
- Bot CANNOT modify whitelist without PIN
- Bot CANNOT chain actions without individual confirmations
