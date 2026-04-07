---
name: buddy-meta
description: "Self-extending agent: creates new skills when current capabilities are insufficient. Uses MiniMax M2.7 for code generation via OpenRouter. ALWAYS requires PIN (CRITICAL level)."
trigger:
  - on_intent: create_tool, create_skill, extend_capability, new_function
  - on_keyword: "створи навик, новий інструмент, не вмію, потрібен тул, create tool, extend"
priority: 30
tools:
  - exec
  - read
  - write
---

## When to Trigger

If the user asks you to do something and NO existing skill can handle it:
1. Tell the user: "Для цього мені потрібен новий навик. Створити?"
2. If user agrees, call create_skill.py with the requirements
3. ALWAYS requires CRITICAL security level (PIN)

## Workflow

### Creating a New Skill (THREE-STEP PROCESS)

**Step 1:** Write request file using `file_write` tool:
Path: `C:/Users/User/.openclaw/workspace/skills/buddy-meta/request.json`
Content:
```json
{"action": "create", "need": "DESCRIBE WHAT IS NEEDED IN ENGLISH", "context": "original user message"}
```
Write "need" in ENGLISH — it goes to the code generator. Be technical and specific.

**Step 2:** Run the script via exec with NO arguments (IGNORE stdout):
```bash
python C:/Users/User/.openclaw/workspace/skills/buddy-meta/create_skill.py
```
The script reads request.json automatically and deletes it after reading.

**Step 3:** Read result using `file_read` tool (NOT exec, NOT cat):
Path: `C:/Users/User/.openclaw/workspace/skills/buddy-meta/last_result.json`

**IMPORTANT:** You do NOT write code. You ONLY describe what is needed. MiniMax M2.7 handles ALL engineering.

The script will:
1. Send the need to MiniMax M2.7 via OpenRouter API
2. MiniMax generates: skill name, description, SKILL.md, Python script
3. validate_code.py checks the generated code (AST analysis, forbidden patterns)
4. If invalid — MiniMax gets errors and retries (up to 3 attempts)
5. If valid — saves to `generated/<skill_name>/`, registers in skill_registry.json
6. Writes result to `last_result.json`

**If result JSON has `"status": "created"`, use `inline_exec` path to run immediately:**
```bash
python <inline_exec_path> <args>
```
NOTE: Generated skills live in `skills/buddy-meta/generated/<name>/`, NOT in `skills/<name>/`.

Tell user: "Навик створено. Працює зараз через пряме виконання."

**NEVER say "JSON is broken" — always read last_result.json with file_read tool instead.**

### Reading and Updating Skills

Write request.json, then run create_skill.py with no args, then read last_result.json:

```json
{"action": "read", "name": "buddy-skill-name"}
```
```json
{"action": "update", "name": "buddy-skill-name", "need": "Description of what to fix in English"}
```
```json
{"action": "list"}
```

### Managing Generated Skills

```bash
# Uninstall a skill (moves to _uninstalled/, MEDIUM security)
python skill_registry.py uninstall "buddy-skill-name"

# Reinstall a previously uninstalled skill (MEDIUM security)
python skill_registry.py reinstall "buddy-skill-name"
```

## SAFETY RULES (NON-NEGOTIABLE)

- NEVER create a skill that modifies buddy-security, buddy-meta, or buddy-files
- NEVER set priority above 40 for generated skills
- NEVER bypass validate_code.py checks
- NEVER save code that fails validation
- ALWAYS require PIN for skill creation
- ALWAYS show the user what the skill does before requesting PIN
- Maximum 20 active generated skills
- Maximum 800 lines per generated script
- Generated skills can ONLY use whitelisted imports (network domains are warnings only)
