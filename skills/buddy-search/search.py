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
_CONFIG_PATH = PROJECT_ROOT / "skills" / "buddy-security" / "security_config.json"


def _load_whitelist() -> list[str]:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f).get("whitelist_paths", [])
    return ["D:/BuddyWorkspace", "D:/Projects", "D:/Documents"]


def search_memory(query: str) -> list[dict]:
    results = []
    if not MEMORY_DIR.exists():
        return results
    q = query.lower()
    for f in MEMORY_DIR.rglob("*.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if q in content.lower():
                for line in content.splitlines():
                    if q in line.lower():
                        results.append({"source": "memory", "file": f.name, "match": line.strip()[:200]})
                        break
        except OSError:
            continue
    return results


def search_files(query: str) -> list[dict]:
    results = []
    q = query.lower()
    for directory in _load_whitelist():
        dp = pathlib.Path(directory)
        if not dp.exists():
            continue
        for f in dp.rglob("*"):
            if not f.is_file():
                continue
            if q in f.name.lower():
                results.append({"source": "files", "path": str(f), "name": f.name, "match_type": "filename"})
            elif f.suffix in (".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".csv"):
                try:
                    if f.stat().st_size > 1_000_000:
                        continue
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if q in content.lower():
                        for line in content.splitlines():
                            if q in line.lower():
                                results.append({"source": "files", "path": str(f), "name": f.name, "match_type": "content", "match": line.strip()[:200]})
                                break
                except OSError:
                    continue
            if len(results) >= 20:
                break
        if len(results) >= 20:
            break
    return results


def search_web(query: str) -> list[dict]:
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "BuddyAgent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            if data.get("AbstractText"):
                results.append({"source": "web", "title": data["AbstractText"][:200], "url": data.get("AbstractURL", "")})
            for topic in data.get("RelatedTopics", [])[:5]:
                if "Text" in topic:
                    results.append({"source": "web", "title": topic["Text"][:150], "url": topic.get("FirstURL", "")})
            return results
    except Exception as e:
        return [{"source": "web", "error": str(e)}]


def classify_intent(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ["пам'ять", "згадати", "раніше", "казав", "було", "memory", "remember"]):
        return "memory"
    if any(k in q for k in ["файл", "документ", "знайди", "file", "folder", "диск", "шлях"]):
        return "files"
    if any(k in q for k in ["інтернет", "web", "новини", "що таке", "online", "як зробити", "how to"]):
        return "web"
    return "auto"


def search(query: str, source: str = "auto") -> dict:
    if source == "auto":
        source = classify_intent(query)
    if source == "memory":
        results = search_memory(query)
    elif source == "files":
        results = search_files(query)
    elif source == "web":
        results = search_web(query)
    else:
        results = search_memory(query)
        if not results:
            results = search_files(query)
        if not results:
            results = search_web(query)
        source = "combined"
    return {"query": query, "source": source, "count": len(results), "results": results}


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: search.py <query> [source: auto|memory|files|web]"}))
        sys.exit(1)
    query = sys.argv[1]
    source = sys.argv[2] if len(sys.argv) > 2 else "auto"
    print(json.dumps(search(query, source), ensure_ascii=True))


if __name__ == "__main__":
    main()
