---
name: buddy-files
description: Secure file operations with whitelist enforcement. All file access must pass through this skill.
trigger:
  - on_file_operation
  - on_intent: file_read, file_write, file_delete, file_list, file_move
priority: 90
tools:
  - exec
  - read
  - write
---

## Rules

1. ALWAYS validate the file path via file_validator.py BEFORE any file operation
2. To validate, call exec tool:
```
python C:/Users/User/.openclaw/workspace/skills/buddy-files/file_validator.py "FILE_PATH" "ACTION"
```
Where ACTION is: read, write, or delete.

3. Read the JSON result:
   - `{"allowed": true, "level": "SAFE"}` → proceed without asking
   - `{"allowed": true, "level": "MEDIUM"}` → ask user confirmation
   - `{"allowed": true, "level": "CRITICAL"}` → require PIN via buddy-security
   - `{"allowed": false, "level": "BLOCKED"}` → refuse, explain why
   - `{"allowed": false, "level": "CRITICAL"}` → ask user permission first

4. Whitelisted directories (from security_config.json):
   - D:/BuddyWorkspace/
   - D:/Projects/
   - D:/Documents/
5. NEVER touch: C:/Windows/, C:/Program Files/, system directories
6. Delete operations → ALWAYS CRITICAL level via buddy-security
7. Sensitive files (*.env, *.key, etc.) → ALWAYS CRITICAL
8. When creating files, suggest appropriate directory from whitelist
9. When organizing files, show the plan before executing
10. Maximum file size for creation: 100MB
