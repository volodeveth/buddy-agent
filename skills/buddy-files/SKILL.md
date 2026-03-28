---
name: buddy-files
description: Secure file operations with whitelist enforcement. All file access must pass through this skill.
trigger:
  - on_file_operation
  - on_intent: file_read, file_write, file_delete, file_list, file_move
priority: 90
tools:
  - file_read
  - file_write
  - shell
---

## Rules

1. ALWAYS validate the file path via file_validator.py BEFORE any file operation
2. Whitelisted directories (from security_config.json):
   - D:/BuddyWorkspace/
   - D:/Projects/
   - D:/Documents/
3. If path NOT in whitelist -> delegate to buddy-security (REQUEST PERMISSION)
4. NEVER touch: C:/Windows/, C:/Program Files/, system directories
5. Delete operations -> ALWAYS CRITICAL level via buddy-security
6. Sensitive files (*.env, *.key, etc.) -> ALWAYS CRITICAL
7. When creating files, suggest appropriate directory from whitelist
8. When organizing files, show the plan before executing
9. Maximum file size for creation: 100MB
