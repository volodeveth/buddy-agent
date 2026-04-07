# Production-Ready Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Buddy Agent project to production-ready quality: fix all critical bugs, clean repository, add missing skill implementations, type hints, tests, CI, and reconcile all documentation to use DeepSeek V3.2.

**Architecture:** No architectural changes — this is a quality/completeness overhaul. The modular skill system and OpenClaw framework remain unchanged. We add a shared `buddy-utils/env_loader.py` utility, implement two stub skills (`buddy-search`, `buddy-dev`), and wrap everything in tests + CI.

**Tech Stack:** Python 3.12, pytest, pytest-cov, bcrypt, GitHub Actions, pre-commit

---

### Task 1: Repository Cleanup — Delete Junk Files

**Files:**
- Delete: `000.txt`, `0000.txt`, `00000.txt`, `000000.txt`, `0000000.txt`, `00000000.txt`, `000000000.txt`
- Delete: `lin.txt`, `lin2.txt`, `lin23.txt`, `lin234.txt`, `lin2345.txt`, `lin23456.txt`, `lin234567.txt`, `lin2345678.txt`, `lin23456789.txt`, `lin2345678910.txt`, `lin2345678911.txt`
- Delete: `fix_request_json.py`, `test_fix_json.py`, `test_fix_json2.py`, `test_fix_json3.py`, `test_fix_json4.py`, `test_fix_json5.py`
- Modify: `.gitignore`

- [ ] **Step 1: Delete all junk files**

```bash
cd "D:/Myapps/buddy agent"
rm -f 000.txt 0000.txt 00000.txt 000000.txt 0000000.txt 00000000.txt 000000000.txt
rm -f lin.txt lin2.txt lin23.txt lin234.txt lin2345.txt lin23456.txt lin234567.txt lin2345678.txt lin23456789.txt lin2345678910.txt lin2345678911.txt
rm -f fix_request_json.py test_fix_json.py test_fix_json2.py test_fix_json3.py test_fix_json4.py test_fix_json5.py
```

- [ ] **Step 2: Update .gitignore to prevent future debug file clutter**

Add after the `# Test/debug files` section in `.gitignore`:

```gitignore
# Test/debug iteration files
fix_*.py
test_fix_*.py
```

- [ ] **Step 3: Create .env.example**

Create file `.env.example`:

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

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: clean up 25+ debug/test files from root, add .env.example"
```

---

### Task 2: Create Shared Env Loader Utility

**Files:**
- Create: `skills/buddy-utils/__init__.py`
- Create: `skills/buddy-utils/env_loader.py`

- [ ] **Step 1: Create buddy-utils directory and __init__.py**

Create `skills/buddy-utils/__init__.py` (empty file).

- [ ] **Step 2: Create env_loader.py**

Create `skills/buddy-utils/env_loader.py`:

```python
#!/usr/bin/env python3
"""Shared environment loader for all buddy skills.

Reads .env file and sets missing environment variables.
Used by skills that need API keys, SMTP credentials, etc.
"""

import os
from pathlib import Path


def _find_env_file() -> Path | None:
    """Search for .env file in known locations."""
    candidates = [
        Path(__file__).parent.parent.parent / ".env",
        Path.home() / ".openclaw" / "workspace" / ".env",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_env() -> None:
    """Load .env file if key environment variables are missing.

    Reads the first .env file found in candidate locations and sets
    any variables not already present in os.environ.
    """
    if os.environ.get("OPENROUTER_API_KEY") and os.environ.get("TELEGRAM_BOT_TOKEN"):
        return

    env_path = _find_env_file()
    if env_path is None:
        return

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val:
                os.environ.setdefault(key, val)
```

- [ ] **Step 3: Commit**

```bash
git add skills/buddy-utils/__init__.py skills/buddy-utils/env_loader.py
git commit -m "feat: add shared env_loader utility for buddy skills"
```

---

### Task 3: Fix Critical Bug — PIN Gate Race Condition

**Files:**
- Modify: `skills/buddy-security/pin_gate.py`

- [ ] **Step 1: Replace record_failure() with file-locked version**

In `skills/buddy-security/pin_gate.py`, replace the entire `record_failure` function (lines 53-73) with:

```python
def record_failure() -> dict:
    """Record a failed PIN attempt; lockout after max_attempts.
    Uses file locking to prevent race conditions."""
    import msvcrt

    config = load_config()
    LOCKOUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(LOCKOUT_PATH, "a+", encoding="utf-8") as f:
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

- [ ] **Step 2: Fix .seconds bug in check_lockout()**

In `skills/buddy-security/pin_gate.py`, line 34, replace:

```python
        remaining = (lockout_until - datetime.now()).seconds // 60
```

with:

```python
        remaining = int((lockout_until - datetime.now()).total_seconds()) // 60
```

- [ ] **Step 3: Commit**

```bash
git add skills/buddy-security/pin_gate.py
git commit -m "fix: PIN gate race condition with file locking + .total_seconds() bug"
```

---

### Task 4: Fix Critical Bug — Voice Utils Duration

**Files:**
- Modify: `skills/buddy-voice-ua/voice_utils.py`

- [ ] **Step 1: Remove dead code lines 51-52**

In `skills/buddy-voice-ua/voice_utils.py`, replace the `get_duration` function (lines 48-55) with:

```python
def get_duration(input_path: str) -> float:
    """Get audio duration in seconds."""
    container = av.open(input_path)
    duration_sec = container.duration / 1_000_000 if container.duration else 0.0
    container.close()
    return round(duration_sec, 1)
```

- [ ] **Step 2: Commit**

```bash
git add skills/buddy-voice-ua/voice_utils.py
git commit -m "fix: remove incorrect duration calculation in voice_utils"
```

---

### Task 5: Fix Create Skill Auto-Fix Logic

**Files:**
- Modify: `skills/buddy-meta/create_skill.py`

- [ ] **Step 1: Replace _try_fix_syntax() with safer version**

In `skills/buddy-meta/create_skill.py`, replace the entire `_try_fix_syntax` function (lines 70-110) with:

```python
def _try_fix_syntax(code: str) -> str:
    """Attempt to auto-fix common syntax errors in generated code.
    Only fixes safe patterns. Returns fixed code or original if no fix found."""
    import ast as _ast
    try:
        _ast.parse(code)
        return code  # Already valid
    except SyntaxError as e:
        err_lineno = e.lineno
        err_msg = str(e.msg)

    lines = code.splitlines()
    if not err_lineno or err_lineno > len(lines):
        return code

    bad_line = lines[err_lineno - 1]
    stripped = bad_line.strip()

    # Fix: only replace with pass if line is inside an indented block,
    # is NOT a return/yield/assignment, and is NOT a control structure
    unsafe_prefixes = ("return ", "yield ", "raise ", "if ", "elif ", "else:", "for ", "while ", "try:", "except", "finally:", "with ", "class ", "def ")
    is_assignment = "=" in stripped and not stripped.startswith("=") and "==" not in stripped.split("=")[0]

    if (bad_line[0:1] == " "
            and stripped
            and not any(stripped.startswith(p) for p in unsafe_prefixes)
            and not is_assignment):
        indent = len(bad_line) - len(bad_line.lstrip())
        lines[err_lineno - 1] = " " * indent + "pass  # auto-fixed: syntax error in original line"
        fixed = "\n".join(lines)
        try:
            _ast.parse(fixed)
            return fixed
        except SyntaxError:
            pass

    return code
```

- [ ] **Step 2: Commit**

```bash
git add skills/buddy-meta/create_skill.py
git commit -m "fix: safer auto-fix logic in create_skill — no hardcoded replacements"
```

---

### Task 6: Fix Scheduler Monthly Drift

**Files:**
- Modify: `skills/buddy-scheduler/scheduler.py`

- [ ] **Step 1: Fix _calc_next_occurrence monthly logic**

In `skills/buddy-scheduler/scheduler.py`, replace lines 118-120:

```python
    elif recurring == "monthly":
        # Simple: add 30 days
        return from_time + timedelta(days=30)
```

with:

```python
    elif recurring == "monthly":
        import calendar
        year = from_time.year + (from_time.month // 12)
        month = (from_time.month % 12) + 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(from_time.day, max_day)
        return from_time.replace(year=year, month=month, day=day)
```

- [ ] **Step 2: Commit**

```bash
git add skills/buddy-scheduler/scheduler.py
git commit -m "fix: scheduler monthly recurrence uses actual month length"
```

---

### Task 7: Add Type Hints to All Security Files

**Files:**
- Modify: `skills/buddy-security/pin_gate.py`
- Modify: `skills/buddy-security/audit_log.py`
- Modify: `skills/buddy-files/file_validator.py`

- [ ] **Step 1: Add type hints to pin_gate.py**

Update function signatures in `skills/buddy-security/pin_gate.py`:

```python
def load_config() -> dict[str, any]:

def check_lockout() -> bool:

def verify_pin(pin_input: str) -> bool:

def main() -> None:
```

- [ ] **Step 2: Add type hints to audit_log.py**

Update function signatures in `skills/buddy-security/audit_log.py`:

```python
def log_action(action: str, target: str, level: str, decision: str,
               pin_used: bool = False, initiated_by: str = "user_message",
               original_message: str = "", execution_result: str = "pending") -> dict[str, str | bool]:

def main() -> None:
```

- [ ] **Step 3: Add type hints to file_validator.py**

Update function signatures in `skills/buddy-files/file_validator.py`:

```python
def load_config() -> dict[str, any]:

def normalize_path(path_str: str) -> str:

def is_in_whitelist(path: str, whitelist: list[str]) -> bool:

def is_blocked(path: str) -> bool:

def is_sensitive(path: str, patterns: list[str]) -> bool:

def validate(path: str, action: str = "read") -> dict[str, str | bool]:

def main() -> None:
```

- [ ] **Step 4: Commit**

```bash
git add skills/buddy-security/pin_gate.py skills/buddy-security/audit_log.py skills/buddy-files/file_validator.py
git commit -m "chore: add type hints to security and file validator modules"
```

---

### Task 8: Add Type Hints to Comms & Scheduler

**Files:**
- Modify: `skills/buddy-comms/contacts_lookup.py`
- Modify: `skills/buddy-comms/send_email.py`
- Modify: `skills/buddy-comms/send_telegram.py`
- Modify: `skills/buddy-scheduler/scheduler.py`

- [ ] **Step 1: Add type hints to contacts_lookup.py**

```python
def load_contacts() -> list[dict[str, str]]:
def save_contacts(contacts: list[dict[str, str]]) -> None:
def _normalize_ukrainian(text: str) -> str:
def search(query: str) -> list[dict[str, str]]:
def add_contact(name: str, email: str = "", role: str = "",
                telegram: str = "", viber: str = "", notes: str = "") -> dict[str, str | dict]:
def main() -> None:
```

- [ ] **Step 2: Add type hints to send_email.py**

```python
def send_via_smtp(to: str, subject: str, body: str,
                  from_name: str = "Buddy Agent",
                  cc: str = "", bcc: str = "",
                  attachment: str = "") -> dict[str, str]:
def main() -> None:
```

- [ ] **Step 3: Add type hints to send_telegram.py**

```python
def _load_bot_token() -> str:
def send_telegram(chat_id: str, text: str) -> dict[str, str]:
def main() -> None:
```

- [ ] **Step 4: Add type hints to scheduler.py**

```python
def load_reminders() -> list[dict]:
def save_reminders(reminders: list[dict]) -> None:
def add_reminder(text: str, trigger_at: str, recurring: str | None = None) -> dict:
def list_reminders(show_all: bool = False) -> dict:
def cancel_reminder(reminder_id: str) -> dict:
def check_due() -> dict:
def _calc_next_occurrence(from_time: datetime, recurring: str) -> datetime:
def main() -> None:
```

- [ ] **Step 5: Commit**

```bash
git add skills/buddy-comms/contacts_lookup.py skills/buddy-comms/send_email.py skills/buddy-comms/send_telegram.py skills/buddy-scheduler/scheduler.py
git commit -m "chore: add type hints to comms and scheduler modules"
```

---

### Task 9: Add Type Hints to Voice & Meta Files

**Files:**
- Modify: `skills/buddy-voice-ua/voice_utils.py`
- Modify: `skills/buddy-voice-ua/stt_whisper.py`
- Modify: `skills/buddy-voice-ua/tts_edge.py`
- Modify: `skills/buddy-meta/create_skill.py`
- Modify: `skills/buddy-meta/generate_with_model.py`
- Modify: `skills/buddy-meta/validate_code.py`
- Modify: `skills/buddy-meta/skill_registry.py`

- [ ] **Step 1: Add type hints to voice files**

`voice_utils.py`:
```python
def convert(input_path: str, output_format: str = "wav") -> str:
def get_duration(input_path: str) -> float:
def main() -> None:
```

`stt_whisper.py`:
```python
def get_model() -> "WhisperModel":
def convert_to_wav(input_path: str) -> str:
def transcribe(audio_path: str) -> dict[str, str | float]:
def main() -> None:
```

`tts_edge.py`:
```python
async def synthesize(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> dict[str, str | int]:
def main() -> None:
```

- [ ] **Step 2: Add type hints to meta files**

`create_skill.py` — key functions:
```python
def _load_registry() -> dict:
def _save_registry(registry: dict) -> None:
def _next_id(registry: dict) -> str:
def _skill_exists(name: str) -> bool:
def _validate_skill_name(name: str) -> str | None:
def _try_fix_syntax(code: str) -> str:
def action_create(need: str, context: str = "") -> dict:
def action_read(name: str) -> dict:
def action_update(name: str, fix_description: str) -> dict:
def action_rollback(name: str) -> dict:
def action_list() -> dict:
def _parse_args() -> dict:
def main() -> None:
def _write_result(result: dict) -> None:
```

`generate_with_model.py`:
```python
def _load_env() -> None:
def _load_meta_config() -> dict:
def _load_system_prompt(need: str, context: str, allowed_domains: list[str], existing_skills: list[str]) -> str:
def _get_existing_skills() -> list[str]:
def call_model(model: str, system_prompt: str, user_prompt: str, max_tokens: int = 25000, temperature: float = 0.3) -> dict:
def _extract_fields_fallback(content: str) -> dict:
def parse_skill_response(content: str) -> dict:
def generate_skill(need: str, context: str = "", correction_errors: list[str] | None = None) -> dict:
```

`skill_registry.py`:
```python
def load_registry() -> dict:
def list_skills() -> None:
def uninstall_skill(name: str) -> None:
def reinstall_skill(name: str) -> None:
def main() -> None:
```

`validate_code.py` — already has some type hints, add return type to `_load_config`:
```python
def _load_config() -> dict:
```

- [ ] **Step 3: Add type hints to generated skill files**

`exchange_rates.py`:
```python
def fetch_exchange_rates() -> list[dict]:
def parse_rates(data: list[dict]) -> dict[str, dict]:
def format_response(rates: dict[str, dict]) -> str:
def main() -> None:
```

`find.py`:
```python
def search_memory(query: str) -> list[dict]:
def search_files(query: str) -> list[dict]:
def search_web(query: str) -> list[dict]:
def search_auto(query: str) -> dict:
def main() -> None:
```

`dev-helper.py`:
```python
def get_scaffold_structure(project_type: str = "nextjs") -> dict:
def read_dependencies(path: Path) -> dict:
def check_git_status(path: Path) -> dict:
def main() -> None:
```

- [ ] **Step 4: Commit**

```bash
git add skills/buddy-voice-ua/ skills/buddy-meta/ skills/buddy-meta/generated/
git commit -m "chore: add type hints to voice, meta, and generated skill modules"
```

---

### Task 10: Refactor Skills to Use Shared Env Loader

**Files:**
- Modify: `skills/buddy-comms/send_email.py`
- Modify: `skills/buddy-comms/send_telegram.py`
- Modify: `skills/buddy-meta/generate_with_model.py`

- [ ] **Step 1: Refactor send_email.py**

Replace lines 17-39 (the inline env loading block) with:

```python
# Load environment
import importlib.util
_loader_path = Path(__file__).parent.parent / "buddy-utils" / "env_loader.py"
if _loader_path.exists():
    _spec = importlib.util.spec_from_file_location("env_loader", _loader_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _mod.load_env()
```

Remove `_ENV_CANDIDATES` and the inline loading loop.

- [ ] **Step 2: Refactor send_telegram.py**

Replace the `_load_bot_token` env-file-reading logic. Keep the openclaw.json fallback but replace the .env loading part (lines 32-43) with the shared loader. Before the function, add:

```python
_loader_path = Path(__file__).parent.parent / "buddy-utils" / "env_loader.py"
if _loader_path.exists():
    import importlib.util
    _spec = importlib.util.spec_from_file_location("env_loader", _loader_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _mod.load_env()
```

Then simplify `_load_bot_token()` to check `os.environ` first, then openclaw.json only.

- [ ] **Step 3: Refactor generate_with_model.py**

Replace `_load_env()` function (lines 35-50) and `_ENV_CANDIDATES` (lines 28-32) with:

```python
def _load_env() -> None:
    """Load .env file if OPENROUTER_API_KEY not set."""
    _loader_path = SKILL_DIR.parent / "buddy-utils" / "env_loader.py"
    if _loader_path.exists():
        import importlib.util
        _spec = importlib.util.spec_from_file_location("env_loader", _loader_path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.load_env()
```

- [ ] **Step 4: Commit**

```bash
git add skills/buddy-comms/send_email.py skills/buddy-comms/send_telegram.py skills/buddy-meta/generate_with_model.py
git commit -m "refactor: use shared env_loader instead of duplicated .env loading"
```

---

### Task 11: LLM Migration — DeepSeek V3.2

**Files:**
- Modify: `README.md`
- Modify: `skills/buddy-meta/create_skill.py:3`
- Modify: `skills/buddy-meta/generate_with_model.py:2-4,241-242`
- Modify: `skills/buddy-security/security_config.json:70-71`
- Modify: `docs/superpowers/specs/2026-03-29-buddy-agent-v2.md` (add header note)

- [ ] **Step 1: Update security_config.json**

In `skills/buddy-security/security_config.json`, replace:

```json
    "heavy_model": "minimax/minimax-m2.7",
    "fallback_model": "deepseek/deepseek-chat-v3.2",
```

with:

```json
    "heavy_model": "deepseek/deepseek-chat-v3.2",
    "fallback_model": "deepseek/deepseek-chat",
```

- [ ] **Step 2: Update generate_with_model.py**

In `skills/buddy-meta/generate_with_model.py`:

Line 2-4, replace docstring:
```python
"""Call DeepSeek V3.2 via OpenRouter for skill engineering.
DeepSeek receives: need description + template + constraints.
DeepSeek returns: complete skill (name, SKILL.md, Python code) as JSON."""
```

Lines 241-242, update defaults:
```python
    model = config.get("heavy_model", "deepseek/deepseek-chat-v3.2")
    fallback = config.get("fallback_model", "deepseek/deepseek-chat")
```

- [ ] **Step 3: Update create_skill.py docstring**

In `skills/buddy-meta/create_skill.py`, line 3, replace:
```python
"""Main orchestrator for self-extending agent.
Receives a need from Gemini Flash, delegates to MiniMax M2.7,
validates, saves, and registers new skills."""
```
with:
```python
"""Main orchestrator for self-extending agent.
Receives a need description, delegates to DeepSeek V3.2 via OpenRouter,
validates, saves, and registers new skills."""
```

- [ ] **Step 4: Update README.md**

Replace the opening paragraph (line 3):
```
A self-extending personal AI assistant built on the [OpenClaw](https://github.com/openclaw) framework. Communicates via Telegram (text + voice in Ukrainian). Uses **DeepSeek V3.2** via OpenRouter as its LLM brain — for both conversation dispatch and autonomous skill generation.
```

Replace the architecture diagram (lines 17-33):
```
User (Telegram) ──> OpenClaw Gateway ──> DeepSeek V3.2 (via OpenRouter)
                                              │
                         ┌────────────────────┴────────────────────┐
                         │                                         │
                  Existing Skills                          Need new skill?
                  (exec Python scripts)                          │
                                                          create_skill.py
                                                                 │
                                                          DeepSeek V3.2
                                                          (code generation)
                                                                 │
                                                          validate_code.py
                                                          (AST safety check)
                                                                 │
                                                          Save + Register
                                                          Execute immediately
```

Replace the Dual LLM table (lines 35-41) with:
```markdown
### LLM

| Model | Provider | Role |
|-------|----------|------|
| **DeepSeek V3.2** | OpenRouter | All tasks: conversation, intent classification, tool dispatch, and code generation for new skills |
```

- [ ] **Step 5: Add note to v2 spec**

At the top of `docs/superpowers/specs/2026-03-29-buddy-agent-v2.md`, after the title, add:
```markdown
> **UPDATE 2026-04-06:** LLM architecture simplified — switched from dual-LLM (Gemini Flash + MiniMax M2.7) to single **DeepSeek V3.2** via OpenRouter for all tasks. max_script_lines confirmed at 800.
```

- [ ] **Step 6: Commit**

```bash
git add README.md skills/buddy-meta/create_skill.py skills/buddy-meta/generate_with_model.py skills/buddy-security/security_config.json docs/superpowers/specs/2026-03-29-buddy-agent-v2.md
git commit -m "feat: migrate LLM from Gemini Flash + MiniMax to DeepSeek V3.2"
```

---

### Task 12: Implement buddy-search

**Files:**
- Create: `skills/buddy-search/search.py`
- Modify: `skills/buddy-search/SKILL.md`

- [ ] **Step 1: Create search.py**

Create `skills/buddy-search/search.py`:

```python
#!/usr/bin/env python3
"""Smart search router — routes queries to memory, files, or web."""

import sys
import io
import json
import os
import pathlib
import urllib.request
import urllib.parse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"

# Load whitelist from security config
_CONFIG_PATH = PROJECT_ROOT / "skills" / "buddy-security" / "security_config.json"


def _load_whitelist() -> list[str]:
    """Load whitelisted directories from security config."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("whitelist_paths", [])
    return ["D:/BuddyWorkspace", "D:/Projects", "D:/Documents"]


def search_memory(query: str) -> list[dict]:
    """Search in memory markdown files."""
    results = []
    if not MEMORY_DIR.exists():
        return results
    query_lower = query.lower()
    for file in MEMORY_DIR.rglob("*.md"):
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
            if query_lower in content.lower():
                # Extract matching line for context
                for line in content.splitlines():
                    if query_lower in line.lower():
                        results.append({
                            "source": "memory",
                            "file": file.name,
                            "match": line.strip()[:200],
                        })
                        break
        except OSError:
            continue
    return results


def search_files(query: str) -> list[dict]:
    """Search filenames and content in whitelisted directories."""
    results = []
    whitelist = _load_whitelist()
    query_lower = query.lower()

    for directory in whitelist:
        dir_path = pathlib.Path(directory)
        if not dir_path.exists():
            continue
        for file in dir_path.rglob("*"):
            if not file.is_file():
                continue
            # Match filename
            if query_lower in file.name.lower():
                results.append({
                    "source": "files",
                    "path": str(file),
                    "name": file.name,
                    "match_type": "filename",
                })
            # Match content (only text files, skip large/binary)
            elif file.suffix in (".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".csv"):
                try:
                    if file.stat().st_size > 1_000_000:  # Skip files > 1MB
                        continue
                    content = file.read_text(encoding="utf-8", errors="ignore")
                    if query_lower in content.lower():
                        for line in content.splitlines():
                            if query_lower in line.lower():
                                results.append({
                                    "source": "files",
                                    "path": str(file),
                                    "name": file.name,
                                    "match_type": "content",
                                    "match": line.strip()[:200],
                                })
                                break
                except OSError:
                    continue
            if len(results) >= 20:
                break
        if len(results) >= 20:
            break
    return results


def search_web(query: str) -> list[dict]:
    """Search the web via DuckDuckGo Instant Answer API."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "BuddyAgent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            results = []
            if data.get("AbstractText"):
                results.append({
                    "source": "web",
                    "title": data["AbstractText"][:200],
                    "url": data.get("AbstractURL", ""),
                })
            for topic in data.get("RelatedTopics", [])[:5]:
                if "Text" in topic:
                    results.append({
                        "source": "web",
                        "title": topic["Text"][:150],
                        "url": topic.get("FirstURL", ""),
                    })
            return results
    except Exception as e:
        return [{"source": "web", "error": str(e)}]


def classify_intent(query: str) -> str:
    """Classify search intent based on keywords."""
    q = query.lower()
    memory_kw = ["пам'ять", "згадати", "раніше", "казав", "було", "memory", "remember"]
    file_kw = ["файл", "документ", "знайди", "file", "folder", "диск", "шлях"]
    web_kw = ["інтернет", "web", "новини", "що таке", "online", "google", "як зробити", "how to"]

    if any(k in q for k in memory_kw):
        return "memory"
    if any(k in q for k in file_kw):
        return "files"
    if any(k in q for k in web_kw):
        return "web"
    return "auto"


def search(query: str, source: str = "auto") -> dict:
    """Main search function with automatic or manual routing."""
    if source == "auto":
        source = classify_intent(query)

    if source == "memory":
        results = search_memory(query)
    elif source == "files":
        results = search_files(query)
    elif source == "web":
        results = search_web(query)
    else:
        # Combined: memory -> files -> web
        results = search_memory(query)
        if not results:
            results = search_files(query)
        if not results:
            results = search_web(query)
        source = "combined"

    return {
        "query": query,
        "source": source,
        "count": len(results),
        "results": results,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: search.py <query> [source: auto|memory|files|web]"}))
        sys.exit(1)

    query = sys.argv[1]
    source = sys.argv[2] if len(sys.argv) > 2 else "auto"

    result = search(query, source)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update SKILL.md to reference the script**

Append to `skills/buddy-search/SKILL.md` after line 20:

```markdown

## Script

`search.py <query> [source: auto|memory|files|web]`

Returns JSON: `{"query": "...", "source": "memory|files|web|combined", "count": N, "results": [...]}`
```

- [ ] **Step 3: Commit**

```bash
git add skills/buddy-search/search.py skills/buddy-search/SKILL.md
git commit -m "feat: implement buddy-search skill — memory/files/web routing"
```

---

### Task 13: Implement buddy-dev

**Files:**
- Create: `skills/buddy-dev/dev.py`

- [ ] **Step 1: Create dev.py**

Create `skills/buddy-dev/dev.py`:

```python
#!/usr/bin/env python3
"""Development workflow helper — scaffold, git, dependencies."""

import sys
import io
import json
import os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent
PROJECTS_DIR = Path("D:/Projects")

SCAFFOLDS: dict[str, dict] = {
    "nextjs": {
        "files": {
            "package.json": '{"name": "{{NAME}}", "private": true, "scripts": {"dev": "next dev", "build": "next build", "start": "next start"}, "dependencies": {"next": "latest", "react": "latest", "react-dom": "latest"}}',
            "tsconfig.json": '{"compilerOptions": {"target": "es5", "lib": ["dom", "esnext"], "strict": true, "jsx": "preserve", "moduleResolution": "bundler"}, "include": ["**/*.ts", "**/*.tsx"], "exclude": ["node_modules"]}',
            "app/layout.tsx": 'export default function RootLayout({ children }: { children: React.ReactNode }) {\n  return <html><body>{children}</body></html>\n}',
            "app/page.tsx": 'export default function Home() {\n  return <h1>Hello World</h1>\n}',
            ".gitignore": "node_modules/\n.next/\n.env\n",
        },
        "commands": ["npm install"],
    },
    "python": {
        "files": {
            "requirements.txt": "",
            "src/__init__.py": "",
            "src/main.py": '#!/usr/bin/env python3\n"""Main entry point."""\n\n\ndef main() -> None:\n    print("Hello World")\n\n\nif __name__ == "__main__":\n    main()\n',
            "tests/__init__.py": "",
            "tests/test_main.py": 'from src.main import main\n\ndef test_main(capsys):\n    main()\n    assert "Hello" in capsys.readouterr().out\n',
            ".gitignore": "__pycache__/\n*.pyc\nvenv/\n.env\ndist/\n",
        },
        "commands": [],
    },
    "node": {
        "files": {
            "package.json": '{"name": "{{NAME}}", "version": "1.0.0", "main": "src/index.js", "scripts": {"start": "node src/index.js", "test": "echo \\"no tests\\" && exit 0"}}',
            "src/index.js": 'console.log("Hello World");\n',
            ".gitignore": "node_modules/\n.env\n",
        },
        "commands": ["npm install"],
    },
}


def action_scaffold(name: str, project_type: str = "python") -> dict:
    """Create a new project from template."""
    if project_type not in SCAFFOLDS:
        return {"status": "error", "message": f"Unknown type: {project_type}. Use: {list(SCAFFOLDS.keys())}"}

    project_dir = PROJECTS_DIR / name
    if project_dir.exists():
        return {"status": "error", "message": f"Directory already exists: {project_dir}"}

    scaffold = SCAFFOLDS[project_type]
    created_files = []

    for rel_path, content in scaffold["files"].items():
        content = content.replace("{{NAME}}", name)
        file_path = project_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        created_files.append(rel_path)

    return {
        "status": "created",
        "name": name,
        "type": project_type,
        "path": str(project_dir),
        "files": created_files,
        "next_steps": scaffold.get("commands", []),
    }


def action_git_status(path: str) -> dict:
    """Check git status of a directory."""
    project_path = Path(path).resolve()
    git_dir = project_path / ".git"

    if not git_dir.exists():
        return {"status": "error", "message": f"Not a git repo: {path}"}

    result = {"is_git_repo": True, "path": str(project_path)}

    # Read current branch
    head = git_dir / "HEAD"
    if head.exists():
        content = head.read_text().strip()
        if content.startswith("ref: refs/heads/"):
            result["branch"] = content[16:]
        else:
            result["branch"] = content[:8] + "... (detached)"

    # Read remotes
    config = git_dir / "config"
    if config.exists():
        remotes = []
        for line in config.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("url = "):
                remotes.append(stripped[6:])
        result["remotes"] = remotes

    return result


def action_deps(path: str) -> dict:
    """List project dependencies."""
    project_path = Path(path).resolve()

    # Check package.json
    pkg = project_path / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = list(data.get("dependencies", {}).keys())
            dev_deps = list(data.get("devDependencies", {}).keys())
            return {
                "type": "node",
                "file": "package.json",
                "dependencies": deps,
                "dev_dependencies": dev_deps,
                "total": len(deps) + len(dev_deps),
            }
        except (json.JSONDecodeError, OSError) as e:
            return {"status": "error", "message": str(e)}

    # Check requirements.txt
    req = project_path / "requirements.txt"
    if req.exists():
        try:
            lines = req.read_text(encoding="utf-8").splitlines()
            deps = [
                line.strip().split("==")[0].split(">=")[0].split("<=")[0]
                for line in lines
                if line.strip() and not line.startswith("#")
            ]
            return {"type": "python", "file": "requirements.txt", "dependencies": deps, "total": len(deps)}
        except OSError as e:
            return {"status": "error", "message": str(e)}

    return {"status": "error", "message": "No package.json or requirements.txt found"}


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: dev.py <action> [args]",
            "actions": {
                "scaffold": "dev.py scaffold <name> [type: python|nextjs|node]",
                "git-status": "dev.py git-status <path>",
                "deps": "dev.py deps <path>",
            }
        }))
        sys.exit(1)

    action = sys.argv[1]

    if action == "scaffold":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        ptype = sys.argv[3] if len(sys.argv) > 3 else "python"
        if not name:
            result = {"status": "error", "message": "Project name required"}
        else:
            result = action_scaffold(name, ptype)
    elif action == "git-status":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        result = action_git_status(path)
    elif action == "deps":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        result = action_deps(path)
    else:
        result = {"status": "error", "message": f"Unknown action: {action}"}

    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add skills/buddy-dev/dev.py
git commit -m "feat: implement buddy-dev skill — scaffold, git-status, deps"
```

---

### Task 14: Update HEARTBEAT.md

**Files:**
- Modify: `templates/HEARTBEAT.md`

- [ ] **Step 1: Replace placeholder with real content**

Replace contents of `templates/HEARTBEAT.md`:

```markdown
# Heartbeat

Periodic health checks and scheduled task processing.

## On Every Heartbeat
1. Check for due reminders: `python skills/buddy-scheduler/scheduler.py check`
2. If any triggered, notify owner via Telegram with reminder text

## On Session Start
1. Run reminder check (same as above)
2. Verify API connectivity: confirm OPENROUTER_API_KEY is set
3. Check generated skills registry for any newly created skills

## Health Indicators
- Memory directory readable: `memory/` exists and contains MEMORY.md
- Audit log writable: `data/audit.jsonl` can be appended to
- Security config valid: `skills/buddy-security/security_config.json` parses as JSON
```

- [ ] **Step 2: Commit**

```bash
git add templates/HEARTBEAT.md
git commit -m "feat: implement HEARTBEAT.md with reminder checks and health indicators"
```

---

### Task 15: Update sync.sh

**Files:**
- Modify: `sync.sh`

- [ ] **Step 1: Add buddy-utils and buddy-search to sync and health checks**

In `sync.sh`, add `buddy-utils` and `buddy-search` to the skill sync section (wherever buddy-* skills are copied). Add syntax checks for the new Python files:

```bash
# Add to health check section:
python -m py_compile "$WORKSPACE/skills/buddy-search/search.py" 2>/dev/null && echo "  ✓ buddy-search/search.py" || { echo "  ✗ buddy-search/search.py"; errors=$((errors+1)); }
python -m py_compile "$WORKSPACE/skills/buddy-dev/dev.py" 2>/dev/null && echo "  ✓ buddy-dev/dev.py" || { echo "  ✗ buddy-dev/dev.py"; errors=$((errors+1)); }
python -m py_compile "$WORKSPACE/skills/buddy-utils/env_loader.py" 2>/dev/null && echo "  ✓ buddy-utils/env_loader.py" || { echo "  ✗ buddy-utils/env_loader.py"; errors=$((errors+1)); }
```

- [ ] **Step 2: Commit**

```bash
git add sync.sh
git commit -m "chore: add new skills to sync.sh health checks"
```

---

### Task 16: Create Test Infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create test directory and requirements**

Create `tests/__init__.py` (empty file).

Create `requirements-dev.txt`:

```
pytest>=8.0
pytest-cov>=5.0
bcrypt>=4.0
```

Create `tests/conftest.py`:

```python
"""Shared test fixtures for Buddy Agent tests."""

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_config(tmp_dir):
    """Create a sample security_config.json."""
    config = {
        "owner_telegram_id": "123456",
        "pin_hash": "$2b$12$test_hash_value",
        "whitelist_paths": [str(tmp_dir / "workspace")],
        "blacklist_commands": ["rm -rf /"],
        "sensitive_file_patterns": ["*.env", "*.key", "*.pem"],
        "max_pin_attempts": 3,
        "lockout_minutes": 15,
        "max_file_size_mb": 100,
        "audit_log_path": "data/audit.jsonl",
        "meta_skill_rules": {
            "max_script_lines": 800,
            "max_generated_priority": 40,
            "forbidden_imports": ["subprocess", "shutil", "ctypes"],
            "allowed_network_domains": ["api.privatbank.ua"],
        }
    }
    config_path = tmp_dir / "security_config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    (tmp_dir / "workspace").mkdir()
    return config_path


@pytest.fixture
def sample_contacts(tmp_dir):
    """Create a sample contacts.json."""
    contacts = {
        "contacts": [
            {
                "name": "Ірина Дорош",
                "nickname": ["Ірина", "Іра"],
                "email": "iryna@example.com",
                "telegram": "123456",
                "viber": "",
                "role": "дружина",
                "notes": "test contact"
            }
        ]
    }
    path = tmp_dir / "contacts.json"
    path.write_text(json.dumps(contacts), encoding="utf-8")
    return path
```

- [ ] **Step 2: Commit**

```bash
git add tests/__init__.py tests/conftest.py requirements-dev.txt
git commit -m "chore: add test infrastructure — pytest, fixtures, requirements-dev"
```

---

### Task 17: Unit Tests — Security Layer

**Files:**
- Create: `tests/test_file_validator.py`
- Create: `tests/test_audit_log.py`

- [ ] **Step 1: Write test_file_validator.py**

Create `tests/test_file_validator.py`:

```python
"""Tests for buddy-files/file_validator.py."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-files"
sys.path.insert(0, str(SKILL_PATH))

import file_validator


@pytest.fixture(autouse=True)
def mock_config(sample_config, tmp_dir):
    """Override config path for all tests."""
    with patch.object(file_validator, "CONFIG_PATH", sample_config):
        yield


class TestNormalizePath:
    def test_forward_slashes(self):
        result = file_validator.normalize_path("D:\\Users\\test")
        assert "\\" not in result

    def test_resolves_relative(self):
        result = file_validator.normalize_path("./test/../test/file.txt")
        assert ".." not in result


class TestIsInWhitelist:
    def test_path_in_whitelist(self, tmp_dir):
        assert file_validator.is_in_whitelist(
            str(tmp_dir / "workspace" / "file.txt"),
            [str(tmp_dir / "workspace")]
        )

    def test_path_outside_whitelist(self, tmp_dir):
        assert not file_validator.is_in_whitelist(
            "C:/Windows/system32/cmd.exe",
            [str(tmp_dir / "workspace")]
        )

    def test_case_insensitive(self, tmp_dir):
        ws = str(tmp_dir / "workspace")
        assert file_validator.is_in_whitelist(ws.upper() + "/file.txt", [ws])


class TestIsBlocked:
    def test_system_dir_blocked(self):
        assert file_validator.is_blocked("C:/Windows/System32/cmd.exe")

    def test_user_dir_not_blocked(self):
        assert not file_validator.is_blocked("D:/Projects/myapp/main.py")


class TestIsSensitive:
    def test_env_file(self):
        assert file_validator.is_sensitive(".env", ["*.env"])

    def test_key_file(self):
        assert file_validator.is_sensitive("server.key", ["*.key"])

    def test_normal_file(self):
        assert not file_validator.is_sensitive("main.py", ["*.env", "*.key"])


class TestValidate:
    def test_whitelisted_read_is_safe(self, tmp_dir):
        result = file_validator.validate(str(tmp_dir / "workspace" / "file.txt"), "read")
        assert result["level"] == "SAFE"
        assert result["allowed"] is True

    def test_whitelisted_write_is_medium(self, tmp_dir):
        result = file_validator.validate(str(tmp_dir / "workspace" / "file.txt"), "write")
        assert result["level"] == "MEDIUM"

    def test_delete_is_always_critical(self, tmp_dir):
        result = file_validator.validate(str(tmp_dir / "workspace" / "file.txt"), "delete")
        assert result["level"] == "CRITICAL"

    def test_sensitive_file_is_critical(self, tmp_dir):
        result = file_validator.validate(str(tmp_dir / "workspace" / ".env"), "read")
        assert result["level"] == "CRITICAL"

    def test_blocked_dir_not_allowed(self):
        result = file_validator.validate("C:/Windows/System32/cmd.exe", "read")
        assert result["allowed"] is False
        assert result["level"] == "BLOCKED"

    def test_outside_whitelist_is_critical(self):
        result = file_validator.validate("C:/Users/secret/data.txt", "read")
        assert result["level"] == "CRITICAL"
```

- [ ] **Step 2: Write test_audit_log.py**

Create `tests/test_audit_log.py`:

```python
"""Tests for buddy-security/audit_log.py."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-security"
sys.path.insert(0, str(SKILL_PATH))

import audit_log


class TestLogAction:
    def test_creates_jsonl_entry(self, tmp_dir):
        log_path = tmp_dir / "audit.jsonl"
        with patch.object(audit_log, "AUDIT_PATH", log_path):
            entry = audit_log.log_action(
                action="file_read",
                target="/test/file.txt",
                level="SAFE",
                decision="approved"
            )

        assert entry["action"] == "file_read"
        assert entry["security_level"] == "SAFE"
        assert "timestamp" in entry

        # Verify file was written
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["action"] == "file_read"

    def test_appends_to_existing_log(self, tmp_dir):
        log_path = tmp_dir / "audit.jsonl"
        with patch.object(audit_log, "AUDIT_PATH", log_path):
            audit_log.log_action("action1", "target1", "SAFE", "approved")
            audit_log.log_action("action2", "target2", "MEDIUM", "confirmed")

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_pin_used_field(self, tmp_dir):
        log_path = tmp_dir / "audit.jsonl"
        with patch.object(audit_log, "AUDIT_PATH", log_path):
            entry = audit_log.log_action(
                action="deploy",
                target="production",
                level="CRITICAL",
                decision="approved",
                pin_used=True
            )
        assert entry["pin_used"] is True

    def test_creates_parent_directory(self, tmp_dir):
        log_path = tmp_dir / "nested" / "dir" / "audit.jsonl"
        with patch.object(audit_log, "AUDIT_PATH", log_path):
            audit_log.log_action("test", "target", "SAFE", "approved")
        assert log_path.exists()
```

- [ ] **Step 3: Run tests**

```bash
cd "D:/Myapps/buddy agent"
python -m pytest tests/test_file_validator.py tests/test_audit_log.py -v
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_file_validator.py tests/test_audit_log.py
git commit -m "test: add unit tests for file_validator and audit_log"
```

---

### Task 18: Unit Tests — Scheduler & Contacts

**Files:**
- Create: `tests/test_scheduler.py`
- Create: `tests/test_contacts.py`

- [ ] **Step 1: Write test_scheduler.py**

Create `tests/test_scheduler.py`:

```python
"""Tests for buddy-scheduler/scheduler.py."""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-scheduler"
sys.path.insert(0, str(SKILL_PATH))

import scheduler


@pytest.fixture(autouse=True)
def tmp_reminders(tmp_dir):
    """Use temp reminders file for all tests."""
    path = tmp_dir / "reminders.json"
    with patch.object(scheduler, "REMINDERS_PATH", path):
        yield path


class TestAddReminder:
    def test_adds_reminder(self):
        result = scheduler.add_reminder("Test reminder", "2026-12-31T10:00:00")
        assert result["status"] == "added"
        assert result["reminder"]["text"] == "Test reminder"
        assert result["reminder"]["status"] == "active"
        assert len(result["reminder"]["id"]) == 8

    def test_adds_recurring(self):
        result = scheduler.add_reminder("Daily standup", "2026-04-07T09:00:00", "daily")
        assert result["reminder"]["recurring"] == "daily"


class TestListReminders:
    def test_empty_list(self):
        result = scheduler.list_reminders()
        assert result["count"] == 0

    def test_lists_active_only(self):
        scheduler.add_reminder("Active", "2026-12-31T10:00:00")
        scheduler.add_reminder("Cancel me", "2026-12-31T11:00:00")
        reminders = scheduler.load_reminders()
        reminders[1]["status"] = "cancelled"
        scheduler.save_reminders(reminders)

        result = scheduler.list_reminders()
        assert result["count"] == 1

    def test_lists_all(self):
        scheduler.add_reminder("Active", "2026-12-31T10:00:00")
        scheduler.add_reminder("Cancel me", "2026-12-31T11:00:00")
        reminders = scheduler.load_reminders()
        reminders[1]["status"] = "cancelled"
        scheduler.save_reminders(reminders)

        result = scheduler.list_reminders(show_all=True)
        assert result["count"] == 2


class TestCancelReminder:
    def test_cancel_existing(self):
        add_result = scheduler.add_reminder("Cancel me", "2026-12-31T10:00:00")
        rid = add_result["reminder"]["id"]

        result = scheduler.cancel_reminder(rid)
        assert result["status"] == "cancelled"

    def test_cancel_nonexistent(self):
        result = scheduler.cancel_reminder("nonexist")
        assert result["status"] == "not_found"


class TestCheckDue:
    def test_triggers_past_reminder(self):
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        scheduler.add_reminder("Overdue", past)

        result = scheduler.check_due()
        assert result["count"] == 1
        assert result["triggered"][0]["text"] == "Overdue"

    def test_does_not_trigger_future(self):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        scheduler.add_reminder("Future", future)

        result = scheduler.check_due()
        assert result["count"] == 0

    def test_recurring_reschedules(self):
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        scheduler.add_reminder("Daily", past, "daily")

        scheduler.check_due()

        reminders = scheduler.load_reminders()
        # Should still be active (rescheduled, not completed)
        assert reminders[0]["status"] == "active"
        new_trigger = datetime.fromisoformat(reminders[0]["trigger_at"])
        assert new_trigger > datetime.now()


class TestCalcNextOccurrence:
    def test_daily(self):
        base = datetime(2026, 4, 6, 9, 0)
        result = scheduler._calc_next_occurrence(base, "daily")
        assert result == datetime(2026, 4, 7, 9, 0)

    def test_weekly(self):
        base = datetime(2026, 4, 6, 9, 0)
        result = scheduler._calc_next_occurrence(base, "weekly")
        assert result == datetime(2026, 4, 13, 9, 0)

    def test_monthly_30_day_month(self):
        base = datetime(2026, 4, 15, 9, 0)
        result = scheduler._calc_next_occurrence(base, "monthly")
        assert result.month == 5
        assert result.day == 15

    def test_monthly_end_of_month(self):
        # Jan 31 -> Feb should be Feb 28
        base = datetime(2026, 1, 31, 9, 0)
        result = scheduler._calc_next_occurrence(base, "monthly")
        assert result.month == 2
        assert result.day == 28

    def test_weekdays_skips_weekend(self):
        # Friday -> should skip to Monday
        friday = datetime(2026, 4, 10, 9, 0)  # April 10, 2026 is Friday
        result = scheduler._calc_next_occurrence(friday, "weekdays")
        assert result.weekday() < 5  # Monday-Friday
```

- [ ] **Step 2: Write test_contacts.py**

Create `tests/test_contacts.py`:

```python
"""Tests for buddy-comms/contacts_lookup.py."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-comms"
sys.path.insert(0, str(SKILL_PATH))

import contacts_lookup


@pytest.fixture(autouse=True)
def tmp_contacts(sample_contacts):
    """Use temp contacts file for all tests."""
    with patch.object(contacts_lookup, "CONTACTS_PATH", sample_contacts):
        yield


class TestSearch:
    def test_exact_name(self):
        results = contacts_lookup.search("Ірина Дорош")
        assert len(results) == 1
        assert results[0]["name"] == "Ірина Дорош"

    def test_nickname(self):
        results = contacts_lookup.search("Іра")
        assert len(results) == 1

    def test_role(self):
        results = contacts_lookup.search("дружина")
        assert len(results) == 1

    def test_not_found(self):
        results = contacts_lookup.search("Невідомий")
        assert len(results) == 0

    def test_case_insensitive(self):
        results = contacts_lookup.search("ірина")
        assert len(results) == 1

    def test_ukrainian_stem_match(self):
        # "Ірині" (dative case) should match "Ірина"
        results = contacts_lookup.search("Ірині")
        assert len(results) == 1


class TestNormalizeUkrainian:
    def test_strips_suffix(self):
        stem = contacts_lookup._normalize_ukrainian("Ірині")
        assert len(stem) >= 3

    def test_preserves_short_words(self):
        # Words shorter than 3 chars after stripping should keep original
        result = contacts_lookup._normalize_ukrainian("ді")
        assert result == "ді"


class TestAddContact:
    def test_add_new(self):
        result = contacts_lookup.add_contact("Олег Тест", "oleg@test.com", "колега")
        assert result["status"] == "added"
        assert result["contact"]["name"] == "Олег Тест"

    def test_add_duplicate(self):
        result = contacts_lookup.add_contact("Ірина Дорош", "new@test.com")
        assert result["status"] == "exists"
```

- [ ] **Step 3: Run tests**

```bash
cd "D:/Myapps/buddy agent"
python -m pytest tests/test_scheduler.py tests/test_contacts.py -v
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_scheduler.py tests/test_contacts.py
git commit -m "test: add unit tests for scheduler and contacts"
```

---

### Task 19: Unit Tests — Validate Code & Voice Utils

**Files:**
- Create: `tests/test_validate_code.py`
- Create: `tests/test_voice_utils.py`
- Create: `tests/test_env_loader.py`

- [ ] **Step 1: Write test_validate_code.py**

Create `tests/test_validate_code.py`:

```python
"""Tests for buddy-meta/validate_code.py."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-meta"
sys.path.insert(0, str(SKILL_PATH))

import validate_code


VALID_SKILL = '''#!/usr/bin/env python3
"""Test skill."""
import sys
import json

def main():
    result = {"status": "ok"}
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''

FORBIDDEN_IMPORT_SKILL = '''#!/usr/bin/env python3
import sys
import json
import subprocess

def main():
    print(json.dumps({"status": "ok"}))

if __name__ == "__main__":
    main()
'''

EVAL_SKILL = '''#!/usr/bin/env python3
import sys
import json

def main():
    result = eval("1+1")
    print(json.dumps({"result": result}))

if __name__ == "__main__":
    main()
'''

NO_MAIN_SKILL = '''#!/usr/bin/env python3
import sys
import json
print(json.dumps({"status": "ok"}))
'''


class TestValidate:
    def test_valid_skill_passes(self):
        result = validate_code.validate(VALID_SKILL)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_forbidden_import_fails(self):
        result = validate_code.validate(FORBIDDEN_IMPORT_SKILL)
        assert result["valid"] is False
        assert any("subprocess" in e for e in result["errors"])

    def test_eval_fails(self):
        result = validate_code.validate(EVAL_SKILL)
        assert result["valid"] is False
        assert any("eval" in e for e in result["errors"])

    def test_no_main_fails(self):
        result = validate_code.validate(NO_MAIN_SKILL)
        assert result["valid"] is False
        assert any("main()" in e for e in result["errors"])

    def test_syntax_error(self):
        result = validate_code.validate("def broken(:\n  pass")
        assert result["valid"] is False
        assert any("Syntax error" in e for e in result["errors"])

    def test_too_many_lines(self):
        long_code = VALID_SKILL + "\n# padding\n" * 900
        result = validate_code.validate(long_code)
        assert result["valid"] is False
        assert any("lines" in e and "max" in e for e in result["errors"])

    def test_stats_returned(self):
        result = validate_code.validate(VALID_SKILL)
        assert "stats" in result
        assert result["stats"]["functions"] >= 1
        assert result["stats"]["lines"] > 0


class TestAllowedDomains:
    def test_whitelisted_domain_no_warning(self):
        code = VALID_SKILL.replace(
            'result = {"status": "ok"}',
            'url = "https://api.privatbank.ua/rates"'
        )
        result = validate_code.validate(code, allowed_domains=["api.privatbank.ua"])
        domain_warnings = [w for w in result["warnings"] if "domain" in w.lower()]
        assert len(domain_warnings) == 0

    def test_unknown_domain_warning(self):
        code = VALID_SKILL.replace(
            'result = {"status": "ok"}',
            'url = "https://evil.example.com/steal"'
        )
        result = validate_code.validate(code, allowed_domains=["api.privatbank.ua"])
        domain_warnings = [w for w in result["warnings"] if "domain" in w.lower()]
        assert len(domain_warnings) > 0
```

- [ ] **Step 2: Write test_env_loader.py**

Create `tests/test_env_loader.py`:

```python
"""Tests for buddy-utils/env_loader.py."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-utils"
sys.path.insert(0, str(SKILL_PATH))

import env_loader


class TestLoadEnv:
    def test_loads_from_env_file(self, tmp_dir):
        env_file = tmp_dir / ".env"
        env_file.write_text("TEST_VAR_XYZ=hello123\n")

        with patch.object(env_loader, "_find_env_file", return_value=env_file):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TEST_VAR_XYZ", None)
                os.environ.pop("OPENROUTER_API_KEY", None)
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
                env_loader.load_env()
                assert os.environ.get("TEST_VAR_XYZ") == "hello123"

    def test_skips_if_keys_present(self, tmp_dir):
        env_file = tmp_dir / ".env"
        env_file.write_text("NEW_VAR=should_not_load\n")

        with patch.object(env_loader, "_find_env_file", return_value=env_file):
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "x", "TELEGRAM_BOT_TOKEN": "y"}):
                env_loader.load_env()
                assert os.environ.get("NEW_VAR") is None

    def test_skips_comments_and_empty_lines(self, tmp_dir):
        env_file = tmp_dir / ".env"
        env_file.write_text("# comment\n\nVALID_KEY=value\n")

        with patch.object(env_loader, "_find_env_file", return_value=env_file):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("OPENROUTER_API_KEY", None)
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
                os.environ.pop("VALID_KEY", None)
                env_loader.load_env()
                assert os.environ.get("VALID_KEY") == "value"

    def test_does_not_overwrite_existing(self, tmp_dir):
        env_file = tmp_dir / ".env"
        env_file.write_text("EXISTING=new_value\n")

        with patch.object(env_loader, "_find_env_file", return_value=env_file):
            with patch.dict(os.environ, {"EXISTING": "old_value"}, clear=False):
                os.environ.pop("OPENROUTER_API_KEY", None)
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
                env_loader.load_env()
                assert os.environ.get("EXISTING") == "old_value"
```

- [ ] **Step 3: Run all tests**

```bash
cd "D:/Myapps/buddy agent"
python -m pytest tests/ -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_validate_code.py tests/test_env_loader.py
git commit -m "test: add unit tests for validate_code and env_loader"
```

---

### Task 20: Pre-commit Hooks & CI Pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [master, develop, "feature/*", "fix/*"]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Syntax check all Python files
        run: |
          Get-ChildItem -Path skills -Recurse -Filter *.py | ForEach-Object {
            python -m py_compile $_.FullName
            if ($LASTEXITCODE -ne 0) { exit 1 }
          }
        shell: pwsh

      - name: Run tests
        run: python -m pytest tests/ -v --cov=skills --cov-report=term-missing

      - name: Check for secrets in tracked files
        run: |
          $found = git grep -l "sk-or-v1-" -- ":(exclude).env*" ":(exclude).gitignore" 2>$null
          if ($found) {
            Write-Error "Possible API key found in tracked files: $found"
            exit 1
          }
        shell: pwsh
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow — tests, syntax check, secrets scan"
```

---

### Task 21: Documentation Reconciliation

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md key directories to include new skills**

In `CLAUDE.md`, in the Key Directories section, add under the skills listing:

After `buddy-search`:
```
  buddy-utils     — shared utilities (env_loader)
```

- [ ] **Step 2: Update CLAUDE.md implementation phases**

Update the phases list to reflect current state:
```
1. **Buddy Alive** ✅ — OpenClaw + Telegram + DeepSeek + identity templates
2. **Remembers & Hears** ✅ — Voice UA + memory system
3. **Acts Safely** ✅ — Full security + files + email + reminders
4. **Codes & Deploys** 🔄 — Git + buddy-meta self-extending
5. **On Server** ⏳ — Railway 24/7 deployment
6. **Future:** Business orders, Viber, voice calls
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with new skills and phase status"
```

---

### Task 22: Final Validation

**Files:** None (validation only)

- [ ] **Step 1: Run full test suite**

```bash
cd "D:/Myapps/buddy agent"
python -m pytest tests/ -v --cov=skills --cov-report=term-missing
```

Expected: All tests PASS with reasonable coverage.

- [ ] **Step 2: Syntax check all Python files**

```bash
cd "D:/Myapps/buddy agent"
find skills -name "*.py" -exec python -m py_compile {} \;
echo "All syntax checks passed"
```

- [ ] **Step 3: Verify git status is clean**

```bash
cd "D:/Myapps/buddy agent"
git status
git log --oneline -15
```

Expected: Clean working tree, 15+ well-organized commits.

- [ ] **Step 4: Run sync.sh to verify workspace sync works**

```bash
cd "D:/Myapps/buddy agent"
bash sync.sh
```

Expected: All health checks pass.
