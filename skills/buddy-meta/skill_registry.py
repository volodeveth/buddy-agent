#!/usr/bin/env python3
"""CRUD operations for generated skill registry.
Commands: list, uninstall, reinstall."""

import sys
import io
import json
import shutil
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
GENERATED_DIR = SKILL_DIR / "generated"
UNINSTALLED_DIR = GENERATED_DIR / "_uninstalled"
REGISTRY_PATH = GENERATED_DIR / "skill_registry.json"


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "generated_skills": [], "config": {}}


def _save_registry(registry: dict) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def action_list() -> dict:
    """List all generated skills with status."""
    registry = _load_registry()
    skills = []
    for s in registry["generated_skills"]:
        skills.append({
            "id": s["id"],
            "name": s["name"],
            "description": s.get("description", ""),
            "status": s["status"],
            "priority": s.get("priority", 35),
            "created_at": s["created_at"],
            "model_used": s.get("model_used", ""),
            "sessions_used": s.get("sessions_used", 0),
            "last_used": s.get("last_used"),
        })

    active = [s for s in skills if s["status"] == "active"]
    uninstalled = [s for s in skills if s["status"] == "uninstalled"]

    return {
        "status": "success",
        "total": len(skills),
        "active": len(active),
        "uninstalled": len(uninstalled),
        "skills": skills,
    }


def action_uninstall(name: str) -> dict:
    """Uninstall a generated skill. Moves files to _uninstalled/."""
    registry = _load_registry()

    entry = None
    for s in registry["generated_skills"]:
        if s["name"] == name and s["status"] == "active":
            entry = s
            break

    if not entry:
        return {"status": "error", "message": f"Active skill not found: {name}"}

    # Move skill directory
    src = GENERATED_DIR / name
    if src.exists():
        UNINSTALLED_DIR.mkdir(parents=True, exist_ok=True)
        dst = UNINSTALLED_DIR / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src), str(dst))

    entry["status"] = "uninstalled"
    entry["uninstalled_at"] = datetime.now().isoformat()
    _save_registry(registry)

    return {
        "status": "success",
        "message": f"Навик {name} деінстальовано",
        "name": name,
        "restore_command": f'python skill_registry.py reinstall "{name}"',
    }


def action_reinstall(name: str) -> dict:
    """Reinstall a previously uninstalled skill."""
    registry = _load_registry()

    entry = None
    for s in registry["generated_skills"]:
        if s["name"] == name and s["status"] == "uninstalled":
            entry = s
            break

    if not entry:
        return {"status": "error", "message": f"Uninstalled skill not found: {name}"}

    # Move skill directory back
    src = UNINSTALLED_DIR / name
    dst = GENERATED_DIR / name
    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src), str(dst))
    elif not dst.exists():
        return {"status": "error", "message": f"Skill files not found for: {name}"}

    entry["status"] = "active"
    entry["reinstalled_at"] = datetime.now().isoformat()
    _save_registry(registry)

    return {
        "status": "success",
        "message": f"Навик {name} відновлено",
        "name": name,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: skill_registry.py <list|uninstall|reinstall> [name]"
        }))
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        result = action_list()

    elif command == "uninstall":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: skill_registry.py uninstall <name>"}))
            sys.exit(1)
        result = action_uninstall(sys.argv[2])

    elif command == "reinstall":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: skill_registry.py reinstall <name>"}))
            sys.exit(1)
        result = action_reinstall(sys.argv[2])

    else:
        result = {"error": f"Unknown command: {command}. Use: list, uninstall, reinstall"}

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
