# Buddy Agent — Project Instructions

## Project Overview

Personal AI assistant "Buddy" built on **OpenClaw** framework, using **DeepSeek V3.2** via **OpenRouter** as LLM. Communicates via **Telegram** (text + voice in Ukrainian). Three-tier security system (SAFE/MEDIUM/CRITICAL + PIN gate).

## Design Specification

**IMPORTANT:** Full design doc with all architecture decisions, file structures, code samples, security rules, configurations, data flows, and implementation phases is at:

```
docs/superpowers/specs/2026-03-28-buddy-agent-design.md
```

**Always read this file before making any implementation decisions.** It contains:
- Complete architecture diagram (OpenClaw core + 8 custom skills)
- Security layer details (NemoClaw + buddy-security)
- All configuration files (config.yaml, sandbox policy, templates)
- All custom skill SKILL.md contents and Python scripts
- 5 data flow scenarios with step-by-step flows
- Implementation phases with testing checklists
- Budget estimation and technology stack
- Complete file tree (Appendix A)
- Environment variables list (Appendix B)
- OpenClaw installation commands (Appendix C)

## Architecture Summary

```
OpenClaw Core (built-in): Gateway (Telegram), LLM (DeepSeek), Memory, Sandbox (NemoClaw)
     |
Custom Skills (we build):
  buddy-security    — PIN gate, 3-tier permissions, audit log (priority 100)
  buddy-voice-ua    — STT (faster-whisper) + TTS (edge-tts), Ukrainian
  buddy-files       — Whitelist file system enforcement
  buddy-comms       — Email (SMTP), contacts management
  buddy-dev         — Git workflow, deploy (Vercel/Railway)
  buddy-scheduler   — Reminders, cron tasks
  buddy-search      — Search router (web/memory/files)
  buddy-utils       — Shared utilities (env_loader)
  buddy-business    — [FUTURE] Orders, Google Sheets
```

## Security Rules (non-negotiable)

- **SAFE:** chat, search, read whitelisted files — no confirmation
- **MEDIUM:** write files, send email, git commit — inline keyboard confirmation
- **CRITICAL:** delete files, shell exec, deploy, access outside whitelist — PIN + 60s timeout
- File whitelist: `D:/BuddyWorkspace`, `D:/Projects`, `D:/Documents`
- Sensitive files (`*.env`, `*.key`, `*.pem`, `*secret*`, `*credential*`) — always CRITICAL
- PIN: bcrypt hash, 3 max attempts, 15-min lockout
- Anti-spoofing: bot CANNOT self-approve actions
- Every action logged to `audit.jsonl`

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | OpenClaw (TypeScript) |
| LLM | DeepSeek V3.2 via OpenRouter |
| Gateway | Telegram Bot API |
| STT | faster-whisper (Python, local, free) |
| TTS | edge-tts (Microsoft, free, Ukrainian) |
| Sandbox | NemoClaw (Nvidia OpenShell) |
| Email | Gmail SMTP |
| Scheduler | APScheduler (Python) |
| Security | bcrypt (PIN), custom audit log |

## Implementation Phases

1. **Buddy Alive** ✅ — OpenClaw + Telegram + DeepSeek + identity templates
2. **Remembers & Hears** ✅ — Voice UA + memory system
3. **Acts Safely** ✅ — Full security + files + email + reminders
4. **Codes & Deploys** 🔄 — Git + buddy-meta self-extending agent
5. **On Server** ⏳ — Railway 24/7 deployment
6. **Future:** Business orders, Viber, voice calls

## Code Standards

- Python scripts in skills: Python 3.12, type hints, JSON output to stdout
- SKILL.md files: YAML frontmatter + Markdown instructions
- All secrets in environment variables, never hardcoded
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
- Ukrainian in user-facing text, English in code/logs
- Every action must pass through buddy-security before execution

## Key Directories

```
~/openclaw/                    — OpenClaw home
~/openclaw/skills/             — Custom skills (buddy-*)
~/openclaw/templates/          — SOUL.md, IDENTITY.md, etc.
~/openclaw/memory/             — Persistent memory
~/openclaw/data/               — Runtime data (audit, temp)
~/openclaw/policies/           — NemoClaw sandbox policies
D:/BuddyWorkspace/            — Primary workspace
D:/Projects/                   — Development projects
D:/Documents/                  — Documents
D:/Myapps/buddy agent/         — This repo (design docs, git)
```
