#!/usr/bin/env python3
"""
Search Router Skill - Пошук в пам'яті, файлах або інтернеті
"""
import sys
import io
import json
import pathlib
import urllib.request
import urllib.parse
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SKILL_DIR = pathlib.Path(__file__).parent.resolve()

def search_memory(query: str) -> list[dict]:
    """Шукає в файлах папки memory/"""
    results = []
    memory_dir = SKILL_DIR.parent / "memory"
    if memory_dir.exists():
        for file in memory_dir.rglob("*"):
            if file.is_file():
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                    if query.lower() in content.lower():
                        results.append({
                            "source": "memory",
                            "file": str(file.name),
                            "match": content[:200].replace('\n', ' ')
                        })
                except Exception:
                    pass
    return results

def search_files(query: str) -> list[dict]:
    """Шукає файли в робочих директоріях"""
    results = []
    dirs = ["D:/BuddyWorkspace", "D:/Projects", "D:/Documents"]
    for directory in dirs:
        dir_path = pathlib.Path(directory)
        if dir_path.exists():
            for file in dir_path.rglob("*"):
                if file.is_file() and query.lower() in file.name.lower():
                    results.append({
                        "source": "files",
                        "path": str(file.parent),
                        "name": file.name
                    })
    return results

def search_web(query: str) -> list[dict]:
    """Шукає в інтернеті через DuckDuckGo API"""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            results = []
            for topic in data.get("RelatedTopics", [])[:5]:
                if "Text" in topic:
                    results.append({
                        "source": "web",
                        "title": topic.get("Text", "")[:100],
                        "url": topic.get("URL", "")
                    })
            if not results and data.get("AbstractText"):
                results.append({
                    "source": "web",
                    "title": data.get("AbstractText", "")[:200],
                    "url": data.get("AbstractURL", "")
                })
            return results
    except Exception as e:
        return [{"source": "web", "error": str(e)}]

def search_auto(query: str) -> dict:
    """Автоматичний вибір джерела пошуку"""
    q = query.lower()
    keywords_mem = ["память", "згадати", "memory", "remember", "раніше", "було"]
    keywords_file = ["файл", "документ", "file", "folder", "диск", "де"]
    keywords_web = ["інтернет", "web", "новини", "online", "google", "що таке"]
    
    results = {"query": query, "mode": "auto", "results": []}
    if any(k in q for k in keywords_mem):
        results["results"].extend(search_memory(query))
    if any(k in q for k in keywords_file):
        results["results"].extend(search_files(query))
    if any(k in q for k in keywords_web) or not any(k in q for k in keywords_mem + keywords_file):
        results["results"].extend(search_web(query))
    return results

def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    search_type = sys.argv[2] if len(sys.argv) > 2 else "auto"
    
    if not query:
        print(json.dumps({"error": "Вкажіть запит для пошуку"}, ensure_ascii=True))
        return
    
    try:
        if search_type == "memory":
            result = {"query": query, "mode": "memory", "results": search_memory(query)}
        elif search_type == "files":
            result = {"query": query, "mode": "files", "results": search_files(query)}
        elif search_type == "web":
            result = {"query": query, "mode": "web", "results": search_web(query)}
        elif search_type == "auto":
            result = search_auto(query)
        else:
            result = {"error": f"Невідомий тип пошуку: {search_type}"}
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=True))

if __name__ == "__main__":
    main()