---
name: buddy-search
description: Routes search queries to web, memory, or file system.
trigger:
  - on_intent: search, find, lookup
priority: 50
tools:
  - web_search
  - file_read
  - shell
---

## Routing

### Memory: "що я казав про", past conversations, personal facts
### Web: current events, docs, how-to, external info
### Files: "знайди файл", content search in whitelist dirs
### Combined: when unsure, check memory -> files -> web

All searches are SAFE level.

## Script

`search.py <query> [source: auto|memory|files|web]`

Returns JSON: `{"query": "...", "source": "memory|files|web|combined", "count": N, "results": [...]}`
