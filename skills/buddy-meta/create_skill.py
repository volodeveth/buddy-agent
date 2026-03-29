#!/usr/bin/env python3
"""Main orchestrator for self-extending agent.
Receives a need from Gemini Flash, delegates to MiniMax M2.7,
validates, saves, and registers new skills."""

import sys
import io
import json
import os
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent
GENERATED_DIR = SKILL_DIR / "generated"
REGISTRY_PATH = GENERATED_DIR / "skill_registry.json"
TEMPLATES_DIR = SKILL_DIR / "templates"

# Hardcoded safety boundaries
IMMUTABLE_SKILLS = {"buddy-security", "buddy-meta", "buddy-files"}
MAX_GENERATED_PRIORITY = 40
MAX_GENERATED_SKILLS = 20
MAX_SCRIPT_LINES = 200


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "generated_skills": [], "config": {}}


def _save_registry(registry: dict) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def _next_id(registry: dict) -> str:
    existing = [s["id"] for s in registry["generated_skills"]]
    n = 1
    while f"gen_{n:03d}" in existing:
        n += 1
    return f"gen_{n:03d}"


def _skill_exists(name: str) -> bool:
    """Check if skill name already exists (core or generated)."""
    core_dir = PROJECT_ROOT / "skills" / name
    gen_dir = GENERATED_DIR / name
    return core_dir.exists() or gen_dir.exists()


def _validate_skill_name(name: str) -> str | None:
    """Return error message if name is invalid, None if OK."""
    if not name.startswith("buddy-"):
        return f"Skill name must start with 'buddy-': {name}"
    if name in IMMUTABLE_SKILLS:
        return f"Cannot create skill with reserved name: {name}"
    if _skill_exists(name):
        return f"Skill already exists: {name}"
    if not name.replace("-", "").replace("_", "").isalnum():
        return f"Skill name must be alphanumeric with dashes: {name}"
    return None


def action_create(need: str, context: str = "") -> dict:
    """Create a new skill. Calls MiniMax, validates, saves."""
    registry = _load_registry()

    # Check limits
    active = [s for s in registry["generated_skills"] if s["status"] == "active"]
    if len(active) >= MAX_GENERATED_SKILLS:
        return {"status": "error", "message": f"Maximum {MAX_GENERATED_SKILLS} generated skills reached. Uninstall unused skills first."}

    # Import generate_with_model (same directory)
    sys.path.insert(0, str(SKILL_DIR))
    from generate_with_model import generate_skill
    from validate_code import validate

    # Call MiniMax (with up to 3 self-correction attempts)
    max_attempts = 3
    last_errors = None
    skill_def = None

    for attempt in range(1, max_attempts + 1):
        skill_def = generate_skill(need, context, correction_errors=last_errors)

        if "error" in skill_def:
            return {"status": "error", "message": skill_def["error"], "attempt": attempt}

        # Validate skill name
        skill_name = skill_def.get("skill_name", "")
        name_error = _validate_skill_name(skill_name)
        if name_error:
            last_errors = [name_error]
            continue

        # Validate priority
        priority = skill_def.get("priority", 35)
        if priority > MAX_GENERATED_PRIORITY:
            skill_def["priority"] = MAX_GENERATED_PRIORITY

        # Validate generated code
        script_code = skill_def.get("script_code", "")
        if not script_code:
            last_errors = ["No script_code in response"]
            continue

        validation = validate(script_code)
        if not validation["valid"]:
            last_errors = validation["errors"]
            continue

        # All checks passed
        break
    else:
        # All attempts failed
        return {
            "status": "error",
            "message": f"Code generation failed after {max_attempts} attempts",
            "last_errors": last_errors,
        }

    # --- Save skill files ---
    skill_name = skill_def["skill_name"]
    script_name = skill_def.get("script_name", f"{skill_name.replace('buddy-', '')}.py")
    skill_dir = GENERATED_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Write SKILL.md
    skill_md_template = (TEMPLATES_DIR / "skill_template.md").read_text(encoding="utf-8")
    skill_md = skill_md_template.replace("{{SKILL_NAME}}", skill_name)
    skill_md = skill_md.replace("{{DESCRIPTION}}", skill_def.get("description", ""))
    skill_md = skill_md.replace("{{INTENTS}}", skill_def.get("intents", ""))
    skill_md = skill_md.replace("{{PRIORITY}}", str(skill_def.get("priority", 35)))
    skill_md = skill_md.replace("{{INSTRUCTIONS}}", skill_def.get("instructions", ""))

    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Write Python script
    (skill_dir / script_name).write_text(script_code, encoding="utf-8")

    # --- Register ---
    entry = {
        "id": _next_id(registry),
        "name": skill_name,
        "description": skill_def.get("description", ""),
        "purpose": need,
        "context": context,
        "priority": skill_def.get("priority", 35),
        "created_at": datetime.now().isoformat(),
        "model_used": skill_def.get("model_used", "unknown"),
        "tokens_input": skill_def.get("tokens_input", 0),
        "tokens_output": skill_def.get("tokens_output", 0),
        "files": ["SKILL.md", script_name],
        "path": str(skill_dir.relative_to(PROJECT_ROOT)),
        "status": "active",
        "validation_result": validation,
        "attempts": attempt,
        "approval_pin_used": True,
        "sessions_used": 0,
        "last_used": None,
    }
    registry["generated_skills"].append(entry)
    _save_registry(registry)

    # Build workspace path for inline execution
    workspace_path = Path.home() / ".openclaw" / "workspace" / entry["path"] / script_name

    return {
        "status": "created",
        "skill_name": skill_name,
        "description": skill_def.get("description", ""),
        "path": str(skill_dir),
        "files": ["SKILL.md", script_name],
        "validation": validation,
        "available_in": "next_session",
        "inline_exec": f"python {workspace_path}",
        "model_used": entry["model_used"],
        "tokens_used": {
            "input": entry["tokens_input"],
            "output": entry["tokens_output"],
        },
        "attempts": attempt,
    }


def action_list() -> dict:
    """List all generated skills."""
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
        })
    return {"status": "success", "count": len(skills), "skills": skills}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Buddy Meta — Skill Creator")
    parser.add_argument("--action", required=True, choices=["create", "list"],
                        help="Action to perform")
    parser.add_argument("--need", default="", help="What the user needs (for create)")
    parser.add_argument("--context", default="", help="Original user message (for create)")

    args = parser.parse_args()

    if args.action == "create":
        if not args.need:
            print(json.dumps({"status": "error", "message": "--need is required for create"}))
            sys.exit(1)
        result = action_create(args.need, args.context)

    elif args.action == "list":
        result = action_list()

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
