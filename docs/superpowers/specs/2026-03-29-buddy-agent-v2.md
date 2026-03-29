# Buddy Agent v2 — Updated Design & Implementation Plan

**Date:** 2026-03-29 | **Status:** Draft | **Supersedes:** Phases 4+ of original spec

---

## Current State (Phases 1-3: COMPLETE)

| Skill | Priority | Status | Key Files |
|-------|----------|--------|-----------|
| buddy-security | 100 | DONE | pin_gate.py, audit_log.py, security_config.json |
| buddy-files | 90 | DONE | file_validator.py |
| buddy-voice-ua | 80 | DONE | stt_whisper.py (medium model), tts_edge.py, voice_utils.py |
| buddy-comms | 70 | DONE | contacts_lookup.py, send_email.py, send_telegram.py |
| buddy-dev | 60 | STUB | SKILL.md only, no scripts/templates |
| buddy-scheduler | 50 | DONE | scheduler.py, reminders.json |
| buddy-search | 50 | STUB | SKILL.md only, no search_router.py |
| buddy-business | — | EMPTY | Directory exists, no files |

**Key constraint:** Skills discovered at SESSION START only. New skills not visible until next session.

---

## Dual LLM Architecture

```
User message → Telegram Gateway → OpenClaw
                                     |
                              Gemini 2.0 Flash (Dispatcher)
                              95% of all work: chat, classify,
                              call existing tools, dispatch
                                     |
                    ┌────────────────┴────────────────┐
                    |                                  |
            [Existing skills]                 [Need new skill?]
            exec existing .py                         |
            scripts directly                   create_skill.py
                                                      |
                                              ┌───────┴───────┐
                                              |               |
                                         [Simple?]      [Complex?]
                                              |               |
                                        Gemini Flash    MiniMax M2.7
                                        generates       via OpenRouter
                                        code inline     generates code
                                              |               |
                                              └───────┬───────┘
                                                      |
                                              validate_code.py
                                              (AST + safety check)
                                                      |
                                              Save → generated/
                                              Register → registry
                                              Exec inline now
                                              Full skill next session
```

### Model Roles

| Model | Role | When | Cost |
|-------|------|------|------|
| **Gemini 2.0 Flash** | Dispatcher | 95% of time — chat, tool calls, classify. Describes WHAT is needed | ~$0.10/1M input |
| **MiniMax M2.7** | Architect + Engineer | ALL skill creation: plans, designs, writes, self-checks code | ~$0.15/1M input |

### Division of Responsibility

**Gemini Flash (dispatcher) ONLY:**
- Detects that a request requires a new skill
- Describes the NEED in natural language: "User needs a currency checker that..."
- Calls `create_skill.py` with the need description
- Receives the finished skill back
- Executes it and reports result to user

**MiniMax M2.7 (engineer) does ALL the rest:**
- Receives the need description from Gemini
- Plans the skill architecture (what scripts, what APIs, what data format)
- Writes the system prompt for itself (self-prompting)
- Generates the complete Python code
- Self-reviews: checks for errors, edge cases, security issues
- Iterates if needed (MiniMax has built-in self-correction loop)
- Returns the final, production-ready code

**Why this split?**
- Gemini Flash is fast but a "junior" — writes code with bugs, misses structure
- MiniMax M2.7 is a "senior engineer" — designs and writes correct code from first attempt
- Gemini describes the problem, MiniMax solves it. Clean separation.

### How It Works (in create_skill.py)

```python
# Step 1: Gemini Flash detects "I need a tool that doesn't exist"
# Step 2: Gemini calls create_skill.py with ONLY the need description:
#   python create_skill.py --action create \
#     --need "User needs to check UAH/USD exchange rates" \
#     --context "User asked: яким сьогодні курс долара?"
#
# Step 3: create_skill.py passes the need to MiniMax via generate_with_model.py
#   MiniMax receives:
#   - The need description
#   - The script template (mandatory structure)
#   - Safety constraints (forbidden imports, allowed domains)
#   - Existing skills list (to avoid duplication)
#
# Step 4: MiniMax plans + generates:
#   - Skill name, description, intents
#   - SKILL.md content
#   - Python script code
#   - All returned as structured JSON
#
# Step 5: create_skill.py validates via validate_code.py
# Step 6: If valid → saves, registers, returns to Gemini
# Step 7: Gemini executes inline and reports to user
```

### generate_with_model.py — The Model Router Script

```python
# New script that calls OpenRouter API with a specific model
# Used ONLY by buddy-meta when heavy code generation is needed
#
# Usage: python generate_with_model.py --model "minimax/MiniMax-M1-80k" \
#          --system "You are a Python code generator..." \
#          --prompt "Write a script that..." \
#          --template "..." (the script_template.py content)
#
# Reads OPENROUTER_API_KEY from .env
# Calls OpenRouter API (already whitelisted in sandbox)
# Returns: {"code": "...", "model_used": "minimax/MiniMax-M1-80k"}
```

This way MiniMax is called DIRECTLY via HTTP API from Python, not through the LLM layer. Gemini Flash never needs to "become" MiniMax — it just delegates to it via a script.

---

## Redefined Phases (4-8)

### CRITICAL CHANGE: buddy-meta is Phase 4 (FIRST)

The self-extending capability is the foundation. Once buddy-meta works, the agent builds everything else itself.

| Phase | Name | Built By | Effort |
|-------|------|----------|--------|
| **4** | **buddy-meta (self-extending + safety)** | **Us (human + Claude)** | **4-5d** |
| 5 | buddy-business, buddy-search, buddy-dev | **Agent via buddy-meta** (with owner approval) | 3-5d |
| 6 | Multi-user support | Us + Agent | 3-4d |
| 7+ | Future (Railway 24/7, Sheets, Viber, dashboard) | TBD | TBD |

**Philosophy:** We build the self-improvement engine + safety. The agent builds everything else. Owner approves (PIN) each new skill.

---

## Phase 4: buddy-meta — Self-Extending Agent (4-5 days)

### File Structure
```
skills/buddy-meta/
+-- SKILL.md                    (priority 30)
+-- create_skill.py             # orchestrator: assess, route, validate, save, register
+-- generate_with_model.py      # calls OpenRouter API with heavy model (MiniMax M2.7)
+-- validate_code.py            # AST static analysis + safety checks
+-- skill_registry.py           # CRUD: list, uninstall, reinstall
+-- templates/
|   +-- skill_template.md       # SKILL.md template for generated skills
|   +-- script_template.py      # Python script template (mandatory structure)
|   +-- system_prompt.txt       # System prompt for MiniMax when generating code
+-- generated/                  # ALL generated skills go here (isolated from core)
    +-- skill_registry.json     # metadata for all generated skills
```

### create_skill.py — Main Orchestrator

**Single command from Gemini Flash (just describes the need):**
```bash
python create_skill.py --action create \
  --need "User needs to check UAH/USD and UAH/EUR exchange rates" \
  --context "User asked: яким сьогодні курс долара?"
```

**What happens internally:**

1. `create_skill.py` packages the need + template + constraints
2. Calls `generate_with_model.py` → sends everything to MiniMax M2.7
3. MiniMax returns COMPLETE skill definition:
   - Skill name, description, intents, priority
   - SKILL.md content
   - Python script code (following template structure)
4. `create_skill.py` runs `validate_code.py` on the generated code
5. If valid → saves files, updates registry
6. If invalid → sends errors back to MiniMax for self-correction (up to 3 attempts)

**Returns to Gemini Flash:**
```json
{
  "status": "created",
  "skill_name": "buddy-currency",
  "description": "Перевірка курсу валют UAH/USD/EUR через PrivatBank API",
  "path": "skills/buddy-meta/generated/buddy-currency/",
  "files": ["SKILL.md", "currency.py"],
  "validation": {"valid": true, "warnings": []},
  "available_in": "next_session",
  "inline_exec": "python C:/Users/User/.openclaw/workspace/skills/buddy-meta/generated/buddy-currency/currency.py",
  "model_used": "minimax/MiniMax-M1-80k",
  "tokens_used": {"input": 1200, "output": 800},
  "attempts": 1
}
```

Gemini Flash then just executes the script inline and reports result to user. It never saw or touched the code — MiniMax did everything.

### generate_with_model.py — MiniMax Engineer Brain

This is the core of self-extension. Calls MiniMax M2.7 via OpenRouter API directly from Python (not through LLM layer). MiniMax does ALL engineering: planning, architecture, code generation, self-review.

```python
#!/usr/bin/env python3
"""Call MiniMax M2.7 via OpenRouter for full skill engineering.
MiniMax receives: need description + template + constraints.
MiniMax returns: complete skill (name, SKILL.md, Python code)."""

DEFAULT_MODEL = "minimax/MiniMax-M1-80k"
FALLBACK_MODEL = "deepseek/deepseek-chat-v3.2"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_ATTEMPTS = 3  # self-correction attempts
```

**System prompt for MiniMax (templates/system_prompt.txt):**

```
You are a skill engineer for the Buddy Agent system (OpenClaw framework).
Your job: receive a NEED description and produce a COMPLETE, production-ready skill.

You must return a JSON object with:
{
  "skill_name": "buddy-xxx",
  "description": "What this skill does",
  "intents": "comma,separated,intents",
  "priority": 35,
  "skill_md": "Full SKILL.md content with YAML frontmatter",
  "script_name": "xxx.py",
  "script_code": "Full Python script following the template below"
}

MANDATORY SCRIPT TEMPLATE:
[... script_template.py content injected here ...]

SAFETY CONSTRAINTS:
- ALLOWED imports: json, sys, io, pathlib, urllib.request, urllib.parse, datetime, re, math
- FORBIDDEN: subprocess, os.system, eval, exec, ctypes, socket, threading, shutil
- NO file writes (stdout-only via json.dumps)
- Network: ONLY to whitelisted domains: [list]
- Max 200 lines, max priority 40
- Error handling: try/except returning {"error": "message"}
- Ukrainian in user-facing strings

EXISTING SKILLS (do not duplicate):
[... list of existing skills injected here ...]

THINK CAREFULLY:
1. Plan the architecture before writing
2. Consider edge cases and error handling
3. Self-review your code for bugs and security issues
4. Return ONLY valid JSON, no explanations
```

**Self-correction loop:**
If `validate_code.py` finds errors in MiniMax output, `create_skill.py` sends errors BACK to MiniMax:
```
Previous code had these errors: [error list from validate_code.py]
Fix the code and return corrected JSON.
```
Up to 3 attempts. If all fail → report to user that skill creation failed.

**Why MiniMax M2.7?**
- Built for recursive self-improvement: treats errors as fuel, not failures
- 97% accuracy on complex tool descriptions (>2000 tokens)
- SWE-Pro benchmark: top tier code generation
- Native understanding of agent architectures and tool systems
- Available via OpenRouter

**Fallback chain:** MiniMax M2.7 → DeepSeek V3.2 (if MiniMax unavailable)

### templates/system_prompt.txt — Instructions for MiniMax

```
You are a Python code generator for the Buddy Agent system (OpenClaw framework).

STRICT RULES:
1. Generate ONLY the function body that goes inside the main() function
2. Use ONLY these imports: json, sys, io, pathlib.Path, urllib.request, urllib.parse, datetime, re, math
3. FORBIDDEN: subprocess, os.system, eval, exec, shutil.rmtree, socket, multiprocessing, threading
4. FORBIDDEN: any file write operations (open(..., "w"), Path.write_text, etc.)
5. ALL output MUST be via: print(json.dumps(result, ensure_ascii=False))
6. ALL input MUST be via: sys.argv[N]
7. Network requests: ONLY urllib.request.urlopen to whitelisted domains
8. Keep code under 150 lines
9. Include error handling: try/except that returns {"error": "message"} as JSON
10. Use Ukrainian in user-facing strings where appropriate

TEMPLATE STRUCTURE (you fill in the {{GENERATED_CODE}} section):
```python
def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: script.py <args>"}))
        sys.exit(1)

    # Your code here:
    {{GENERATED_CODE}}

    print(json.dumps(result, ensure_ascii=False))
```

Return ONLY the Python code, no explanations.
```

### validate_code.py — Static Analysis

```python
FORBIDDEN_IMPORTS = {
    "subprocess", "os.system", "shutil.rmtree",
    "eval", "exec", "compile",
    "importlib", "__import__",
    "ctypes", "cffi", "socket",
    "multiprocessing", "threading",
    "signal", "pty", "termios",
}

FORBIDDEN_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\.\w+\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
    r"open\s*\([^)]*['\"][wa]['\"]",   # file write/append
    r"Path\([^)]*\)\.write",
    r"\.unlink\s*\(",
    r"\.rmdir\s*\(",
    r"shutil\.",
]

ALLOWED_NETWORK_DOMAINS = [
    "api.privatbank.ua",
    "api.openweathermap.org",
    "api.duckduckgo.com",
    "api.github.com",
    "wttr.in",
    # Extensible via security_config.json
]
```

Pipeline:
1. `ast.parse()` — reject if syntax error
2. Walk AST: check all Import/ImportFrom nodes
3. Regex scan for forbidden patterns
4. Verify template structure (has main(), json.dumps, sys.argv)
5. Check no file writes
6. Check URL domains against whitelist
7. Line count <= 200

### Safety Framework (4 Layers)

**Layer 1 — Approval Gate (CRITICAL):**
- Creating ANY new skill = CRITICAL → PIN required
- Owner sees: name, description, what tools it needs, generated code preview
- Owner can: approve, reject, or ask for changes

**Layer 2 — Capability Boundaries (hardcoded constants):**
```python
IMMUTABLE_SKILLS = ["buddy-security", "buddy-meta", "buddy-files"]
MAX_GENERATED_PRIORITY = 40       # below ALL core skills
GENERATED_SKILL_DIR = "skills/buddy-meta/generated/"
MAX_SCRIPT_LINES = 200
MAX_GENERATED_SKILLS = 20
ALLOWED_TOOLS = ["exec", "read"]  # generated skills can ONLY read and exec
```

**Layer 3 — Code Review (validate_code.py):**
- AST-based static analysis (deterministic, fast)
- Forbidden imports, patterns, file writes, unsafe network calls
- Template structure enforcement

**Layer 4 — Reversibility:**
- `skill_registry.py uninstall <name>` → moves to _uninstalled/
- `skill_registry.py reinstall <name>` → restores
- `skill_registry.py list` → shows all with status
- Full audit trail in skill_registry.json

### "Next Session" Limitation — Mitigation

1. **Inline execution (immediate):** After creation, `create_skill.py` returns the script path. LLM calls `exec python <path> <args>` directly — works NOW, no need to wait for session restart.
2. **Full skill integration:** On next session, OpenClaw discovers the new SKILL.md in `generated/` and adds it to the skill snapshot. LLM sees it in `<available_skills>` and can use it naturally.
3. **Session restart hint:** Bot suggests: "Навик створено. Працює зараз через пряме виконання. Для повної інтеграції почніть нову сесію."

### skill_registry.json Format
```json
{
  "version": 1,
  "generated_skills": [
    {
      "id": "gen_001",
      "name": "buddy-currency",
      "description": "Check UAH exchange rates from PrivatBank API",
      "purpose": "User asked for currency rates on 2026-03-29",
      "priority": 35,
      "created_at": "2026-03-29T15:00:00",
      "model_used": "minimax/MiniMax-M1-80k",
      "complexity": "light",
      "files": ["SKILL.md", "currency.py"],
      "path": "skills/buddy-meta/generated/buddy-currency/",
      "status": "active",
      "validation_result": {"valid": true, "warnings": []},
      "approval_pin_used": true,
      "sessions_used": 0,
      "last_used": null
    }
  ],
  "config": {
    "max_skills": 20,
    "max_priority": 40,
    "heavy_model": "minimax/MiniMax-M1-80k",
    "fallback_model": "deepseek/deepseek-chat-v3.2"
  }
}
```

### SKILL.md for buddy-meta

```yaml
---
name: buddy-meta
description: "Self-extending agent: creates new skills when current capabilities are insufficient. Uses MiniMax M2.7 for complex code generation. ALWAYS requires PIN (CRITICAL level)."
trigger:
  - on_intent: create_tool, create_skill, extend_capability, new_function
  - on_keyword: створи навик, новий інструмент, не вмію, потрібен тул, create tool, extend
priority: 30
tools:
  - exec
  - read
  - write
---

## When to Trigger

If the user asks you to do something and you recognize that NO existing skill can handle it:
1. Tell the user: "Для цього мені потрібен новий навик. Створити?"
2. If user agrees, call create_skill.py with the requirements
3. ALWAYS requires CRITICAL security level (PIN)

## Workflow

1. Describe the need: `python create_skill.py --action create --need "WHAT user needs" --context "original user message"`
2. MiniMax M2.7 handles EVERYTHING: plans architecture, writes code, self-reviews
3. create_skill.py validates and saves automatically
4. Execute immediately: `python <generated_script_path> <args>`
5. Tell user: result + "Full skill integration in next session"

IMPORTANT: You (Gemini Flash) do NOT write code. You ONLY describe what is needed. MiniMax does the engineering.

## Managing Generated Skills
- List: `python skill_registry.py list`
- Uninstall: `python skill_registry.py uninstall "name"` (MEDIUM)
- Reinstall: `python skill_registry.py reinstall "name"` (MEDIUM)

## SAFETY RULES (NON-NEGOTIABLE)
- NEVER create a skill that modifies buddy-security, buddy-meta, or buddy-files
- NEVER set priority above 40 for generated skills
- NEVER bypass validate_code.py checks
- NEVER save code that fails validation
- ALWAYS require PIN for skill creation
- ALWAYS show the user what the skill does before requesting PIN
```

### Security Config Updates

Add to `security_config.json`:
```json
"meta_skill_rules": {
  "create_skill": "CRITICAL",
  "uninstall_skill": "MEDIUM",
  "reinstall_skill": "MEDIUM",
  "list_skills": "SAFE",
  "max_generated_skills": 20,
  "max_script_lines": 200,
  "max_generated_priority": 40,
  "immutable_skills": ["buddy-security", "buddy-meta", "buddy-files"],
  "heavy_model": "minimax/MiniMax-M1-80k",
  "fallback_model": "deepseek/deepseek-chat-v3.2",
  "forbidden_imports": [
    "subprocess", "os.system", "shutil.rmtree", "eval", "exec",
    "compile", "importlib", "__import__", "ctypes", "cffi",
    "socket", "multiprocessing", "threading", "signal", "pty"
  ],
  "allowed_network_domains": [
    "api.privatbank.ua", "api.openweathermap.org",
    "api.duckduckgo.com", "api.github.com", "wttr.in"
  ]
}
```

Update `buddy-sandbox.yaml`:
```yaml
network:
  allow:
    # Add for generated skills
    - api.privatbank.ua
    - api.openweathermap.org
    - wttr.in

filesystem:
  allow:
    write:
      - "~/openclaw/skills/buddy-meta/generated/**"
```

### Phase 4 Testing Checklist
- [ ] "Мені потрібен курс валют" → bot proposes new skill → CRITICAL PIN → created
- [ ] validate_code.py rejects code with `subprocess` import
- [ ] validate_code.py rejects code with file writes
- [ ] Simple skill (light) generated by Gemini Flash inline
- [ ] Complex skill (heavy) routed to MiniMax M2.7 via generate_with_model.py
- [ ] Generated skill works immediately via inline exec
- [ ] Generated skill auto-discovered in next session
- [ ] skill_registry.json correctly tracks all metadata
- [ ] Owner can list/uninstall/reinstall generated skills
- [ ] Max 20 skills enforced
- [ ] Generated skill priority capped at 40
- [ ] Attempt to create skill modifying buddy-security → rejected

---

## Phase 5: Agent Builds Its Own Skills (3-5 days)

**This phase is different.** Instead of us writing code, we ask the agent (via Telegram) to create the needed skills using buddy-meta.

### Skills the Agent Should Create

**5.1 buddy-search** (search router)
```
Owner: "Створи навик для пошуку — щоб розуміти коли шукати в пам'яті, коли у файлах, коли в інтернеті"
→ Agent creates: search_router.py via buddy-meta
→ PIN approval
→ Test: "що я казав про проект?" → memory search
```

**5.2 buddy-dev tools** (scaffold + deploy)
```
Owner: "Створи навик для створення проектів з шаблонів та деплою на Vercel"
→ Agent creates: scaffold_project.py, deploy helper
→ PIN approval
→ Test: "Створи проект Next.js" → scaffold
```

**5.3 buddy-business** (orders, inventory)
```
Owner: "Створи навик для бізнесу — клієнти питають наявність товару, роблять замовлення,
        постачальник отримує сповіщення, вечірній звіт"
→ Agent creates: inventory.py, order_manager.py, client_manager.py, daily_report.py
→ Multiple PIN approvals (one per script)
→ Test full order pipeline
```

**Note:** Complex skills like buddy-business will likely require multiple iterations:
1. Agent creates first version
2. Owner tests, finds issues
3. Owner asks agent to fix/improve → agent creates updated version
4. Iterative refinement

**Our role in Phase 5:**
- Guide the agent with clear requirements
- Approve (PIN) each generated skill
- Test in Telegram
- Ask for fixes/improvements
- Provide data files (inventory.json, suppliers.json) manually since agent can't write data files

### Data Files (Manual Setup)

Since generated skills are read-only (can't write files for safety), we create data files manually:

```
skills/buddy-meta/generated/buddy-business/data/
+-- inventory.json      # we populate with products
+-- orders.json         # starts empty: {"orders": []}
+-- clients.json        # starts empty: {"clients": []}
+-- suppliers.json      # we populate with supplier contacts
```

**Exception:** order_manager.py WILL need write access to orders.json. This is a special case:
- Generated skills normally can't write files
- For buddy-business, we add an explicit exception in security_config.json:
  ```json
  "business_data_write_paths": [
    "skills/buddy-meta/generated/buddy-business/data/orders.json",
    "skills/buddy-meta/generated/buddy-business/data/clients.json"
  ]
  ```
- validate_code.py allows writes ONLY to these specific paths
- This exception requires CRITICAL approval (PIN) when first set up

---

## Phase 6: Multi-User Support (3-4 days)

### Architecture
- Same bot, two modes: Owner (full) vs Client (business-only)
- `user_router.py` in buddy-security classifies user by telegram_id
- Client sessions: only buddy-business loaded, no MEMORY.md

### New File: `skills/buddy-security/user_router.py`
```bash
python user_router.py <telegram_id>
→ {"user_type": "owner|client|unknown|blocked", "permissions": [...]}
```

### Permission Model
| Role | Access |
|------|--------|
| Owner | Everything |
| Client | Product queries, place orders, own order status |
| Unknown | Greeting, auto-register on product query |
| Blocked | Nothing |

### Session Isolation
- Client: buddy-business ONLY, formal "Ви", no MEMORY.md, no file/dev access
- Owner: all skills, informal "ти", full memory access

### security_config.json additions
```json
"multi_user": {
  "enabled": true,
  "auto_register_clients": true,
  "client_greeting": "Вітаю! Я бот для замовлень. Напишіть назву товару, щоб дізнатися про наявність.",
  "blocked_message": "Вас заблоковано. Зверніться до адміністратора."
}
```

---

## Phase 7+: Future Roadmap (all local until Railway needed)

| Feature | Built By |
|---------|----------|
| Railway 24/7 deployment | Us (when needed) |
| Google Sheets for inventory | Agent via buddy-meta |
| Viber gateway for clients | Agent via buddy-meta + us (config) |
| Web dashboard (Next.js on Vercel) | Us (separate project) |
| Advanced voice (real-time calls) | Us |
| Payment integration (Mono/Privat) | Agent via buddy-meta |

---

## Updated Budget (local phase)

| Item | Cost ($) |
|------|----------|
| Gemini 2.0 Flash (dispatcher) | 1-3/mo |
| MiniMax M2.7 (code gen, occasional) | 0-3/mo |
| STT/TTS | 0 |
| Telegram/Gmail/DuckDuckGo | 0 |
| **Total** | **1-6/mo** |

---

## Key Decisions

| # | Decision | Why |
|---|----------|-----|
| 12 | Gemini Flash = dispatcher (WHAT), MiniMax M2.7 = full engineer (HOW) | Flash only describes the need; MiniMax plans, designs, writes, self-reviews ALL code |
| 13 | buddy-meta is Phase 4 (FIRST after core) | Agent builds everything else itself |
| 14 | generate_with_model.py calls OpenRouter directly | No LLM layer overhead; MiniMax gets full context via direct HTTP |
| 21 | MiniMax self-correction loop (up to 3 attempts) | MiniMax treats errors as feedback, iterates until code passes validation |
| 15 | Generated skills in buddy-meta/generated/ | Isolation from core skills |
| 16 | Max priority 40 for generated skills | Core skills always take precedence |
| 17 | Static analysis (AST) for validation | Deterministic, fast, no sandbox needed |
| 18 | Inline exec for current-session use | Bypasses OpenClaw skill discovery limitation |
| 19 | Business data write exception (explicit paths) | Safety trade-off for functional business module |
| 20 | Phase 5 skills built BY the agent | Proves self-extension works; agent learns by doing |

---

## Git & Repository

Create public GitHub repo. Ensure `.gitignore` excludes all sensitive data:

```gitignore
# Secrets
.env
.env.*
*.key
*.pem
*secret*
*credential*

# OpenClaw runtime
data/audit.jsonl
data/temp/
data/pin_lockout.json

# Business data (contains client info)
skills/buddy-meta/generated/*/data/

# Python
__pycache__/
*.pyc
*.pyo

# Whisper models (too large)
*.bin
*.pt

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

Commit and push all code. Everything except `.env` and runtime data is safe to publish.

---

## Verification Plan

| Phase | Test |
|-------|------|
| 4 | "Курс валют" → PIN → skill created → inline exec works → next session auto-discovers |
| 4 | Forbidden code (subprocess) → rejected by validate_code.py |
| 4 | MiniMax generates complex skill correctly |
| 5 | Agent creates buddy-search, buddy-dev, buddy-business via buddy-meta |
| 5 | Full order pipeline: client inquiry → order → supplier notification → daily report |
| 6 | Second Telegram account as client → restricted to business only |
