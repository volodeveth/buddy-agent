# Buddy Agent

A self-extending personal AI assistant built on the [OpenClaw](https://github.com/openclaw) framework. Communicates via Telegram (text + voice in Ukrainian). Features a dual-LLM architecture where **Gemini 2.0 Flash** dispatches tasks and **MiniMax M2.7** autonomously generates new capabilities.

## Key Features

- **Voice interface** — STT via faster-whisper, TTS via edge-tts (Microsoft). Defaults to Ukrainian, configurable to any language supported by Whisper
- **Self-extending** — the agent creates, tests, and fixes its own skills using MiniMax M2.7
- **3-tier security** — SAFE / MEDIUM / CRITICAL actions with PIN gate and audit logging
- **Modular skill system** — each capability is an independent skill with its own SKILL.md and Python scripts
- **Persistent memory** — remembers conversations, people, preferences across sessions
- **Sandboxed execution** — NemoClaw policy restricts filesystem, network, and shell access

## Architecture

```
User (Telegram) ──> OpenClaw Gateway ──> Gemini 2.0 Flash (Dispatcher)
                                              │
                         ┌────────────────────┴────────────────────┐
                         │                                         │
                  Existing Skills                          Need new skill?
                  (exec Python scripts)                          │
                                                          create_skill.py
                                                                 │
                                                          MiniMax M2.7
                                                          (via OpenRouter)
                                                                 │
                                                          validate_code.py
                                                          (AST safety check)
                                                                 │
                                                          Save + Register
                                                          Execute immediately
```

### Dual LLM Roles

| Model | Role | Responsibility |
|-------|------|----------------|
| **Gemini 2.0 Flash** | Dispatcher | Handles 95% of work: chat, classify intents, call existing tools. Only describes WHAT is needed for new skills. |
| **MiniMax M2.7** | Engineer | Designs architecture, writes code, self-reviews. Called via OpenRouter API when new capabilities are needed. |

## Skills

### Core Skills (built-in)

| Skill | Priority | Description |
|-------|----------|-------------|
| **buddy-security** | 100 | PIN gate, 3-tier permissions (SAFE/MEDIUM/CRITICAL), bcrypt PIN hash, audit log, lockout after 3 failed attempts |
| **buddy-files** | 90 | Filesystem access with whitelist enforcement. Only allows access to designated workspace paths |
| **buddy-voice-ua** | 80 | Speech-to-text (faster-whisper, medium model) and text-to-speech (edge-tts). Language defaults to Ukrainian (`uk`), configurable in `stt_whisper.py` (`LANGUAGE` constant) and TTS voice in `tts_edge.py` |
| **buddy-comms** | 70 | Send emails (Gmail SMTP), Telegram messages (direct Bot API), contact lookup |
| **buddy-dev** | 60 | Development tools (stub — to be built by agent) |
| **buddy-scheduler** | 50 | Reminders and scheduled tasks with APScheduler |
| **buddy-search** | 50 | Search routing (stub — to be built by agent) |
| **buddy-meta** | 30 | Self-extending engine: creates, reads, updates, and manages generated skills |

### Generated Skills (created by the agent)

Generated skills live in `skills/buddy-meta/generated/` and are isolated from core skills. They have a maximum priority of 40 (always below core skills) and are limited to 200 lines of code.

Currently generated:

| Skill | Description | Model |
|-------|-------------|-------|
| buddy-exchange-rates | UAH/USD/EUR exchange rates from PrivatBank API | MiniMax M2.7 |
| buddy-find | Smart search router: memory, local files, web (DuckDuckGo) | MiniMax M2.7 |
| buddy-dev-helper | Dev tools: project scaffolding, dependency listing, git status | MiniMax M2.7 |

## Security Model

### Three-Tier Permission System

| Level | Actions | Confirmation |
|-------|---------|-------------|
| **SAFE** | Chat, search, read whitelisted files | None |
| **MEDIUM** | Write files, send email, git commit, uninstall skills | Inline keyboard confirmation |
| **CRITICAL** | Delete files, shell exec, deploy, create/update skills, access outside whitelist | PIN + 60s timeout |

### Safety Boundaries

- **PIN gate**: bcrypt-hashed PIN, 3 max attempts, 15-minute lockout
- **File whitelist**: Only `D:/BuddyWorkspace`, `D:/Projects`, `D:/Documents`
- **Sensitive files**: `*.env`, `*.key`, `*.pem`, `*secret*`, `*credential*` always require CRITICAL
- **Audit log**: Every action logged to `data/audit.jsonl`
- **Anti-spoofing**: Bot cannot self-approve actions
- **Sandbox policy**: NemoClaw restricts network, filesystem, and shell access

### Self-Extension Safety (4 Layers)

| Layer | Protection |
|-------|-----------|
| **Approval Gate** | Creating/updating any skill requires CRITICAL level (PIN) |
| **Capability Boundaries** | Immutable skills (security, meta, files), max priority 40, max 20 generated skills, max 200 lines |
| **Code Review** | AST-based static analysis: forbidden imports (subprocess, socket, ctypes...), forbidden patterns (eval, exec, file writes, non-GET HTTP), domain whitelist |
| **Reversibility** | Uninstall/reinstall with full audit trail, files preserved in `_uninstalled/` |

## Self-Extension (buddy-meta)

The agent can autonomously create new skills when it encounters a request beyond its current capabilities.

### How It Works

1. Gemini Flash detects a need for a new capability
2. Gemini describes the need in natural language (does NOT write code)
3. `create_skill.py` sends the need to MiniMax M2.7 via OpenRouter
4. MiniMax generates: skill name, description, SKILL.md, complete Python script
5. `validate_code.py` performs AST-based safety analysis
6. If invalid: errors sent back to MiniMax for self-correction (up to 3 attempts)
7. If valid: saved to `generated/`, registered in `skill_registry.json`
8. Script executed immediately via inline exec
9. Full skill integration on next session restart

### Available Actions

```bash
# Create a new skill
python create_skill.py --action create \
  --need "What the skill should do" \
  --context "Original user message"

# Read source code of a generated skill
python create_skill.py --action read --name "buddy-skill-name"

# Update/fix a generated skill
python create_skill.py --action update \
  --name "buddy-skill-name" \
  --need "Description of what to fix or change"

# List all generated skills
python create_skill.py --action list

# Uninstall a skill (preserves files)
python skill_registry.py uninstall "buddy-skill-name"

# Reinstall a previously uninstalled skill
python skill_registry.py reinstall "buddy-skill-name"
```

### Code Validation Rules

Generated scripts must follow strict rules enforced by `validate_code.py`:

- **Allowed imports**: json, sys, io, pathlib, urllib, datetime, re, math, hashlib, base64, collections, csv, os.path, typing, dataclasses, enum, functools, itertools
- **Forbidden imports**: subprocess, shutil, ctypes, cffi, socket, multiprocessing, threading, signal, importlib
- **Forbidden operations**: eval(), exec(), compile(), file writes, file deletes, POST/PUT/DELETE requests
- **Network**: Only GET requests via urllib to whitelisted domains
- **Structure**: Must have `main()`, `json.dumps` output, `sys.argv` input, `__name__ == "__main__"` guard
- **Size**: Maximum 200 lines

## Project Structure

```
buddy-agent/
├── skills/
│   ├── buddy-security/        # PIN gate, audit log, security config
│   ├── buddy-files/           # File access with whitelist
│   ├── buddy-voice-ua/        # Ukrainian STT + TTS
│   ├── buddy-comms/           # Email, Telegram, contacts
│   ├── buddy-dev/             # Dev tools (stub)
│   ├── buddy-scheduler/       # Reminders, cron tasks
│   ├── buddy-search/          # Search routing (stub)
│   └── buddy-meta/            # Self-extending engine
│       ├── create_skill.py    # Orchestrator: create/read/update/list
│       ├── generate_with_model.py  # MiniMax M2.7 via OpenRouter
│       ├── validate_code.py   # AST safety analysis
│       ├── skill_registry.py  # Uninstall/reinstall management
│       ├── templates/         # System prompt, skill/script templates
│       └── generated/         # All generated skills (isolated)
├── templates/                 # SOUL.md, IDENTITY.md (agent personality)
├── memory/                    # Persistent memory (people, preferences)
├── policies/                  # NemoClaw sandbox policy
├── data/                      # Runtime data (audit log, temp)
└── docs/                      # Design specs
```

## Setup

### Prerequisites

- Python 3.12+
- [OpenClaw](https://github.com/openclaw) framework installed
- Telegram Bot Token
- OpenRouter API key (for MiniMax M2.7)
- Gmail App Password (for email)

### Environment Variables

Create a `.env` file in the project root:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_OWNER_ID=your_telegram_id

# LLM
OPENROUTER_API_KEY=your_openrouter_key

# Email
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# Security
BUDDY_PIN_HASH=$2b$12$...  # bcrypt hash of your PIN
```

### Installation

```bash
# Clone the repository
git clone https://github.com/volodeveth/buddy-agent.git
cd buddy-agent

# Install Python dependencies
pip install faster-whisper edge-tts bcrypt apscheduler

# Set up OpenClaw workspace
# Copy skills to ~/.openclaw/workspace/skills/
# Copy templates to ~/.openclaw/workspace/templates/
# Copy policies to ~/.openclaw/workspace/policies/

# Start OpenClaw with Telegram gateway
openclaw start --gateway telegram
```

### Sync Script

Use `sync.sh` to sync project files to the OpenClaw workspace:

```bash
bash sync.sh
```

## Tech Stack

| Component | Technology | Cost |
|-----------|-----------|------|
| Framework | OpenClaw (TypeScript) | Free |
| Dispatcher LLM | Gemini 2.0 Flash | ~$0.10/1M tokens |
| Engineer LLM | MiniMax M2.7 (via OpenRouter) | ~$0.15/1M tokens |
| Telegram Gateway | Telegram Bot API | Free |
| STT | faster-whisper (local) | Free |
| TTS | edge-tts (Microsoft) | Free |
| Email | Gmail SMTP | Free |
| Security | bcrypt, custom audit | Free |
| **Total** | | **$1-6/month** |

## Roadmap

- [x] **Phase 1-2**: Core agent + voice + memory
- [x] **Phase 3**: Security + files + email + scheduler
- [x] **Phase 4**: Self-extending engine (buddy-meta)
- [ ] **Phase 5**: Agent builds business module, search, dev tools via buddy-meta
- [ ] **Phase 6**: Multi-user support (owner vs client roles)
- [ ] **Phase 7+**: Railway deployment, Google Sheets, Viber, web dashboard

## License

MIT
