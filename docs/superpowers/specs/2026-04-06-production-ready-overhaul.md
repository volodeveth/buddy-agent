# Production-Ready Overhaul — Buddy Agent

**Date:** 2026-04-06
**Status:** Draft
**Scope:** Full project cleanup, bug fixes, missing implementations, tests, CI, documentation reconciliation

---

## Table of Contents

1. [Overview](#1-overview)
2. [Critical Bug Fixes](#2-critical-bug-fixes)
3. [LLM Migration: Gemini Flash -> DeepSeek V3.2](#3-llm-migration)
4. [Repository Cleanup](#4-repository-cleanup)
5. [Shared Utilities Module](#5-shared-utilities-module)
6. [Type Hints for All Files](#6-type-hints)
7. [Implement buddy-search](#7-buddy-search)
8. [Implement buddy-dev](#8-buddy-dev)
9. [HEARTBEAT.md Implementation](#9-heartbeat)
10. [Unit & Integration Tests](#10-tests)
11. [Pre-commit Hooks & CI](#11-ci)
12. [Documentation Reconciliation](#12-docs)
13. [.env.example Template](#13-env-example)
14. [Implementation Order](#14-implementation-order)

---

## 1. Overview

The Buddy Agent project has completed Phases 1-3 and is actively working on Phase 4 (buddy-meta). This overhaul brings the entire codebase to production-ready quality without changing core architecture.

**Key decisions:**
- LLM: DeepSeek V3.2 via OpenRouter (replacing Gemini Flash + MiniMax M2.7 dual-LLM)
- All documentation aligned to single-LLM architecture
- max_script_lines stays at 800 (practical value, specs updated to match)

---

## 2. Critical Bug Fixes

### 2.1 PIN Gate Race Condition (`pin_gate.py:53-71`)

**Problem:** `record_failure()` reads lockout file, increments, writes back — not atomic. Two concurrent requests can both read `attempts=2`, both write `attempts=3`, second overwrites first. Lockout can be bypassed.

**Fix:** Use `msvcrt.locking()` (Windows) for file-level locking during read-modify-write cycle. Wrap the entire read→increment→write in a locked block.

```python
import msvcrt

def record_failure():
    config = load_config()
    LOCKOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(LOCKOUT_PATH, "a+", encoding="utf-8") as f:
        # Lock the file for exclusive access
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        try:
            f.seek(0)
            raw = f.read()
            lockout_data = json.loads(raw) if raw.strip() else {"attempts": 0, "lockout_until": None}
            
            lockout_data["attempts"] = lockout_data.get("attempts", 0) + 1
            
            if lockout_data["attempts"] >= config.get("max_pin_attempts", 3):
                lockout_minutes = config.get("lockout_minutes", 15)
                lockout_until = datetime.now() + timedelta(minutes=lockout_minutes)
                lockout_data["lockout_until"] = lockout_until.isoformat()
                lockout_data["attempts"] = 0
            
            f.seek(0)
            f.truncate()
            json.dump(lockout_data, f)
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    
    return lockout_data
```

### 2.2 PIN Gate `.seconds` Bug (`pin_gate.py:34`)

**Problem:** `.seconds` only returns seconds within the current day portion, not total seconds. For lockouts > 1 hour, shows wrong remaining time.

**Fix:** Replace `.seconds // 60` with `int((lockout_until - datetime.now()).total_seconds()) // 60`.

### 2.3 Voice Utils Duration Bug (`voice_utils.py:51-52`)

**Problem:** Line 51 `container.duration / av.time_base` is incorrect. Line 53 is the correct calculation.

**Fix:** Remove lines 51-52 (dead code). Keep only line 53.

### 2.4 Create Skill Auto-Fix Fragility (`create_skill.py:70-110`)

**Problem:** `_try_fix_syntax()` has two fragile fixes:
- Fix 1 (line 88-96): Hardcoded replacement for "actions" dict — too specific
- Fix 2 (line 98-108): Replaces bad line with `pass` — hides real errors

**Fix:** Replace with a more robust approach:
1. Remove Fix 1 (hardcoded replacement)
2. Make Fix 2 smarter: only replace if line is inside a function body AND is not a return/assignment
3. Add post-fix validation: after fixing, run `validate_code.validate()` to ensure the fix didn't break logic
4. Log which lines were auto-fixed for debugging

### 2.5 Scheduler Monthly Drift (`scheduler.py`)

**Problem:** `"monthly"` recurring reminders use hardcoded 30 days.

**Fix:** Use `calendar.monthrange()` to get actual days in the current month.

---

## 3. LLM Migration: Gemini Flash -> DeepSeek V3.2

### Files to update:

| File | Change |
|------|--------|
| `README.md` | Replace dual-LLM architecture with single DeepSeek V3.2 |
| `CLAUDE.md` | Already correct (says DeepSeek V3.2) |
| `templates/IDENTITY.md` | Already correct (says DeepSeek V3.2) |
| `create_skill.py:3` | Update docstring: "Receives a need, delegates to DeepSeek V3.2" |
| `generate_with_model.py:2-4` | Update docstring: "Call DeepSeek V3.2 via OpenRouter" |
| `generate_with_model.py:241` | Change `heavy_model` default to `"deepseek/deepseek-chat-v3.2"` |
| `generate_with_model.py:242` | Change `fallback_model` to `"deepseek/deepseek-chat"` (older DeepSeek as fallback) |
| `security_config.json` | Update `meta_skill_rules.heavy_model` and `fallback_model` |
| `docs/superpowers/specs/2026-03-29-buddy-agent-v2.md` | Add note at top: "UPDATE 2026-04-06: Switched to single DeepSeek V3.2" |

### Architecture change:
- **Before:** Gemini Flash (dispatcher) + MiniMax M2.7 (engineer) via OpenRouter
- **After:** DeepSeek V3.2 (single LLM for both dispatch and code generation) via OpenRouter
- OpenClaw still handles dispatch; DeepSeek V3.2 is the brain for both conversation and buddy-meta code generation

---

## 4. Repository Cleanup

### Delete from root (25+ junk files):

```
000.txt, 0000.txt, 00000.txt, 000000.txt, 0000000.txt, 00000000.txt, 000000000.txt
lin.txt, lin2.txt, lin23.txt, lin234.txt, lin2345.txt, lin23456.txt,
lin234567.txt, lin2345678.txt, lin23456789.txt, lin2345678910.txt, lin2345678911.txt
fix_request_json.py
test_fix_json.py, test_fix_json2.py, test_fix_json3.py, test_fix_json4.py, test_fix_json5.py
```

### Keep:
- `linkedin-posts.txt` — explicitly whitelisted in .gitignore, user content

### Update .gitignore:
- Add patterns for debug iteration files: `fix_*.py`, `test_fix_*.py`
- Keep `*.txt` exclusion (already present)

---

## 5. Shared Utilities Module

**Problem:** Environment loading duplicated in `send_email.py`, `send_telegram.py`, `generate_with_model.py`. Each has its own `.env` loading logic with hardcoded paths.

**Solution:** Create `skills/buddy-utils/env_loader.py`:

```python
"""Shared environment loader for all buddy skills."""
import os
from pathlib import Path

_ENV_CANDIDATES = [
    Path(__file__).parent.parent.parent / ".env",  # project root
    Path.home() / ".openclaw" / "workspace" / ".env",
]

def load_env() -> None:
    """Load .env file if key variables are missing."""
    if os.environ.get("OPENROUTER_API_KEY") and os.environ.get("TELEGRAM_BOT_TOKEN"):
        return
    for env_path in _ENV_CANDIDATES:
        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
            break
```

All skills import from this shared module instead of duplicating.

---

## 6. Type Hints for All Files

Add return type annotations and parameter types to every function in every Python file. Priority order:

1. **Security-critical:** `pin_gate.py`, `audit_log.py`, `file_validator.py`
2. **Core skills:** `send_email.py`, `send_telegram.py`, `contacts_lookup.py`, `scheduler.py`
3. **Voice:** `stt_whisper.py`, `tts_edge.py`, `voice_utils.py`
4. **Meta:** `create_skill.py`, `generate_with_model.py`, `validate_code.py`, `skill_registry.py`
5. **Generated:** `exchange_rates.py`, `find.py`, `dev-helper.py`

Convention: Use `dict[str, Any]` for JSON return types, `str | None` for optional strings. Python 3.12 syntax (no `from __future__`).

---

## 7. Implement buddy-search

**Location:** `skills/buddy-search/search.py`

**SKILL.md already defines routing:**
- Memory: "що я казав про", past conversations, personal facts
- Web: current events, docs, how-to
- Files: file search in whitelist dirs
- Combined: memory -> files -> web

**Implementation:**

```python
# search.py — Smart search router
# Actions: search (auto-detect), memory, web, files
# Input: {"action": "search", "query": "...", "source": "auto|memory|web|files"}
# Output: {"results": [...], "source": "memory|web|files|combined"}
```

Components:
1. **Intent classifier:** keyword-based (already prototyped in `buddy-find/find.py`)
2. **Memory search:** read `memory/` directory, search markdown files
3. **File search:** use `os.walk()` within whitelisted dirs, match filename and content
4. **Web search:** DuckDuckGo API (already in `find.py`)

The generated `buddy-find` skill can serve as starting point — promote and refactor its logic into the core skill.

---

## 8. Implement buddy-dev

**Location:** `skills/buddy-dev/dev.py`

**SKILL.md already defines workflow:**
- Scaffold projects in `D:/Projects/`
- Git operations (add, commit, push)
- Deploy to Vercel/Railway

**Implementation (basic — no deploy yet):**

```python
# dev.py — Development workflow helper
# Actions: scaffold, git_status, git_commit, git_push, deps
# Input: {"action": "scaffold", "name": "my-app", "type": "nextjs|python|node"}
# Output: {"status": "created", "path": "D:/Projects/my-app", "files": [...]}
```

Components:
1. **Scaffold:** create project directory with template (package.json / requirements.txt / etc.)
2. **Git status:** run `git status`, `git log --oneline -5`
3. **Git commit:** `git add .` + `git commit -m "message"`
4. **Git push:** `git push` (MEDIUM security)
5. **Dependencies:** list from package.json / requirements.txt

Deploy deferred to Phase 5 (CRITICAL security, needs more design).

---

## 9. HEARTBEAT.md Implementation

**Current:** placeholder "HEARTBEAT_OK"

**New content:**
```markdown
# Heartbeat

Periodic tasks to run when system is idle or on schedule.

## Every 5 minutes
- Check for pending reminders (buddy-scheduler)
- Process reminder queue

## Every 30 minutes
- Memory health check (can read/write memory dir)

## On session start
- Read and apply pending reminders
- Check for updated generated skills
- Verify API connectivity (OpenRouter ping)
```

---

## 10. Unit & Integration Tests

**Location:** `tests/` directory at project root

### Structure:
```
tests/
  __init__.py
  conftest.py           # shared fixtures
  test_pin_gate.py      # security: lockout, race condition, bcrypt
  test_file_validator.py # whitelist, sensitivity, path normalization
  test_audit_log.py     # JSONL append, format
  test_scheduler.py     # add/list/cancel, recurring, monthly calc
  test_contacts.py      # lookup, fuzzy match, add
  test_voice_utils.py   # duration calculation, format conversion
  test_validate_code.py # AST validation, forbidden imports
  test_env_loader.py    # shared env loading
  test_search.py        # search routing (after buddy-search implemented)
  test_dev.py           # dev workflow (after buddy-dev implemented)
```

### Key test cases:

**pin_gate.py:**
- Correct PIN -> approved
- Wrong PIN -> denied, attempts decremented
- 3 wrong PINs -> lockout
- Lockout expiry -> access restored
- Lockout time display (> 1 hour correctness)

**file_validator.py:**
- Path inside whitelist -> SAFE/MEDIUM
- Path outside whitelist -> CRITICAL
- Sensitive file patterns -> CRITICAL
- Path traversal attempt -> blocked
- Symlink handling

**scheduler.py:**
- Add reminder, list, cancel
- Recurring monthly with correct day count
- Past reminder detection

**validate_code.py:**
- Clean code -> valid
- Code with `eval()` -> error
- Code with `subprocess` import -> error
- Code exceeding max lines -> error
- URL domain whitelist check

### Test runner: `pytest` with `pytest-cov`

**requirements-dev.txt:**
```
pytest>=8.0
pytest-cov>=5.0
bcrypt>=4.0
```

---

## 11. Pre-commit Hooks & CI

### Pre-commit config (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: local
    hooks:
      - id: no-secrets
        name: Check for secrets
        entry: python -c "import sys; [sys.exit(1) for f in sys.argv[1:] if any(p in f for p in ['.env', '.key', '.pem', 'secret', 'credential'])]"
        language: system
        types: [file]
      - id: python-syntax
        name: Python syntax check
        entry: python -m py_compile
        language: system
        types: [python]
      - id: run-tests
        name: Run tests
        entry: python -m pytest tests/ -x -q
        language: system
        pass_filenames: false
        stages: [pre-push]
```

### GitHub Actions CI (`.github/workflows/ci.yml`):
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements-dev.txt
      - run: python -m pytest tests/ --cov=skills --cov-report=term-missing
      - run: python -m py_compile skills/buddy-security/pin_gate.py
      # Syntax check all Python files
      - run: |
          for f in $(find skills -name "*.py"); do
            python -m py_compile "$f"
          done
```

---

## 12. Documentation Reconciliation

### Files to update:

| File | Changes |
|------|---------|
| `README.md` | Replace Gemini Flash + MiniMax with DeepSeek V3.2 single-LLM architecture. Update architecture diagram. |
| `CLAUDE.md` | Already says DeepSeek V3.2 — no change needed |
| `2026-03-29-buddy-agent-v2.md` | Add header note: "LLM updated to DeepSeek V3.2 (2026-04-06)" |
| `security_config.json` | Update `max_script_lines` comment, update model references |
| `templates/TOOLS.md` | Verify all tools listed match actual implementations |
| `sync.sh` | Add buddy-utils and buddy-search to sync, update health checks |

### Reconcile max_script_lines:
- **Decision:** Keep 800 (practical, already working)
- Update v2 spec references from 200 to 800
- security_config.json already has 800 — no change

---

## 13. .env.example Template

**Location:** `.env.example` (already whitelisted in .gitignore)

```env
# Buddy Agent Environment Variables
# Copy to .env and fill in real values

# OpenRouter API (required)
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Telegram Bot (required)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_OWNER_ID=your-telegram-id

# Email / SMTP (optional)
SMTP_USER=your-email@gmail.com
SMTP_APP_PASSWORD=your-app-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Security (required)
# Generate with: python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PIN', bcrypt.gensalt()).decode())"
BUDDY_PIN_HASH=$2b$12$your-bcrypt-hash-here
```

---

## 14. Implementation Order

Strict dependency order. Each step builds on previous.

| Step | Task | Depends On | Estimated |
|------|------|------------|-----------|
| 1 | Repository cleanup (delete junk files) | — | 5 min |
| 2 | Create shared env_loader utility | — | 10 min |
| 3 | Fix 5 critical/medium bugs | — | 30 min |
| 4 | Add type hints to all 18 Python files | — | 45 min |
| 5 | Refactor skills to use shared env_loader | Step 2 | 15 min |
| 6 | LLM migration (docs + config + code) | — | 20 min |
| 7 | Implement buddy-search | Steps 2, 4 | 30 min |
| 8 | Implement buddy-dev | Steps 2, 4 | 30 min |
| 9 | HEARTBEAT.md | — | 5 min |
| 10 | .env.example | — | 5 min |
| 11 | Unit tests (all test files) | Steps 3, 7, 8 | 60 min |
| 12 | Pre-commit hooks + CI pipeline | Step 11 | 15 min |
| 13 | Documentation reconciliation | Step 6 | 20 min |
| 14 | Update sync.sh | Steps 7, 8 | 10 min |
| 15 | Final validation run | All | 10 min |

**Total estimated: ~5 hours of implementation work**

---

## Out of Scope

- Railway deployment (Phase 5)
- buddy-business skill (Phase 6)
- Multi-user support (Phase 6)
- Viber integration (future)
- Voice calls (future)
