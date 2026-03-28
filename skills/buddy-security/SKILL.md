---
name: buddy-security
description: Security enforcement for all Buddy Agent actions. Classifies every action into SAFE/MEDIUM/CRITICAL and enforces appropriate confirmation.
trigger: always
priority: 100
tools:
  - send_message
  - shell
---

## Core Rule

Before EVERY action, classify it and enforce the appropriate security level.
NEVER skip this step. NEVER execute a CRITICAL action without PIN.
NEVER execute a MEDIUM action without user confirmation.

## Action Classification

### SAFE (execute without asking):
- Answer a question or have a conversation
- Search the web (DuckDuckGo)
- Search memory (recall facts, search history)
- Read files in whitelisted directories
- Show system status (CPU, RAM, disk)
- List tasks, reminders, contacts
- Generate text/code (show to user, don't save yet)

### MEDIUM (ask for confirmation via inline keyboard [Confirm] [Cancel]):
- Create or edit files in whitelisted directories
- Send an email to a known contact
- Send a Telegram message to a known contact
- Git commit and push
- Set or cancel a reminder
- Delete a memory entry
- Install an npm/pip package

### CRITICAL (require PIN code, 60-second timeout):
- Delete any file
- Execute a shell command (except whitelisted: git, npm, node, python)
- Deploy to any platform (Vercel, Railway, etc.)
- Access files outside whitelisted directories
- Add a directory to the whitelist
- Send messages ON BEHALF of the owner (not from bot, but impersonating owner)
- Any operation on files matching: *.env, *.key, *.pem, *password*, *secret*, *credential*
- Modify security_config.json
- Modify OpenClaw config.yaml

## PIN Gate Protocol

1. Send a Telegram message describing the action:
   "CRITICAL ACTION: [action type]
    Target: [what will be affected]
    Reason: [why this is needed]
    Enter PIN code (60 seconds):"

2. Wait for user response (max 60 seconds)
3. Validate PIN via pin_gate.py:
   - Correct -> execute action
   - Incorrect -> increment attempt counter
   - 3 incorrect attempts -> lockout for 15 minutes
   - Timeout (60s) -> cancel action, log as TIMEOUT
4. DELETE the PIN message from chat immediately after validation
5. Log the action via audit_log.py regardless of outcome

## Permission Request (for files outside whitelist)

When the user asks to access files outside whitelisted directories:

1. Verify the request was initiated by the user (not by the bot autonomously)
2. Send a Telegram message:
   "FILE ACCESS REQUEST
    Path: [full path]
    Action: [read/write/delete]
    Reason: executing your task '[original message]'
    [Allow once] [Add to whitelist (PIN required)] [Deny]"

3. "Allow once" -> grant temporary access for this single operation
4. "Add to whitelist" -> require PIN, then add to security_config.json
5. "Deny" -> cancel, suggest alternative

## Anti-Spoofing Rules

- The bot CANNOT initiate a permission request on its own
- The bot CANNOT simulate confirmation buttons
- The bot CANNOT execute actions during timeout period
- The bot CANNOT modify the whitelist without PIN
- All permission grants are logged in audit_log.py
- The bot CANNOT chain MEDIUM/CRITICAL actions without individual confirmations
