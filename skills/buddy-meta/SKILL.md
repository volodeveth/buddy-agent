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

### Creating a New Skill

```bash
python create_skill.py --action create \
  --need "WHAT user needs (plain language description)" \
  --context "original user message"
```

**IMPORTANT:** You (Gemini Flash) do NOT write code. You ONLY describe what is needed in `--need`. MiniMax M2.7 handles ALL engineering: plans architecture, writes code, self-reviews.

The script will:
1. Send the need to MiniMax M2.7 via OpenRouter API
2. MiniMax generates: skill name, description, SKILL.md, Python script
3. validate_code.py checks the generated code (AST analysis, forbidden patterns)
4. If invalid — MiniMax gets errors and retries (up to 3 attempts)
5. If valid — saves to `generated/<skill_name>/`, registers in skill_registry.json

**Response includes `inline_exec` path** — execute it immediately:
```bash
python <inline_exec_path> <args>
```

Tell user: "Навик створено. Працює зараз через пряме виконання. Для повної інтеграції почніть нову сесію."

### Managing Generated Skills

```bash
# List all generated skills
python skill_registry.py list

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
- Maximum 200 lines per generated script
- Generated skills can ONLY use whitelisted imports and network domains
