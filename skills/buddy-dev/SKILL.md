---
name: buddy-dev
description: Development workflow - scaffold projects, generate code, git operations, deploy to Vercel/Railway.
trigger:
  - on_intent: create_project, write_code, git_commit, git_push, deploy
priority: 60
tools:
  - shell
  - file_read
  - file_write
  - web_search
---

## Workflow

### Scaffold (SAFE in whitelist)
1. Ask project type and name
2. Create in D:/Projects/<name>/
3. Show structure to user

### Code (SAFE show, MEDIUM write)
1. Generate code via DeepSeek
2. Show diff to user
3. On confirmation -> write (MEDIUM)

### Git (MEDIUM)
1. git add + show changes
2. Confirm -> commit with conventional message
3. git push (MEDIUM)

### Deploy (CRITICAL - PIN)
1. Show deployment plan
2. Require PIN
3. Run deploy script
4. Report URL
