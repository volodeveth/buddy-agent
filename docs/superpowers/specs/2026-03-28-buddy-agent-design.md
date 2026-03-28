# Buddy Agent — Design Specification

> **Date:** 2026-03-28
> **Status:** Approved
> **Author:** Claude Opus (orchestrator) + User
> **Project:** D:/Myapps/buddy agent/

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [OpenClaw Core — What We Get For Free](#3-openclaw-core--what-we-get-for-free)
4. [Custom Skills — What We Build](#4-custom-skills--what-we-build)
5. [Security Layer (detailed)](#5-security-layer-detailed)
6. [Configuration Files](#6-configuration-files)
7. [Data Flow Scenarios](#7-data-flow-scenarios)
8. [Technology Stack](#8-technology-stack)
9. [Implementation Phases](#9-implementation-phases)
10. [Budget Estimation](#10-budget-estimation)
11. [Future Roadmap](#11-future-roadmap)
12. [Key Decisions Log](#12-key-decisions-log)

---

## 1. Project Overview

### What Is Buddy Agent?

Buddy Agent is a personal AI assistant built on top of **OpenClaw** (the fastest-growing open-source AI agent framework, 247K+ GitHub stars). It connects to the user via **Telegram** (text + voice), uses **DeepSeek V3.2** via **OpenRouter** as its LLM brain, and can execute real-world tasks: manage files, send emails, write code, deploy projects, set reminders, and more.

### Core Principles

1. **OpenClaw as foundation** — don't reinvent the wheel. Use OpenClaw's gateway, LLM integration, memory, and sandbox. Focus custom development on what OpenClaw doesn't provide.
2. **Security first** — three-tier permission model (SAFE/MEDIUM/CRITICAL), PIN gate for dangerous actions, file whitelist, kernel-level sandbox via NemoClaw.
3. **Ukrainian language** — all communication with the user in Ukrainian. Code and API interactions in English.
4. **Incremental delivery** — each phase produces a working product. Phase 1 = chatbot, Phase 5 = 24/7 server agent.
5. **Budget-conscious** — target $5-10/month. DeepSeek V3.2 is extremely cheap ($0.14/1M input tokens). STT/TTS are free (local Whisper + edge-tts).
6. **Single user** — the bot serves only one person (owner). Multi-user is a future consideration.

### User Profile

- **Role:** Developer / Entrepreneur
- **Primary language:** Ukrainian
- **Tech stack:** TypeScript, Next.js, Python
- **Deployment:** Vercel, Railway
- **Git:** GitHub
- **Messaging:** Telegram (primary), Viber (future), Email
- **Business need (future):** Accept orders from clients in Telegram → Google Sheets → notify supplier via email + messenger

### What the Bot Must Do

| Category | Capabilities | Security Level |
|----------|-------------|----------------|
| **Chat** | Answer questions, have conversations, brainstorm | SAFE |
| **Memory** | Remember conversations, semantic search over history | SAFE (recall), MEDIUM (forget) |
| **Voice** | Receive voice messages (STT), reply with voice (TTS) | SAFE |
| **Files** | Create, read, edit, organize files in whitelisted folders | SAFE (read), MEDIUM (write), CRITICAL (delete) |
| **Search** | Web search, memory search, file search | SAFE |
| **Communication** | Send emails, Telegram messages to contacts | MEDIUM (send), CRITICAL (send as owner) |
| **Reminders** | Set time-based reminders, cron tasks | MEDIUM |
| **Development** | Generate code, git commit/push, deploy | MEDIUM (commit), CRITICAL (deploy) |
| **System** | Run shell commands, check system status | SAFE (status), CRITICAL (exec) |
| **Business (future)** | Parse orders, write to Google Sheets, notify supplier | MEDIUM |

---

## 2. Architecture

### High-Level Diagram

```
+-------------------------------------------------------------+
|                    BUDDY AGENT (OpenClaw)                     |
|                                                             |
|  +------------------------------------------------------+   |
|  |              OpenClaw CORE (built-in)                 |   |
|  |                                                      |   |
|  |  +---------+  +---------+  +----------+  +---------+ |   |
|  |  | Gateway |  |   LLM   |  |  Memory  |  | Sandbox | |   |
|  |  |Telegram |  |DeepSeek |  |Persistent|  |NemoClaw | |   |
|  |  |WhatsApp |  |via Open |  | + Daily  |  |OpenShell| |   |
|  |  |Discord  |  | Router  |  | + Vector |  |         | |   |
|  |  +---------+  +---------+  +----------+  +---------+ |   |
|  +-------------------------+----------------------------+   |
|                            |                                |
|  +-------------------------v----------------------------+   |
|  |           CUSTOM SKILLS (we build)                    |   |
|  |                                                      |   |
|  |  ~/openclaw/skills/                                   |   |
|  |  +-- buddy-security/    PIN gate, 3-tier security     |   |
|  |  +-- buddy-voice-ua/    STT Whisper + TTS Ukrainian   |   |
|  |  +-- buddy-files/       whitelist file system         |   |
|  |  +-- buddy-comms/       email, contacts, messaging    |   |
|  |  +-- buddy-dev/         git, deploy, code generation  |   |
|  |  +-- buddy-scheduler/   reminders, cron tasks         |   |
|  |  +-- buddy-search/      web + semantic + file search  |   |
|  |  +-- buddy-business/    [future] orders, Sheets       |   |
|  +------------------------------------------------------+   |
|                                                             |
|  +------------------------------------------------------+   |
|  |           CONFIGURATION                               |   |
|  |                                                      |   |
|  |  ~/.openclaw/config.yaml     LLM, gateway, API keys   |   |
|  |  ~/openclaw/templates/                                |   |
|  |  +-- SOUL.md          character, communication style  |   |
|  |  +-- IDENTITY.md      role, capabilities              |   |
|  |  +-- USER.md          owner info, preferences         |   |
|  |  +-- TOOLS.md         allowed tools                   |   |
|  |  +-- BOOT.md          startup sequence                |   |
|  |  +-- HEARTBEAT.md     periodic tasks                  |   |
|  |  ~/openclaw/memory/                                   |   |
|  |  +-- MEMORY.md        persistent context              |   |
|  |  +-- people/           contacts                       |   |
|  |  +-- projects/         project notes                  |   |
|  |  +-- decisions/        decision log                   |   |
|  +------------------------------------------------------+   |
|                                                             |
|  +------------------------------------------------------+   |
|  |    SECURITY OVERLAY (NemoClaw + buddy-security)       |   |
|  |                                                      |   |
|  |  NemoClaw (Nvidia):                                   |   |
|  |  +-- OpenShell sandbox (kernel-level isolation)       |   |
|  |  +-- Network egress whitelist (only allowed APIs)     |   |
|  |  +-- Declarative policy YAML                          |   |
|  |  +-- Shell command filtering                          |   |
|  |                                                      |   |
|  |  buddy-security skill (ours):                         |   |
|  |  +-- PIN gate for CRITICAL actions                    |   |
|  |  +-- 3-tier classification (SAFE/MEDIUM/CRITICAL)     |   |
|  |  +-- File whitelist enforcement                       |   |
|  |  +-- Anti-spoofing (bot can't self-approve)           |   |
|  |  +-- Audit log of ALL actions                         |   |
|  +------------------------------------------------------+   |
+-------------------------------------------------------------+
```

### Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **OpenClaw as base** (not custom) | 70% functionality out of the box. 247K+ stars = active community. MIT license = no lock-in. |
| **Modular Monolith** approach | Single process (OpenClaw) + Python sidecar (voice). No microservices overhead for single user. |
| **DeepSeek V3.2 via OpenRouter** | Cheapest capable model ($0.14/1M input). OpenRouter gives failover + model switching. 128K context. |
| **NemoClaw + custom security** | NemoClaw = kernel-level sandbox (Nvidia). Our buddy-security = application-level PIN + permissions. Defense in depth. |
| **Local-first, cloud-ready** | Start on local machine. Phase 5 deploys to Railway with minimal changes. |
| **Python sidecar for voice** | faster-whisper and edge-tts are Python-native. OpenClaw is TypeScript. Sidecar communicates via HTTP. |

---

## 3. OpenClaw Core — What We Get For Free

### Gateway (Telegram)

OpenClaw natively supports Telegram as a messaging gateway:
- Bot creation via @BotFather
- Polling mode (local) / webhook mode (server)
- Text messages, voice messages, inline keyboards, callback queries
- File sending/receiving
- Multi-gateway support (can add WhatsApp, Discord later)

**We configure:** `config.yaml` → `gateway.telegram` section with bot token and owner_id.

### LLM Integration

OpenClaw connects to any OpenAI-compatible API:
- DeepSeek V3.2 via OpenRouter (our choice)
- Automatic context management
- System prompts from templates (SOUL.md, IDENTITY.md)
- Tool/function calling support
- Fallback model configuration

**We configure:** `config.yaml` → `llm` section with OpenRouter API key and model.

### Memory System

OpenClaw has a sophisticated built-in memory system:
- `MEMORY.md` — always in context, persistent facts
- `memory/YYYY-MM-DD.md` — daily notes (today + yesterday auto-loaded)
- `memory/people/` — contact profiles
- `memory/projects/` — project context
- `memory/decisions/` — decision log
- Auto-summarization of daily conversations
- The agent can read/write memory files as part of conversations

**We configure:** `config.yaml` → `memory` section + populate initial memory files.

**Note:** OpenClaw's memory is file-based (Markdown). For semantic vector search, we either:
- Use OpenClaw's built-in search if available, OR
- Add a simple embedding search in our `buddy-search` skill using ChromaDB or similar

### Sandbox (NemoClaw)

NemoClaw by Nvidia provides:
- Kernel-level sandboxing via OpenShell
- Declarative YAML policy for network, filesystem, and shell
- Network egress whitelist (only allowed API endpoints)
- Filesystem access control (read/write per directory)
- Shell command filtering (allow/deny patterns)
- Resource limits (CPU time, memory, file size)

**We configure:** `policies/buddy-sandbox.yaml` with our specific rules.

### Built-in Skills (100+)

OpenClaw comes with skills we DON'T need to build:
- `web-search` — DuckDuckGo search
- `file-manager` — basic file operations
- `shell` — command execution
- `git` — basic git operations
- `skill-creator` — create new skills from natural language
- `telegram-offline-voice` — edge-tts voice messages

**We build custom skills** only for functionality that doesn't exist or needs our specific behavior (security, Ukrainian voice, business logic).

---

## 4. Custom Skills — What We Build

### 4.1. buddy-security (Security Enforcement)

**Priority:** 100 (executes first, before any other skill)
**Trigger:** always (intercepts every action)

#### File Structure

```
skills/buddy-security/
+-- SKILL.md              <- Instructions: classify action -> check level -> request PIN
+-- security_config.json  <- whitelist paths, blacklist commands, sensitive patterns
+-- pin_gate.py           <- PIN verification (bcrypt hash), lockout logic, timeout
+-- audit_log.py          <- Structured logging of every action with timestamp
```

#### SKILL.md Content (Full)

```yaml
# Frontmatter
name: buddy-security
description: Security enforcement for all Buddy Agent actions. Classifies every action into SAFE/MEDIUM/CRITICAL and enforces appropriate confirmation.
trigger: always
priority: 100
tools:
  - send_message (for confirmation dialogs)
  - shell (for running pin_gate.py and audit_log.py)
```

```markdown
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
- Execute a shell command (except whitelisted: git, npm, node, python, pip)
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
  (e.g., "delete 10 files" = 10 individual PIN requests, not one bulk approval)

## Audit Log Format

Every action is logged to ~/openclaw/data/audit.jsonl:
{
  "timestamp": "2026-03-28T14:30:00Z",
  "action": "file.delete",
  "target": "D:/BuddyWorkspace/old-project/",
  "security_level": "CRITICAL",
  "decision": "approved",      // approved | denied | timeout | lockout
  "pin_used": true,
  "initiated_by": "user_message",
  "original_message": "Delete the old-project folder",
  "execution_result": "success" // success | error | cancelled
}
```

#### security_config.json

```json
{
  "owner_telegram_id": 123456789,
  "pin_hash": "$2b$12$... (bcrypt hash of PIN)",
  "whitelist_paths": [
    "D:/BuddyWorkspace",
    "D:/Projects",
    "D:/Documents"
  ],
  "blacklist_commands": [
    "rm -rf /",
    "rm -rf ~",
    "rm -rf .",
    "format",
    "shutdown",
    "del /s /q",
    "net user",
    "reg delete",
    "powershell -enc",
    "powershell -encodedcommand",
    "cmd /c rd /s /q",
    "mkfs",
    "dd if=",
    "> /dev/sda",
    ":(){ :|:& };:",
    "wget | sh",
    "curl | bash"
  ],
  "sensitive_file_patterns": [
    "*.env",
    "*.env.*",
    "*.key",
    "*.pem",
    "*.cert",
    "*.p12",
    "*.pfx",
    "*password*",
    "*secret*",
    "*credential*",
    "*token*",
    "id_rsa",
    "id_ed25519",
    "*.keystore",
    ".git-credentials",
    ".npmrc",
    ".pypirc"
  ],
  "pin_timeout_seconds": 60,
  "max_pin_attempts": 3,
  "lockout_minutes": 15,
  "command_timeout_seconds": 300,
  "max_file_size_mb": 100,
  "audit_log_path": "~/openclaw/data/audit.jsonl"
}
```

#### pin_gate.py

```python
#!/usr/bin/env python3
"""PIN Gate — validates PIN codes for CRITICAL actions."""

import sys
import json
import bcrypt
from pathlib import Path
from datetime import datetime, timedelta

CONFIG_PATH = Path.home() / "openclaw" / "data" / "security_config.json"
LOCKOUT_PATH = Path.home() / "openclaw" / "data" / "pin_lockout.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def check_lockout():
    """Return True if currently locked out."""
    if not LOCKOUT_PATH.exists():
        return False
    with open(LOCKOUT_PATH) as f:
        data = json.load(f)
    lockout_until = datetime.fromisoformat(data.get("lockout_until", "2000-01-01"))
    if datetime.now() < lockout_until:
        remaining = (lockout_until - datetime.now()).seconds // 60
        print(json.dumps({"status": "lockout", "minutes_remaining": remaining}))
        return True
    # Lockout expired, reset
    LOCKOUT_PATH.unlink(missing_ok=True)
    return False

def verify_pin(pin_input: str) -> bool:
    """Verify PIN against bcrypt hash."""
    config = load_config()
    pin_hash = config["pin_hash"].encode("utf-8")
    return bcrypt.checkpw(pin_input.encode("utf-8"), pin_hash)

def record_failure():
    """Record a failed PIN attempt; lockout after max_attempts."""
    config = load_config()
    lockout_data = {"attempts": 0, "lockout_until": None}
    if LOCKOUT_PATH.exists():
        with open(LOCKOUT_PATH) as f:
            lockout_data = json.load(f)

    lockout_data["attempts"] = lockout_data.get("attempts", 0) + 1

    if lockout_data["attempts"] >= config["max_pin_attempts"]:
        lockout_until = datetime.now() + timedelta(minutes=config["lockout_minutes"])
        lockout_data["lockout_until"] = lockout_until.isoformat()
        lockout_data["attempts"] = 0

    with open(LOCKOUT_PATH, "w") as f:
        json.dump(lockout_data, f)

    return lockout_data

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "PIN not provided"}))
        sys.exit(1)

    pin_input = sys.argv[1]

    if check_lockout():
        sys.exit(1)

    if verify_pin(pin_input):
        # Reset attempts on success
        LOCKOUT_PATH.unlink(missing_ok=True)
        print(json.dumps({"status": "approved"}))
        sys.exit(0)
    else:
        result = record_failure()
        attempts_left = load_config()["max_pin_attempts"] - result.get("attempts", 0)
        if result.get("lockout_until"):
            print(json.dumps({"status": "lockout", "minutes_remaining": load_config()["lockout_minutes"]}))
        else:
            print(json.dumps({"status": "denied", "attempts_remaining": attempts_left}))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

#### audit_log.py

```python
#!/usr/bin/env python3
"""Audit Logger — logs every action to a JSONL file."""

import sys
import json
from pathlib import Path
from datetime import datetime

AUDIT_PATH = Path.home() / "openclaw" / "data" / "audit.jsonl"

def log_action(action: str, target: str, level: str, decision: str,
               pin_used: bool = False, initiated_by: str = "user_message",
               original_message: str = "", execution_result: str = "pending"):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "target": target,
        "security_level": level,
        "decision": decision,
        "pin_used": pin_used,
        "initiated_by": initiated_by,
        "original_message": original_message,
        "execution_result": execution_result
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def main():
    if len(sys.argv) < 5:
        print("Usage: audit_log.py <action> <target> <level> <decision> [pin_used] [original_message] [result]")
        sys.exit(1)

    action = sys.argv[1]
    target = sys.argv[2]
    level = sys.argv[3]
    decision = sys.argv[4]
    pin_used = sys.argv[5].lower() == "true" if len(sys.argv) > 5 else False
    original_message = sys.argv[6] if len(sys.argv) > 6 else ""
    result = sys.argv[7] if len(sys.argv) > 7 else "pending"

    entry = log_action(action, target, level, decision, pin_used, "user_message", original_message, result)
    print(json.dumps(entry, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

---

### 4.2. buddy-voice-ua (Ukrainian Voice)

**Priority:** 80
**Trigger:** on_voice_message, on_command "/voice"

#### File Structure

```
skills/buddy-voice-ua/
+-- SKILL.md
+-- stt_whisper.py        <- faster-whisper (small model), runs locally, free
+-- tts_edge.py           <- edge-tts, Ukrainian voices, free
+-- voice_utils.py        <- format conversion (ogg -> wav -> ogg)
+-- requirements.txt      <- faster-whisper, edge-tts, pydub
```

#### SKILL.md Content

```yaml
name: buddy-voice-ua
description: Ukrainian voice messages - STT via local Whisper, TTS via Edge-TTS. Handles incoming voice messages and generates voice replies.
trigger:
  - on_voice_message
  - on_command: /voice
priority: 80
tools:
  - shell
  - send_voice
  - file_read
  - file_write
```

```markdown
## Voice Message Handling

### Incoming Voice (STT)
1. Receive voice message from Telegram (OGG/Opus format)
2. Save to temp file: ~/openclaw/data/temp/voice_in_TIMESTAMP.ogg
3. Run: python stt_whisper.py <input_file>
4. Get transcribed text (Ukrainian)
5. Process the text as a normal text message
6. Delete temp file after processing

### Outgoing Voice (TTS)
1. After generating a text response, also generate voice:
2. Run: python tts_edge.py "<response_text>" <output_file>
3. Voice: "uk-UA-OstapNeural" (male) or "uk-UA-PolinaNeural" (female)
4. Send voice message via Telegram send_voice
5. Also send text version (for readability)
6. Delete temp file after sending

### /voice Command
When user sends /voice followed by text:
- Generate TTS of that text and send as voice message
- Useful for testing voice output

### Error Handling
- If STT fails: reply with "Could not recognize voice. Please try again or send text."
- If TTS fails: send text-only reply with note "Voice generation temporarily unavailable"
- If voice file is too long (>5 minutes): transcribe first 5 minutes, warn about truncation

### Performance Notes
- faster-whisper "small" model: ~1-3 seconds for 30-second audio on CPU
- edge-tts: ~1-2 seconds for a paragraph of text
- Total voice loop: under 5 seconds for typical message
```

#### stt_whisper.py

```python
#!/usr/bin/env python3
"""Speech-to-Text using faster-whisper (local, free)."""

import sys
import json
from faster_whisper import WhisperModel

# Use "small" model - good balance of speed and accuracy for Ukrainian
# Downloads ~461MB on first run, then cached
MODEL_SIZE = "small"

def transcribe(audio_path: str) -> dict:
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, language="uk", beam_size=5)

    text = " ".join([segment.text.strip() for segment in segments])

    return {
        "text": text,
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
        "duration": round(info.duration, 1)
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No audio file path provided"}))
        sys.exit(1)

    audio_path = sys.argv[1]
    result = transcribe(audio_path)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

#### tts_edge.py

```python
#!/usr/bin/env python3
"""Text-to-Speech using edge-tts (Microsoft Edge, free, Ukrainian supported)."""

import sys
import json
import asyncio
import edge_tts

# Ukrainian voices available in edge-tts:
# - uk-UA-OstapNeural (male)
# - uk-UA-PolinaNeural (female)
DEFAULT_VOICE = "uk-UA-OstapNeural"

async def synthesize(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> dict:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return {
        "status": "success",
        "output_path": output_path,
        "voice": voice,
        "text_length": len(text)
    }

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: tts_edge.py <text> <output_path> [voice]"}))
        sys.exit(1)

    text = sys.argv[1]
    output_path = sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VOICE

    result = asyncio.run(synthesize(text, output_path, voice))
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

#### voice_utils.py

```python
#!/usr/bin/env python3
"""Voice format utilities — convert between OGG, WAV, MP3."""

import sys
import json
from pathlib import Path
from pydub import AudioSegment

def convert(input_path: str, output_format: str = "wav") -> str:
    """Convert audio file to specified format. Returns output path."""
    input_file = Path(input_path)
    output_path = input_file.with_suffix(f".{output_format}")

    audio = AudioSegment.from_file(input_path)
    audio.export(str(output_path), format=output_format)

    return str(output_path)

def get_duration(input_path: str) -> float:
    """Get audio duration in seconds."""
    audio = AudioSegment.from_file(input_path)
    return len(audio) / 1000.0

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: voice_utils.py <convert|duration> <file_path> [format]"}))
        sys.exit(1)

    command = sys.argv[1]
    file_path = sys.argv[2]

    if command == "convert":
        fmt = sys.argv[3] if len(sys.argv) > 3 else "wav"
        result = convert(file_path, fmt)
        print(json.dumps({"output_path": result}))
    elif command == "duration":
        duration = get_duration(file_path)
        print(json.dumps({"duration_seconds": duration}))

if __name__ == "__main__":
    main()
```

#### requirements.txt

```
faster-whisper>=1.1.0
edge-tts>=6.1.0
pydub>=0.25.1
```

---

### 4.3. buddy-files (File System with Whitelist)

#### File Structure

```
skills/buddy-files/
+-- SKILL.md
+-- file_validator.py     <- Validate file paths against whitelist
```

#### SKILL.md Content

```yaml
name: buddy-files
description: Secure file operations with whitelist enforcement. All file access must pass through this skill.
trigger:
  - on_file_operation
  - on_intent: file_read, file_write, file_delete, file_list, file_move, file_organize
priority: 90
tools:
  - file_read
  - file_write
  - shell
```

```markdown
## Rules

1. ALWAYS validate the file path via file_validator.py BEFORE any file operation
2. Whitelisted directories (from security_config.json):
   - D:/BuddyWorkspace/ — primary workspace
   - D:/Projects/ — development projects
   - D:/Documents/ — documents
3. If path is NOT in whitelist -> delegate to buddy-security (REQUEST PERMISSION flow)
4. NEVER touch:
   - C:/Windows/, C:/Program Files/, C:/Program Files (x86)/
   - Any system directories
   - Other users' files
   - Hidden system files
5. Delete operations -> ALWAYS CRITICAL level via buddy-security
6. Operations on sensitive files (*.env, *.key, etc.) -> ALWAYS CRITICAL
7. When creating files, suggest appropriate directory from whitelist
8. When organizing files, show the plan before executing (list of moves)
9. Maximum file size for creation: 100MB (from security_config.json)
10. Binary files: can read metadata, cannot modify content
```

#### file_validator.py

```python
#!/usr/bin/env python3
"""Validate file paths against whitelist and security rules."""

import sys
import json
import fnmatch
from pathlib import Path

CONFIG_PATH = Path.home() / "openclaw" / "data" / "security_config.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def normalize_path(path_str: str) -> Path:
    """Normalize path for consistent comparison."""
    return Path(path_str).resolve()

def is_whitelisted(path: str, config: dict) -> bool:
    """Check if path is within whitelisted directories."""
    normalized = normalize_path(path)
    for wl_path in config["whitelist_paths"]:
        wl_normalized = normalize_path(wl_path)
        try:
            normalized.relative_to(wl_normalized)
            return True
        except ValueError:
            continue
    return False

def is_sensitive(path: str, config: dict) -> bool:
    """Check if file matches sensitive patterns."""
    filename = Path(path).name
    full_path = str(Path(path))
    for pattern in config["sensitive_file_patterns"]:
        if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(full_path, pattern):
            return True
    return False

def validate(path: str, operation: str = "read") -> dict:
    """Validate a file operation. Returns security level and whether it's allowed."""
    config = load_config()

    result = {
        "path": path,
        "operation": operation,
        "whitelisted": is_whitelisted(path, config),
        "sensitive": is_sensitive(path, config),
        "security_level": "SAFE",
        "allowed": True,
        "reason": ""
    }

    # Determine security level
    if result["sensitive"]:
        result["security_level"] = "CRITICAL"
        result["reason"] = "Sensitive file pattern detected"
    elif operation == "delete":
        result["security_level"] = "CRITICAL"
        result["reason"] = "Delete operation requires PIN"
    elif not result["whitelisted"]:
        result["security_level"] = "CRITICAL"
        result["reason"] = "Path outside whitelist"
    elif operation in ("write", "create", "move", "rename"):
        result["security_level"] = "MEDIUM"
        result["reason"] = "Write operation requires confirmation"
    else:
        result["security_level"] = "SAFE"
        result["reason"] = "Read in whitelisted directory"

    return result

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: file_validator.py <path> [operation]"}))
        sys.exit(1)

    path = sys.argv[1]
    operation = sys.argv[2] if len(sys.argv) > 2 else "read"

    result = validate(path, operation)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

---

### 4.4. buddy-comms (Communication)

#### File Structure

```
skills/buddy-comms/
+-- SKILL.md
+-- send_email.py         <- SMTP via Gmail App Password or Resend
+-- contacts.json         <- Contact database (name -> email, telegram, viber)
+-- message_templates/
|   +-- meeting_reschedule.md
|   +-- order_confirmation.md
|   +-- general_message.md
```

#### SKILL.md Content

```yaml
name: buddy-comms
description: Send emails and messages to contacts. Always shows preview before sending. Contacts are managed in contacts.json.
trigger:
  - on_intent: send_email, send_message, contact_lookup
priority: 70
tools:
  - shell
  - send_message
  - file_read
```

```markdown
## Rules

1. Before sending ANY message, ALWAYS show the user:
   - Recipient (name + address/handle)
   - Subject/context (for email)
   - Full message text
   - Delivery method (email, Telegram, etc.)
2. Email -> MEDIUM security (confirmation button)
3. Sending ON BEHALF of owner (impersonating) -> CRITICAL (PIN)
4. Contacts are ONLY from contacts.json
5. Unknown contact -> ask for clarification, NEVER guess email/phone
6. For emails, use templates from message_templates/ when applicable
7. Always sign emails with owner's name (from USER.md)
8. CC/BCC -> show explicitly before sending
9. Attachments -> show file name and size before sending

## Contact Lookup

When user says "send to Oleg" or "email Oleg":
1. Search contacts.json for matching name (case-insensitive, partial match)
2. If exact match -> use that contact
3. If multiple matches -> show list, ask to choose
4. If no match -> ask user for contact details, offer to save to contacts.json

## Email Sending

Uses send_email.py which supports:
- Gmail App Password (SMTP, free)
- Resend API (alternative, generous free tier)
- HTML and plain text
- Attachments
```

#### contacts.json (template)

```json
{
  "contacts": [
    {
      "name": "Oleg Petrenko",
      "nickname": ["Oleg", "Oleh"],
      "email": "oleg@example.com",
      "telegram": "@oleg_p",
      "viber": "+380501234567",
      "role": "colleague",
      "notes": "Frontend developer, works on Project Alpha"
    }
  ]
}
```

#### send_email.py

```python
#!/usr/bin/env python3
"""Send emails via SMTP (Gmail) or Resend API."""

import sys
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_via_smtp(to: str, subject: str, body: str,
                  from_name: str = "Buddy Agent") -> dict:
    """Send email via Gmail SMTP."""
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_APP_PASSWORD", "")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        return {"status": "error", "message": "SMTP credentials not configured"}

    msg = MIMEMultipart()
    msg["From"] = f"{from_name} <{smtp_user}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return {"status": "success", "to": to, "subject": subject}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    if len(sys.argv) < 4:
        print(json.dumps({"error": "Usage: send_email.py <to> <subject> <body>"}))
        sys.exit(1)

    to = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]
    from_name = sys.argv[4] if len(sys.argv) > 4 else "Buddy Agent"

    result = send_via_smtp(to, subject, body, from_name)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

---

### 4.5. buddy-dev (Development & Deploy)

#### File Structure

```
skills/buddy-dev/
+-- SKILL.md
+-- deploy_railway.sh     <- Railway deploy script
+-- deploy_vercel.sh      <- Vercel deploy script
+-- project_templates/
|   +-- nextjs/            <- Next.js project template
|   +-- python-api/        <- Python FastAPI template
|   +-- static-site/       <- Simple HTML/CSS/JS template
```

#### SKILL.md Content

```yaml
name: buddy-dev
description: Development workflow - scaffold projects, generate code, git operations, deploy to Vercel/Railway.
trigger:
  - on_intent: create_project, write_code, git_commit, git_push, deploy, code_review
priority: 60
tools:
  - shell
  - file_read
  - file_write
  - web_search
```

```markdown
## Workflow: "Create and deploy a project"

This is the full workflow. Each step has its own security level.

### Step 1: Scaffold (SAFE - within whitelist)
1. Ask: what type of project? (Next.js / Python API / Static / Custom)
2. Ask: project name?
3. Create project directory in D:/Projects/<name>/
4. Copy template files from project_templates/
5. Show project structure to user

### Step 2: Code (SAFE - generate and show, MEDIUM - write to files)
1. Discuss requirements with user
2. Generate code via DeepSeek
3. Show code diff to user
4. On confirmation -> write files (MEDIUM)

### Step 3: Test (MEDIUM - run commands)
1. Run: npm install / pip install (MEDIUM)
2. Run: npm test / pytest (MEDIUM)
3. Show test results
4. If tests fail -> fix and re-run

### Step 4: Git (MEDIUM)
1. git init (if new project)
2. Create .gitignore (include *.env, node_modules, etc.)
3. git add -A
4. Show what will be committed
5. On confirmation -> git commit (MEDIUM)
6. git remote add origin (if not set)
7. git push (MEDIUM)

### Step 5: Deploy (CRITICAL - PIN required)
1. Ask: where to deploy? (Vercel / Railway)
2. Show deployment plan
3. Require PIN
4. Run deploy_vercel.sh or deploy_railway.sh
5. Wait for deployment to complete
6. Report deployment URL

## Individual Operations

### git commit + push
- Security: MEDIUM
- Always show: list of changed files, commit message
- Use conventional commits format: feat/fix/chore/refactor/docs

### code generation
- Security: SAFE (show code), MEDIUM (write to file)
- Always show generated code before writing
- Follow project's existing patterns and style

### deploy
- Security: CRITICAL (always requires PIN)
- Show: project name, platform, branch, environment (preview/production)
- After deploy: report URL and status
```

#### deploy_vercel.sh

```bash
#!/bin/bash
# Deploy to Vercel
# Usage: deploy_vercel.sh <project_dir> [--prod]

set -e

PROJECT_DIR="$1"
PROD_FLAG="$2"

cd "$PROJECT_DIR"

if [ "$PROD_FLAG" = "--prod" ]; then
    echo "Deploying to PRODUCTION..."
    vercel --prod --yes 2>&1
else
    echo "Deploying preview..."
    vercel --yes 2>&1
fi
```

#### deploy_railway.sh

```bash
#!/bin/bash
# Deploy to Railway
# Usage: deploy_railway.sh <project_dir>

set -e

PROJECT_DIR="$1"

cd "$PROJECT_DIR"

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "ERROR: Railway CLI not installed. Run: npm install -g @railway/cli"
    exit 1
fi

echo "Deploying to Railway..."
railway up 2>&1
```

---

### 4.6. buddy-scheduler (Reminders & Cron)

#### File Structure

```
skills/buddy-scheduler/
+-- SKILL.md
+-- scheduler.py          <- APScheduler-based reminder system
+-- reminders.json        <- Stored reminders
```

#### SKILL.md Content

```yaml
name: buddy-scheduler
description: Set reminders, schedule tasks, manage recurring jobs. Checks HEARTBEAT.md for periodic tasks.
trigger:
  - on_intent: set_reminder, cancel_reminder, list_reminders, schedule_task
  - on_heartbeat
priority: 50
tools:
  - shell
  - send_message
  - file_read
  - file_write
```

```markdown
## Reminder Types

### One-time reminder
"Remind me at 15:00 to call Oleg"
-> Store in reminders.json with exact datetime
-> On trigger: send Telegram message

### Recurring reminder
"Every Monday at 9:00 remind me about standup"
-> Store with cron expression
-> On trigger: send Telegram message

### Relative reminder
"Remind me in 2 hours about the meeting"
-> Calculate absolute time from now
-> Store as one-time reminder

## Time Parsing
- Understand Ukrainian time expressions:
  - "о 15:00", "через 2 години", "завтра о 10:00"
  - "щопонеділка о 9:00", "кожного дня о 18:00"
  - "в п'ятницю", "наступного тижня"
- Convert all to UTC internally, display in user's timezone (Europe/Kyiv, UTC+2/+3)

## Storage (reminders.json)
{
  "reminders": [
    {
      "id": "uuid",
      "text": "Call Oleg",
      "trigger_at": "2026-03-28T15:00:00+02:00",
      "recurring": null,
      "created_at": "2026-03-28T12:00:00+02:00",
      "status": "active"
    }
  ]
}

## Heartbeat Integration
- Every 30 minutes (via HEARTBEAT.md), check for due reminders
- Send notifications for any that triggered since last check
- Mark triggered reminders as "completed" (or reschedule if recurring)

## Security
- Setting a reminder: MEDIUM (confirmation button)
- Canceling a reminder: SAFE (just show confirmation)
- Listing reminders: SAFE
```

---

### 4.7. buddy-search (Search Router)

#### File Structure

```
skills/buddy-search/
+-- SKILL.md
+-- search_router.py      <- Determines search type based on query
```

#### SKILL.md Content

```yaml
name: buddy-search
description: Routes search queries to appropriate backend - web (DuckDuckGo), memory (OpenClaw), or file system.
trigger:
  - on_intent: search, find, lookup
priority: 50
tools:
  - web_search
  - file_read
  - shell
```

```markdown
## Search Routing Rules

Analyze the user's query and route to the appropriate search:

### Memory Search (OpenClaw built-in)
Triggers: references to past conversations, "what did I say", "remember when",
personal facts, preferences, decisions, contacts
Example: "What did I say about project Alpha last week?"

### Web Search (DuckDuckGo, built-in)
Triggers: current events, documentation, how-to, external information,
anything not related to personal history
Example: "How to configure nginx reverse proxy?"

### File Search (buddy-files)
Triggers: "find file", "where is", references to specific filenames,
content search within files
Example: "Find all TODO comments in my project"

### Combined Search
When unsure, or query is broad:
1. First check memory (fast, personal context)
2. If insufficient -> search files (if file-related)
3. If still insufficient -> web search
4. Combine and summarize results

## Rules
- All searches are SAFE level (read-only)
- File search respects buddy-files whitelist
- Always cite sources: "Found in memory from March 15" or "From web: [url]"
- For ambiguous queries, ask: "Search in your memory, files, or the internet?"
```

---

### 4.8. buddy-business (Future — Not Built Now)

#### File Structure (planned)

```
skills/buddy-business/
+-- SKILL.md
+-- google_sheets.py      <- Google Sheets API integration
+-- order_parser.py       <- Parse orders from client text messages
+-- supplier_notify.py    <- Notify supplier via email + messenger
+-- order_templates/
|   +-- order_row.json    <- Google Sheets row format
|   +-- supplier_email.md <- Email template for supplier
```

#### SKILL.md Content (planned)

```markdown
## Planned Workflow

1. Client sends order via Telegram (text message)
2. buddy-business parses the order:
   - Client name, items, quantities, delivery address
   - Uses DeepSeek for natural language parsing
3. Shows parsed order to owner for confirmation (MEDIUM)
4. On confirmation:
   a. Writes order to Google Sheets (MEDIUM)
   b. Sends order details to supplier via email (MEDIUM)
   c. Sends order details to supplier via Telegram/Viber (MEDIUM)
5. Logs order in memory/orders/

## Not Implemented Yet
This skill is placeholder documentation for future development.
```

---

## 5. Security Layer (Detailed)

### Defense in Depth — Two Layers

```
Layer 1: NemoClaw (Nvidia) — INFRASTRUCTURE level
+-- Kernel-level sandboxing (OpenShell)
+-- Network egress whitelist (only allowed endpoints)
+-- Filesystem access control (directory-level)
+-- Shell command filtering (pattern-based)
+-- Resource limits (CPU, RAM, file size)
+-- CANNOT be bypassed by the AI agent

Layer 2: buddy-security (ours) — APPLICATION level
+-- Three-tier action classification (SAFE/MEDIUM/CRITICAL)
+-- PIN gate for CRITICAL actions
+-- Inline keyboard confirmations for MEDIUM actions
+-- File whitelist enforcement (with permission request flow)
+-- Anti-spoofing protection
+-- Comprehensive audit logging
+-- Lockout after failed PIN attempts
```

### Why Both Layers?

NemoClaw prevents the agent from doing anything harmful at the OS level — even if the AI is compromised or manipulated. But NemoClaw doesn't know about our business logic (which contacts are safe to email, which deployments need approval). That's what buddy-security adds.

### Full Security Flow

```
User message arrives
       |
       v
[1. AUTH] Is this the owner's Telegram ID?
       |-- NO --> ignore completely, log attempt
       |-- YES
       v
[2. CLASSIFY] AI determines intent + action + target
       |
       v
[3. NemoClaw CHECK] Is this action allowed by sandbox policy?
       |-- NO --> blocked, inform user "Sandbox policy prevents this"
       |-- YES
       v
[4. buddy-security CHECK] What security level?
       |
       +-- SAFE --> [EXECUTE]
       |
       +-- MEDIUM --> [CONFIRM via inline keyboard]
       |                |-- User clicks [Confirm] --> [EXECUTE]
       |                |-- User clicks [Cancel] --> [CANCEL]
       |
       +-- CRITICAL --> [PIN GATE]
                         |-- Correct PIN --> [EXECUTE]
                         |-- Wrong PIN (attempt N/3) --> retry
                         |-- 3 wrong PINs --> lockout 15 min
                         |-- Timeout 60s --> [CANCEL]

[EXECUTE]
       |-- Run the action
       |-- Log to audit_log.py
       |-- Report result to user

[CANCEL]
       |-- Log cancellation to audit_log.py
       |-- Inform user "Action cancelled"
```

### Data Protection Specifics

| Threat | Mitigation |
|--------|-----------|
| File deletion outside workspace | NemoClaw filesystem deny + buddy-files whitelist + CRITICAL PIN |
| Credential/secret leakage | Sensitive file patterns -> CRITICAL. AI system prompt: "never share credentials" |
| Prompt injection (from external text) | Input sanitization. Separate system prompt from user content. |
| Unauthorized access (not owner) | Hardcoded owner_telegram_id. No other user can interact. |
| Bot self-escalation | buddy-security priority 100 runs first. Bot cannot modify its own security config without PIN. |
| Bulk destructive actions | Each destructive action requires individual confirmation. No bulk approval. |
| Network data exfiltration | NemoClaw network egress whitelist. Only allowed API endpoints. |
| Man-in-the-middle | Telegram API uses TLS. OpenRouter uses HTTPS. |

---

## 6. Configuration Files

### ~/.openclaw/config.yaml (complete)

```yaml
# OpenClaw Configuration for Buddy Agent
# Last updated: 2026-03-28

# === LLM Provider ===
llm:
  provider: openrouter
  model: deepseek/deepseek-chat-v3.2
  api_key: ${OPENROUTER_API_KEY}
  context_window: 128000
  temperature: 0.7
  max_tokens: 4096
  system_prompt_from:
    - templates/SOUL.md
    - templates/IDENTITY.md
    - templates/USER.md
    - templates/TOOLS.md
  fallback:
    model: deepseek/deepseek-reasoner-v3.2
    trigger: on_complex_task

# === Gateway: Telegram ===
gateway:
  primary: telegram
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
    owner_id: ${TELEGRAM_OWNER_ID}
    polling: true               # true for local, false for Railway (webhook)
    webhook_url: null            # set when deploying to Railway
    voice_messages: true
    inline_keyboards: true
    max_message_length: 4096
    parse_mode: Markdown

# === Memory ===
memory:
  persistent: true
  daily_notes: true
  deep_knowledge:
    - people
    - projects
    - decisions
    - orders
  auto_summarize: true
  summarize_time: "21:00"       # Europe/Kyiv timezone

# === Sandbox (NemoClaw) ===
sandbox:
  enabled: true
  policy: ./policies/buddy-sandbox.yaml
  tools:
    allow:
      - shell
      - file_read
      - file_write
      - web_search
      - send_message
      - send_voice
    deny:
      - file_delete_system
      - network_unrestricted

# === Skills ===
skills:
  directory: ./skills
  autoload: true
  priority_order:
    - buddy-security        # 100 - always first
    - buddy-files           # 90
    - buddy-voice-ua        # 80
    - buddy-comms           # 70
    - buddy-dev             # 60
    - buddy-scheduler       # 50
    - buddy-search          # 50

# === Workspace ===
workspace:
  root: D:/BuddyWorkspace
  projects: D:/Projects
  documents: D:/Documents
  temp: ~/openclaw/data/temp

# === Heartbeat ===
heartbeat:
  interval: 1800              # 30 minutes in seconds
  tasks:
    - check_reminders
    - check_pending_tasks
    - daily_summary            # only at summarize_time
```

### policies/buddy-sandbox.yaml (NemoClaw policy — complete)

```yaml
version: "1.0"
name: buddy-agent-sandbox-policy
description: Security policy for Buddy Agent - personal AI assistant

# === Network Access ===
network:
  default: deny
  allow:
    # AI / LLM
    - api.openrouter.ai
    - openrouter.ai
    # Telegram
    - api.telegram.org
    # Web search
    - api.duckduckgo.com
    - duckduckgo.com
    # Email
    - smtp.gmail.com
    - api.resend.com
    # Git / Deploy
    - github.com
    - api.github.com
    - api.vercel.com
    - vercel.com
    - api.railway.app
    - railway.app
    # Package managers
    - registry.npmjs.org
    - pypi.org
    - files.pythonhosted.org
    # Future: Google Sheets
    - sheets.googleapis.com
    - oauth2.googleapis.com
    # Edge TTS (Microsoft)
    - speech.platform.bing.com
    - *.tts.speech.microsoft.com

# === File System Access ===
filesystem:
  default: deny
  allow:
    read:
      - D:/BuddyWorkspace/**
      - D:/Projects/**
      - D:/Documents/**
      - ~/openclaw/**
    write:
      - D:/BuddyWorkspace/**
      - D:/Projects/**
      - ~/openclaw/memory/**
      - ~/openclaw/data/**
      - ~/openclaw/skills/**
  deny:
    always:
      - C:/Windows/**
      - C:/Program Files/**
      - C:/Program Files (x86)/**
      - C:/Users/*/AppData/**
      - C:/Users/*/NTUSER*
      - C:/$Recycle.Bin/**
      - /etc/**
      - /usr/**
      - /var/**

# === Shell Commands ===
shell:
  default: deny
  allow:
    - "git *"
    - "npm *"
    - "npx *"
    - "node *"
    - "python *"
    - "python3 *"
    - "pip *"
    - "pip3 *"
    - "vercel *"
    - "railway *"
    - "code *"
    - "dir *"
    - "ls *"
    - "type *"
    - "cat *"
    - "mkdir *"
    - "cp *"
    - "mv *"
    - "echo *"
    - "curl *"           # needed for API testing
    - "which *"
    - "where *"
  deny:
    - "rm -rf /"
    - "rm -rf ~"
    - "rm -rf ."
    - "rm -rf /*"
    - "format *"
    - "shutdown *"
    - "restart *"
    - "del /s /q *"
    - "net user *"
    - "net localgroup *"
    - "reg delete *"
    - "reg add *"
    - "regedit *"
    - "powershell -enc*"
    - "powershell -encodedcommand*"
    - "cmd /c rd /s /q *"
    - "mkfs *"
    - "dd if=*"
    - "> /dev/sd*"
    - "wget * | sh"
    - "wget * | bash"
    - "curl * | sh"
    - "curl * | bash"
    - ":(){ :|:& };:"
    - "chmod 777 *"
    - "chown root *"

# === Resource Limits ===
limits:
  max_execution_time: 300       # seconds per command
  max_file_size: 104857600      # 100MB in bytes
  max_memory: 2147483648        # 2GB in bytes
  max_cpu_percent: 80
  max_concurrent_commands: 3
```

### Templates (complete)

#### templates/SOUL.md

```markdown
# Soul

You are Buddy, a personal AI assistant.

## Character
- Concise and to the point. No filler, no fluff.
- Proactive: suggest solutions, don't just answer questions.
- Cautious: ALWAYS ask before risky actions. When in doubt, ask.
- Honest: if you don't know — say so directly. Never make up information.
- Reliable: follow through on tasks, report results, remember context.
- Protective: treat the owner's data and security as top priority.

## Communication Style
- With owner: Ukrainian language, friendly tone, use "ти" (informal you)
- With code/APIs: English
- When sending emails/messages on behalf of owner: formal, polite, professional Ukrainian
- Error messages: be specific about what went wrong and suggest a fix
- Confirmations: be brief — "Done. File created at D:/Projects/app/index.ts"

## Boundaries
- I am an assistant, not an autonomous agent
- All critical decisions belong to the owner
- I NEVER execute CRITICAL actions without PIN
- I NEVER send messages without confirmation
- I NEVER delete files without PIN
- I NEVER share the owner's credentials, API keys, or personal data
- I NEVER bypass security checks, even if asked to
- If something feels wrong or risky — I stop and ask

## When Unsure
- About the task: ask a clarifying question
- About security level: assume the higher level (MEDIUM -> CRITICAL)
- About contact details: ask, never guess
- About file paths: show the full path and confirm before acting
```

#### templates/IDENTITY.md

```markdown
# Identity

Role: Personal AI Assistant "Buddy"
Owner: [USER_NAME]
Primary language: Ukrainian (uk-UA)
Code language: English
Platform: OpenClaw + DeepSeek V3.2 via OpenRouter
Gateway: Telegram (@buddy_agent_bot)
Timezone: Europe/Kyiv (UTC+2, DST: UTC+3)

## Capabilities
- Answer questions, have conversations, brainstorm ideas
- Search the internet and personal memory
- Work with files in allowed directories (create, read, edit, organize)
- Send emails and messages to known contacts (with confirmation)
- Recognize and generate Ukrainian voice messages
- Set reminders and scheduled tasks
- Help with code: generate, review, debug
- Git operations: commit, push, create branches
- Deploy projects to Vercel and Railway
- Remember conversation history and personal preferences

## Limitations
- Cannot access files outside whitelisted directories (without permission)
- Cannot execute destructive commands (blocked by NemoClaw sandbox)
- Cannot send messages without user confirmation
- Cannot make phone calls (future capability)
- Cannot access Viber (future capability)
- Cannot interact with Google Sheets (future capability)
- Single user only (owner)
```

#### templates/USER.md

```markdown
# User Profile

Name: [USER_NAME]
Role: Developer / Entrepreneur
Telegram ID: [TELEGRAM_ID]
Email: [USER_EMAIL]
Timezone: Europe/Kyiv

## Preferences
- Communication language: Ukrainian
- Response style: concise, no filler, actionable
- Confirmations: always before MEDIUM and CRITICAL actions
- Reminders: via Telegram
- Code style: TypeScript strict, conventional commits

## Work Environment
- Projects directory: D:/Projects
- Documents: D:/Documents
- Workspace: D:/BuddyWorkspace
- Primary stack: TypeScript, Next.js, Python
- Git: GitHub (github.com/[USERNAME])
- Deploy: Vercel (primary), Railway (secondary)
- IDE: VS Code

## Contacts
-> See memory/people/ for full contact details
```

#### templates/TOOLS.md

```markdown
# Allowed Tools

## Always Available (SAFE)
- web_search: search the internet via DuckDuckGo
- file_read: read files in whitelisted directories
- send_message: send Telegram messages to owner
- memory_read: read from memory files
- memory_write: write to memory files

## With Confirmation (MEDIUM)
- file_write: create or edit files
- send_email: send email to contacts
- send_telegram: send Telegram messages to other users
- shell_safe: run whitelisted shell commands (git, npm, node, python)
- git_commit: commit changes
- git_push: push to remote
- set_reminder: create a reminder

## With PIN (CRITICAL)
- file_delete: delete files
- shell_exec: run arbitrary (but not blacklisted) shell commands
- deploy: deploy to Vercel/Railway
- send_as_owner: send messages impersonating the owner
- config_modify: change security or OpenClaw config
- whitelist_modify: add/remove directories from whitelist
```

#### templates/BOOT.md

```markdown
# Boot Sequence

On every startup:

1. Check OpenRouter API connection (ping with minimal request)
2. Check Telegram bot connection (getMe)
3. Load today's reminders from buddy-scheduler
4. Check for pending/incomplete tasks from previous session
5. Load today's and yesterday's memory notes
6. Send startup message to Telegram:
   "Buddy online. [N] reminders for today. [M] pending tasks."
7. If any reminders are overdue (missed while offline), send them immediately

On error during boot:
- API connection failed: "Buddy partially online. AI unavailable, check OpenRouter API key."
- Telegram failed: log locally, retry every 60 seconds
- Non-critical error: boot anyway, report the issue
```

#### templates/HEARTBEAT.md

```markdown
# Heartbeat (every 30 minutes)

## Always
1. Check buddy-scheduler for due reminders
   - If any are due: send Telegram notification
   - If recurring: reschedule next occurrence
2. Check for pending long-running tasks
   - If completed: notify result
   - If failed: notify error, suggest retry

## Daily (21:00 Kyiv time)
3. Create daily summary in memory/YYYY-MM-DD.md:
   - Conversations summary
   - Actions taken (from audit log)
   - Reminders triggered
   - Files created/modified
   - Emails/messages sent

## Weekly (Sunday 21:00)
4. Create weekly digest:
   - Key decisions made
   - Projects worked on
   - Upcoming reminders for next week
```

---

## 7. Data Flow Scenarios

### Scenario 1: Text Question (SAFE)

```
User: "What's the best way to implement auth in Next.js?"
  |
  v
Telegram Gateway -> OpenClaw
  |
  v
[AUTH] owner_id matches -> OK
  |
  v
[buddy-security] classify: chat/question -> SAFE
  |
  v
[Memory] check for relevant context -> found: "User works with Next.js, Clerk"
  |
  v
[LLM] DeepSeek with context: question + memory context
  |
  v
[Response] Send text answer to Telegram
  |
  v
[Memory] Save Q&A to daily note
```

### Scenario 2: Voice Message (SAFE + STT/TTS)

```
User: [voice message] "Remind me to call Oleg tomorrow at 10"
  |
  v
Telegram Gateway -> voice file (.ogg)
  |
  v
[buddy-voice-ua] stt_whisper.py -> "Нагадай мені зателефонувати Олегу завтра о 10"
  |
  v
[buddy-security] classify: set_reminder -> MEDIUM
  |
  v
[Telegram] Inline keyboard:
  "Set reminder: Call Oleg, tomorrow 10:00 Kyiv time
   [Confirm] [Cancel]"
  |
  v
User: [Confirm]
  |
  v
[buddy-scheduler] Save reminder to reminders.json
  |
  v
[buddy-voice-ua] tts_edge.py -> "Done. Reminder set for tomorrow at 10."
  |
  v
[Telegram] Send text + voice reply
  |
  v
[Memory] Save to daily note
[Audit] Log: set_reminder, MEDIUM, approved
```

### Scenario 3: Send Email (MEDIUM)

```
User: "Send Oleg an email that the meeting is moved to Friday"
  |
  v
[buddy-security] classify: email.send -> MEDIUM
  |
  v
[buddy-comms] Look up "Oleg" in contacts.json
  -> Found: Oleg Petrenko, oleg@example.com
  |
  v
[LLM] Generate email text:
  Subject: Meeting rescheduled
  Body: "Oleg, the meeting has been rescheduled to Friday..."
  |
  v
[Telegram] Show preview + inline keyboard:
  "Email to: Oleg Petrenko (oleg@example.com)
   Subject: Meeting rescheduled
   Body: ...
   [Send] [Edit] [Cancel]"
  |
  v
User: [Send]
  |
  v
[buddy-comms] send_email.py -> SMTP -> sent
  |
  v
[Telegram] "Email sent to Oleg Petrenko"
[Memory] Save: "Sent email to Oleg about meeting reschedule"
[Audit] Log: email.send, MEDIUM, approved, success
```

### Scenario 4: Deploy Project (CRITICAL)

```
User: "Deploy buddy-web to Vercel production"
  |
  v
[buddy-security] classify: deploy -> CRITICAL
  |
  v
[Telegram] PIN request:
  "CRITICAL ACTION: Deploy
   Project: buddy-web
   Platform: Vercel (production)
   Branch: main

   Enter PIN code (60 seconds):"
  |
  v
User: "4829"
  |
  v
[buddy-security] pin_gate.py -> verify -> OK
  |
  v
[buddy-security] DELETE PIN message from chat
  |
  v
[buddy-dev] deploy_vercel.sh buddy-web --prod
  |
  v
[Telegram] "Deployed: https://buddy-web.vercel.app"
[Audit] Log: deploy, CRITICAL, approved, pin_used=true, success
```

### Scenario 5: File Access Outside Whitelist (CRITICAL)

```
User: "Find the config.ini file in D:/OtherApp/"
  |
  v
[buddy-files] file_validator.py: D:/OtherApp/ NOT in whitelist
  |
  v
[buddy-security] anti-spoofing: initiated by user message -> OK
  |
  v
[Telegram] Permission request:
  "FILE ACCESS REQUEST
   Path: D:/OtherApp/
   Action: read (search for config.ini)
   Reason: executing your task

   [Allow once] [Add to whitelist (PIN)] [Deny]"
  |
  v
User: [Allow once]
  |
  v
[buddy-files] Temporary read access to D:/OtherApp/
  -> Found: D:/OtherApp/config.ini
  |
  v
[Telegram] "Found: D:/OtherApp/config.ini (2.3 KB)"
[Audit] Log: file.read, CRITICAL, approved (temporary), success
```

---

## 8. Technology Stack

### OpenClaw Core (we don't build this)

| Component | Technology | Notes |
|-----------|-----------|-------|
| Core | TypeScript | OpenClaw main repo |
| Gateway | Telegram Bot API | Built-in adapter |
| Memory | Markdown files | Persistent + daily + deep knowledge |
| Sandbox | NemoClaw + OpenShell | Nvidia, kernel-level |
| Skills | SKILL.md + scripts | 100+ built-in |

### Our Custom Skills

| Component | Technology | Why |
|-----------|-----------|-----|
| Security scripts | Python 3.12 | bcrypt, JSON processing |
| STT | faster-whisper (small) | Local, free, ~461MB model, CPU-optimized |
| TTS | edge-tts | Microsoft Edge, free, Ukrainian voices |
| Audio conversion | pydub + ffmpeg | OGG/WAV/MP3 conversion |
| Email | smtplib (stdlib) | Gmail SMTP, zero dependencies |
| Scheduler | APScheduler | Lightweight Python scheduler |
| File validation | Python pathlib | Stdlib, path manipulation |
| Deploy scripts | Bash/Shell | Vercel CLI, Railway CLI |

### External Services (APIs)

| Service | Purpose | Cost |
|---------|---------|------|
| OpenRouter -> DeepSeek V3.2 | Main AI (chat, classify, plan, code gen) | ~$0.14/1M input, ~$0.28/1M output |
| Telegram Bot API | User interface | Free |
| DuckDuckGo (ddgs) | Web search | Free |
| Gmail SMTP | Email sending | Free (with App Password) |
| GitHub API | Git operations | Free |
| Vercel CLI | Deploy | Free tier available |
| Railway CLI | Deploy | Free tier: $5/month credit |

### Budget Estimate ($5-10/month target)

```
DeepSeek V3.2 via OpenRouter:
  ~100 requests/day x ~2K tokens avg = ~6M tokens/month
  Input:  3M tokens x $0.14/1M = $0.42
  Output: 3M tokens x $0.28/1M = $0.84
  Total LLM: ~$1.26/month

STT (faster-whisper):       $0 (local)
TTS (edge-tts):             $0 (Microsoft, free)
Embeddings:                 $0 (if using local model)
Telegram:                   $0
DuckDuckGo:                 $0
Gmail SMTP:                 $0
GitHub:                     $0
Vercel:                     $0 (free tier: 100GB bandwidth)
Railway (future):           $5/month (starter plan)
──────────────────────────────────────────
TOTAL (local):              ~$1-3/month  ✅
TOTAL (with Railway):       ~$6-8/month  ✅
```

---

## 9. Implementation Phases

### Phase 1: "Buddy Alive" (1-2 days)

**Goal:** OpenClaw installed, Telegram working, DeepSeek responding, basic identity.

**Steps:**
1. Install OpenClaw: `curl -fsSL https://openclaw.ai/install.sh | bash`
2. Create Telegram bot via @BotFather:
   - Name: Buddy Agent
   - Username: @buddy_agent_bot (or available variant)
   - Save token
3. Get OpenRouter API key from openrouter.ai
4. Configure `~/.openclaw/config.yaml`:
   - LLM: deepseek/deepseek-chat-v3.2 via OpenRouter
   - Gateway: Telegram with owner_id
   - Polling mode
5. Write templates:
   - `SOUL.md` — Buddy's character (Ukrainian, concise, cautious)
   - `IDENTITY.md` — role and capabilities
   - `USER.md` — owner info and preferences
   - `TOOLS.md` — allowed tools list
   - `BOOT.md` — startup sequence
6. Create `buddy-security` skill (basic version):
   - Only owner_id authentication
   - Basic audit logging
   - No PIN gate yet (Phase 3)
7. Test: send messages, verify Ukrainian responses, check memory
8. Init git repo, create .gitignore, first commit

**Deliverable:** Buddy responds in Telegram in Ukrainian, knows who you are, has character.

**Testing checklist:**
- [ ] Send text message -> get Ukrainian response
- [ ] Ask personal question -> Buddy says "I don't know yet, tell me about yourself"
- [ ] Send from another Telegram account -> Buddy ignores
- [ ] Check audit.jsonl -> entries are being written

---

### Phase 2: "Buddy Remembers and Hears" (2-3 days)

**Goal:** Voice messages work both ways. Long-term memory with semantic recall.

**Steps:**
1. Configure OpenClaw memory:
   - Enable daily_notes, deep_knowledge directories
   - Create initial memory/people/ files for key contacts
   - Create initial memory/projects/ files for active projects
2. Create `buddy-voice-ua` skill:
   - Install Python dependencies: `pip install faster-whisper edge-tts pydub`
   - Install ffmpeg (for audio conversion)
   - Write stt_whisper.py (Whisper small model, Ukrainian)
   - Write tts_edge.py (uk-UA-OstapNeural voice)
   - Write voice_utils.py (format conversion)
   - Wire into SKILL.md: voice message -> STT -> process -> TTS -> reply
3. Create `buddy-search` skill:
   - Route queries: memory vs web vs files
   - Test: "What did I tell you about X?" -> searches memory
4. Test voice loop end-to-end
5. Populate memory with initial data about owner

**Deliverable:** Send voice -> get voice reply in Ukrainian. "What did I say about X?" works.

**Testing checklist:**
- [ ] Send voice message -> correct transcription in Ukrainian
- [ ] Get voice reply in Ukrainian
- [ ] "What did we talk about?" -> recalls from memory
- [ ] Search the web -> returns results
- [ ] Memory persists between restarts

---

### Phase 3: "Buddy Acts Safely" (2-3 days)

**Goal:** File operations, email, reminders — all with full security.

**Steps:**
1. Install NemoClaw:
   - Follow Nvidia NemoClaw setup guide
   - Configure `policies/buddy-sandbox.yaml`
   - Test: verify sandbox blocks forbidden commands
2. Enhance `buddy-security` skill (full version):
   - Implement pin_gate.py (bcrypt, lockout, timeout)
   - Implement three-tier classification in SKILL.md
   - Add inline keyboard confirmation flow for MEDIUM
   - Add PIN request flow for CRITICAL
   - Test anti-spoofing: bot cannot self-approve
3. Create `buddy-files` skill:
   - Implement file_validator.py
   - Wire whitelist checking into all file operations
   - Test: read inside whitelist (OK), write outside (blocked)
4. Create `buddy-comms` skill:
   - Implement send_email.py
   - Create contacts.json with initial contacts
   - Create message templates
   - Test: "Send email to Oleg" -> shows preview -> confirm -> sent
5. Create `buddy-scheduler` skill:
   - Implement scheduler.py with APScheduler
   - Wire into HEARTBEAT.md
   - Test: "Remind me in 5 minutes" -> notification arrives
6. Configure HEARTBEAT.md (30-minute check cycle)

**Deliverable:** Full assistant with secure file ops, email, reminders, PIN protection.

**Testing checklist:**
- [ ] Create file in whitelist -> MEDIUM, confirm, created
- [ ] Try to delete file -> CRITICAL, PIN required
- [ ] Enter wrong PIN 3 times -> lockout 15 minutes
- [ ] Access file outside whitelist -> permission request dialog
- [ ] Send email -> preview shown, confirm, sent
- [ ] Set reminder -> fires at correct time
- [ ] NemoClaw blocks `rm -rf /` at kernel level
- [ ] Audit log captures all actions

---

### Phase 4: "Buddy Codes and Deploys" (2-3 days)

**Goal:** Create projects, git workflow, deploy to Vercel/Railway.

**Steps:**
1. Create `buddy-dev` skill:
   - Project scaffolding (Next.js, Python, static templates)
   - Code generation via DeepSeek
   - Git workflow (init, add, commit, push)
   - Deploy scripts (Vercel, Railway)
2. Install Vercel CLI: `npm i -g vercel`
3. Install Railway CLI: `npm i -g @railway/cli`
4. Create project templates in skills/buddy-dev/project_templates/
5. Test full cycle: "Create a landing page and deploy to Vercel"

**Deliverable:** "Build me a project" -> scaffolded, coded, pushed, deployed.

**Testing checklist:**
- [ ] "Create a Next.js project" -> scaffold in D:/Projects/
- [ ] "Add a homepage" -> code generated, shown, confirmed, written
- [ ] "Commit and push" -> MEDIUM, confirm, pushed to GitHub
- [ ] "Deploy to Vercel" -> CRITICAL, PIN, deployed, URL returned
- [ ] Each step requires appropriate confirmation level

---

### Phase 5: "Buddy Lives on Server" (1-2 days)

**Goal:** Deploy Buddy itself to Railway, 24/7 availability.

**Steps:**
1. Create Dockerfile:
   ```dockerfile
   # Multi-stage: OpenClaw + Python sidecar
   FROM node:22-slim AS base
   # Install OpenClaw
   # Install Python 3.12 + dependencies
   # Copy skills, templates, config
   # Expose webhook port
   ```
2. Configure Railway:
   - Create project on Railway
   - Add environment variables (API keys, tokens)
   - Attach persistent volume for memory and data
3. Switch Telegram from polling to webhook mode:
   - Update config.yaml: polling: false, webhook_url: https://buddy.railway.internal
4. Set up health checks and auto-restart
5. Configure backup: periodic copy of memory/ and data/ to GitHub repo
6. Push to GitHub, deploy to Railway
7. Test 24/7 operation

**Deliverable:** Buddy works 24/7, independent of local machine.

**Testing checklist:**
- [ ] Bot responds when local machine is off
- [ ] Memory persists between Railway restarts
- [ ] Reminders fire on schedule
- [ ] Voice messages work (Python sidecar running)
- [ ] Audit logs are preserved
- [ ] Webhook receives messages reliably

---

## 10. Budget Estimation

### Monthly Costs

| Item | Local Phase | Railway Phase |
|------|------------|---------------|
| DeepSeek V3.2 (OpenRouter) | $1-3 | $1-3 |
| faster-whisper | $0 (local CPU) | $0 (Railway CPU) |
| edge-tts | $0 | $0 |
| Telegram | $0 | $0 |
| DuckDuckGo | $0 | $0 |
| Gmail SMTP | $0 | $0 |
| Railway hosting | — | $5 (starter) |
| GitHub | $0 | $0 |
| Vercel (for deploying other projects) | $0 | $0 |
| **TOTAL** | **$1-3/month** | **$6-8/month** |

### One-Time Setup

| Item | Cost |
|------|------|
| Whisper model download (~461MB) | $0 (free, open source) |
| OpenRouter account | $0 (pay-as-you-go) |
| Telegram Bot (@BotFather) | $0 |
| Railway account | $0 (free tier includes $5 credit) |
| Gmail App Password | $0 |

---

## 11. Future Roadmap

### Phase 6: Business Automation
- `buddy-business` skill
- Google Sheets API integration (order tracking)
- Order parsing from client Telegram messages
- Supplier notification (email + messenger)
- Order status tracking

### Phase 7: Additional Gateways
- Viber integration (OpenClaw community adapter or custom)
- WhatsApp (OpenClaw built-in)
- Discord (OpenClaw built-in)

### Phase 8: Advanced Voice
- Real-time voice calls via Telegram
- WebRTC integration
- Voice-to-voice without text intermediate step

### Phase 9: Web Dashboard
- Simple web UI for:
  - Viewing audit logs
  - Managing contacts
  - Browsing memory
  - Monitoring system health
  - Configuring security settings

### Phase 10: Multi-User (if needed)
- Separate owner profiles
- Per-user security configs
- Shared vs private memory

---

## 12. Key Decisions Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | OpenClaw as base (not custom) | 70% out-of-box, 247K+ stars, MIT license | 2026-03-28 |
| 2 | DeepSeek V3.2 via OpenRouter | Cheapest capable model, 128K context, OpenAI-compatible | 2026-03-28 |
| 3 | Modular Monolith architecture | Single user, budget-conscious, easy to deploy | 2026-03-28 |
| 4 | Three-tier security (SAFE/MEDIUM/CRITICAL) | Balance between usability and safety | 2026-03-28 |
| 5 | NemoClaw + custom security | Defense in depth: kernel-level + application-level | 2026-03-28 |
| 6 | File whitelist + request permission | User wants control without being too restrictive | 2026-03-28 |
| 7 | PIN gate for CRITICAL actions (bcrypt, lockout) | Prevent unauthorized actions even if bot is compromised | 2026-03-28 |
| 8 | Ukrainian voice: faster-whisper + edge-tts | Both free, both support Ukrainian, both work locally | 2026-03-28 |
| 9 | Local-first, Railway later | Start cheap ($1-3/mo), scale when needed ($6-8/mo) | 2026-03-28 |
| 10 | Business module as future phase | Architecture supports it, but not priority for MVP | 2026-03-28 |
| 11 | Anti-spoofing: bot cannot self-approve | User specifically requested protection against unauthorized access | 2026-03-28 |

---

## Appendix A: File Tree (Complete Project Structure)

```
~/openclaw/                         # OpenClaw home directory
+-- config.yaml                     # Main OpenClaw configuration
+-- policies/
|   +-- buddy-sandbox.yaml          # NemoClaw security policy
+-- templates/
|   +-- SOUL.md                     # Character and communication style
|   +-- IDENTITY.md                 # Role and capabilities
|   +-- USER.md                     # Owner information
|   +-- TOOLS.md                    # Allowed tools
|   +-- BOOT.md                     # Startup sequence
|   +-- HEARTBEAT.md                # Periodic tasks
+-- memory/
|   +-- MEMORY.md                   # Persistent context (always loaded)
|   +-- people/                     # Contact profiles
|   |   +-- oleg-petrenko.md
|   |   +-- ...
|   +-- projects/                   # Project notes
|   |   +-- buddy-agent.md
|   |   +-- ...
|   +-- decisions/                  # Decision log
|   +-- orders/                     # Future: order history
+-- skills/
|   +-- buddy-security/
|   |   +-- SKILL.md
|   |   +-- security_config.json
|   |   +-- pin_gate.py
|   |   +-- audit_log.py
|   +-- buddy-voice-ua/
|   |   +-- SKILL.md
|   |   +-- stt_whisper.py
|   |   +-- tts_edge.py
|   |   +-- voice_utils.py
|   |   +-- requirements.txt
|   +-- buddy-files/
|   |   +-- SKILL.md
|   |   +-- file_validator.py
|   +-- buddy-comms/
|   |   +-- SKILL.md
|   |   +-- send_email.py
|   |   +-- contacts.json
|   |   +-- message_templates/
|   |       +-- meeting_reschedule.md
|   |       +-- order_confirmation.md
|   |       +-- general_message.md
|   +-- buddy-dev/
|   |   +-- SKILL.md
|   |   +-- deploy_railway.sh
|   |   +-- deploy_vercel.sh
|   |   +-- project_templates/
|   |       +-- nextjs/
|   |       +-- python-api/
|   |       +-- static-site/
|   +-- buddy-scheduler/
|   |   +-- SKILL.md
|   |   +-- scheduler.py
|   |   +-- reminders.json
|   +-- buddy-search/
|   |   +-- SKILL.md
|   |   +-- search_router.py
|   +-- buddy-business/             # Future
|       +-- SKILL.md
|       +-- google_sheets.py
|       +-- order_parser.py
|       +-- supplier_notify.py
+-- data/
|   +-- buddy.db                    # SQLite (if needed for structured data)
|   +-- audit.jsonl                 # Audit log
|   +-- pin_lockout.json            # PIN lockout state
|   +-- temp/                       # Temporary files (voice, downloads)
+-- workspace/                      # OpenClaw default workspace
```

## Appendix B: Environment Variables

```bash
# .env (NEVER commit to git)

# LLM
OPENROUTER_API_KEY=sk-or-...

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_OWNER_ID=123456789

# Email (Gmail)
SMTP_USER=your.email@gmail.com
SMTP_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Security
BUDDY_PIN_HASH=$2b$12$...  # bcrypt hash of your PIN

# Future: Google Sheets
# GOOGLE_SHEETS_CREDENTIALS=base64_encoded_json
# GOOGLE_SHEETS_SPREADSHEET_ID=...

# Future: Railway
# RAILWAY_TOKEN=...

# Future: Vercel
# VERCEL_TOKEN=...
```

## Appendix C: OpenClaw Installation Quick Reference

```bash
# 1. Install OpenClaw
curl -fsSL https://openclaw.ai/install.sh | bash

# 2. Navigate to OpenClaw directory
cd ~/openclaw

# 3. Start onboarding wizard (configures gateway, LLM)
openclaw init

# 4. Or manually edit config
nano ~/.openclaw/config.yaml

# 5. Install NemoClaw (security sandbox)
# Follow: https://github.com/NVIDIA/NemoClaw

# 6. Install Python dependencies for voice
pip install faster-whisper edge-tts pydub apscheduler bcrypt

# 7. Install system dependencies
# Windows: install ffmpeg (https://ffmpeg.org/download.html)
# Add to PATH

# 8. Create custom skills
openclaw skills create buddy-security
openclaw skills create buddy-voice-ua
openclaw skills create buddy-files
openclaw skills create buddy-comms
openclaw skills create buddy-dev
openclaw skills create buddy-scheduler
openclaw skills create buddy-search

# 9. Start Buddy
openclaw start

# 10. Check status
openclaw status

# 11. View logs
openclaw logs

# 12. Stop
openclaw stop
```

---

*End of Design Specification*
