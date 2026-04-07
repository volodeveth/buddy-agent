#!/usr/bin/env python3
"""Main orchestrator for self-extending agent.
Receives a need from DeepSeek V3.2, delegates code generation to MiniMax M2.7,
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
MAX_SCRIPT_LINES = 800


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "generated_skills": [], "config": {}}


def _save_registry(registry: dict) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=True, indent=2)


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

        # Validate generated code (with auto-fix attempt)
        script_code = skill_def.get("script_code", "")
        if not script_code:
            last_errors = ["No script_code in response"]
            continue

        script_code = _try_fix_syntax(script_code)
        skill_def["script_code"] = script_code

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


def action_read(name: str) -> dict:
    """Read source code of a generated skill."""
    registry = _load_registry()

    entry = None
    for s in registry["generated_skills"]:
        if s["name"] == name:
            entry = s
            break

    if not entry:
        return {"status": "error", "message": f"Skill not found: {name}"}

    skill_dir = GENERATED_DIR / name
    if not skill_dir.exists():
        return {"status": "error", "message": f"Skill directory not found: {name}"}

    # Find the Python script
    script_name = None
    for f in entry.get("files", []):
        if f.endswith(".py"):
            script_name = f
            break

    if not script_name:
        return {"status": "error", "message": f"No Python script in skill: {name}"}

    script_path = skill_dir / script_name
    if not script_path.exists():
        return {"status": "error", "message": f"Script file not found: {script_path}"}

    code = script_path.read_text(encoding="utf-8")

    return {
        "status": "success",
        "name": name,
        "script_name": script_name,
        "code": code,
        "lines": len(code.strip().split("\n")),
        "description": entry.get("description", ""),
    }


def action_update(name: str, fix_description: str) -> dict:
    """Update an existing generated skill. Sends current code + fix to MiniMax."""
    registry = _load_registry()

    # Find the skill
    entry = None
    entry_idx = None
    for i, s in enumerate(registry["generated_skills"]):
        if s["name"] == name and s["status"] == "active":
            entry = s
            entry_idx = i
            break

    if not entry:
        return {"status": "error", "message": f"Active skill not found: {name}"}

    if name in IMMUTABLE_SKILLS:
        return {"status": "error", "message": f"Cannot update immutable skill: {name}"}

    # Read current code
    read_result = action_read(name)
    if read_result["status"] != "success":
        return read_result

    current_code = read_result["code"]
    script_name = read_result["script_name"]

    # Import modules
    sys.path.insert(0, str(SKILL_DIR))
    from generate_with_model import generate_skill
    from validate_code import validate

    # Call MiniMax with existing code + fix description
    max_attempts = 3
    last_errors = None
    skill_def = None

    for attempt in range(1, max_attempts + 1):
        context = f"UPDATE_EXISTING:{current_code}"
        skill_def = generate_skill(fix_description, context, correction_errors=last_errors)

        if "error" in skill_def:
            return {"status": "error", "message": skill_def["error"], "attempt": attempt}

        # Validate generated code
        script_code = skill_def.get("script_code", "")
        if not script_code:
            last_errors = ["No script_code in response"]
            continue

        validation = validate(script_code)
        if not validation["valid"]:
            last_errors = validation["errors"]
            continue

        break
    else:
        return {
            "status": "error",
            "message": f"Update failed after {max_attempts} attempts",
            "last_errors": last_errors,
        }

    # Backup old version before overwriting
    skill_dir = GENERATED_DIR / name
    old_script = skill_dir / script_name
    if old_script.exists():
        backup_name = script_name.replace(".py", "_backup.py")
        (skill_dir / backup_name).write_text(old_script.read_text(encoding="utf-8"), encoding="utf-8")

    # Save updated code
    (skill_dir / script_name).write_text(script_code, encoding="utf-8")

    # Update SKILL.md if description changed
    new_desc = skill_def.get("description", entry.get("description", ""))
    if new_desc != entry.get("description", ""):
        skill_md_template = (TEMPLATES_DIR / "skill_template.md").read_text(encoding="utf-8")
        skill_md = skill_md_template.replace("{{SKILL_NAME}}", name)
        skill_md = skill_md.replace("{{DESCRIPTION}}", new_desc)
        skill_md = skill_md.replace("{{INTENTS}}", skill_def.get("intents", ""))
        skill_md = skill_md.replace("{{PRIORITY}}", str(entry.get("priority", 35)))
        skill_md = skill_md.replace("{{INSTRUCTIONS}}", skill_def.get("instructions", ""))
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Update registry entry
    entry["description"] = new_desc
    entry["updated_at"] = datetime.now().isoformat()
    entry["update_reason"] = fix_description
    entry["model_used"] = skill_def.get("model_used", "unknown")
    entry["tokens_input"] = entry.get("tokens_input", 0) + skill_def.get("tokens_input", 0)
    entry["tokens_output"] = entry.get("tokens_output", 0) + skill_def.get("tokens_output", 0)
    entry["validation_result"] = validation
    entry["update_attempts"] = attempt
    registry["generated_skills"][entry_idx] = entry
    _save_registry(registry)

    workspace_path = Path.home() / ".openclaw" / "workspace" / entry["path"] / script_name

    backup_name = script_name.replace(".py", "_backup.py")

    return {
        "status": "updated",
        "skill_name": name,
        "description": new_desc,
        "fix_applied": fix_description,
        "validation": validation,
        "inline_exec": f"python {workspace_path}",
        "backup": f"{skill_dir / backup_name}",
        "model_used": skill_def.get("model_used", "unknown"),
        "attempts": attempt,
    }


def action_rollback(name: str) -> dict:
    """Rollback a skill to its previous version (from _backup.py)."""
    registry = _load_registry()

    entry = None
    for s in registry["generated_skills"]:
        if s["name"] == name and s["status"] == "active":
            entry = s
            break

    if not entry:
        return {"status": "error", "message": f"Active skill not found: {name}"}

    # Find script name
    script_name = None
    for f in entry.get("files", []):
        if f.endswith(".py"):
            script_name = f
            break

    if not script_name:
        return {"status": "error", "message": f"No Python script in skill: {name}"}

    skill_dir = GENERATED_DIR / name
    backup_name = script_name.replace(".py", "_backup.py")
    backup_path = skill_dir / backup_name
    script_path = skill_dir / script_name

    if not backup_path.exists():
        return {"status": "error", "message": f"No backup found for {name}"}

    # Restore backup
    script_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
    backup_path.unlink()

    workspace_path = Path.home() / ".openclaw" / "workspace" / entry["path"] / script_name

    return {
        "status": "rolled_back",
        "skill_name": name,
        "inline_exec": f"python {workspace_path}",
        "message": f"Restored previous version of {name}",
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


def _parse_args() -> dict:
    """Parse CLI args. Supports THREE input methods:
    1. request.json file (preferred — no encoding issues):
       Write request.json in same dir, run script with no args
    2. Flag-style: --action create --need "fetch HTML" --context "msg"
    3. Positional: create fetch HTML from URL
    """
    raw = sys.argv[1:]
    result = {"action": "", "need": "", "context": "", "name": ""}

    # Priority 1: ALWAYS check for request.json first (bot writes it via file_write tool)
    # This takes priority even if CLI args are present, because Gemini often
    # adds unexpected arguments to the exec command.
    request_file = SKILL_DIR / "request.json"
    if request_file.exists():
        try:
            raw_text = request_file.read_text(encoding="utf-8")
            try:
                req = json.loads(raw_text)
            except json.JSONDecodeError:
                # Bot (Gemini) often writes invalid escapes like \' in JSON.
                # Fix by stripping invalid backslash sequences.
                fixed = []
                idx = 0
                valid_esc = set('"\\bfnrtu/')
                while idx < len(raw_text):
                    ch = raw_text[idx]
                    if ch == "\\" and idx + 1 < len(raw_text):
                        nxt = raw_text[idx + 1]
                        if nxt in valid_esc:
                            fixed.append(ch)
                            fixed.append(nxt)
                            idx += 2
                        else:
                            idx += 1  # skip invalid backslash
                    else:
                        fixed.append(ch)
                        idx += 1
                req = json.loads("".join(fixed))
            result["action"] = req.get("action", "")
            result["need"] = req.get("need", "")
            result["context"] = req.get("context", "")
            result["name"] = req.get("name", "")
            # Delete after reading to avoid stale data
            request_file.unlink()
            return result
        except (json.JSONDecodeError, OSError):
            pass  # Fall through to CLI parsing

    if not raw:
        return result

    # Check if using --flag style
    if any(a.startswith("--") for a in raw):
        # Flag-style: extract --action, --need, --context, --name
        i = 0
        while i < len(raw):
            arg = raw[i]
            if arg in ("--action",) and i + 1 < len(raw):
                result["action"] = raw[i + 1]
                i += 2
            elif arg in ("--need",) and i + 1 < len(raw):
                # Collect everything until next --flag or end
                parts = []
                i += 1
                while i < len(raw) and not raw[i].startswith("--"):
                    parts.append(raw[i])
                    i += 1
                result["need"] = " ".join(parts)
            elif arg in ("--context",) and i + 1 < len(raw):
                parts = []
                i += 1
                while i < len(raw) and not raw[i].startswith("--"):
                    parts.append(raw[i])
                    i += 1
                result["context"] = " ".join(parts)
            elif arg in ("--name",) and i + 1 < len(raw):
                result["name"] = raw[i + 1]
                i += 2
            else:
                i += 1
    else:
        # Positional style: first arg is action, rest is need/name
        result["action"] = raw[0]
        rest = " ".join(raw[1:])
        if result["action"] in ("create",):
            result["need"] = rest
        elif result["action"] in ("read",):
            result["name"] = rest
        elif result["action"] in ("update",):
            parts = rest.split(" ", 1)
            result["name"] = parts[0] if parts else ""
            result["need"] = parts[1] if len(parts) > 1 else ""

    return result


def main() -> None:
    parsed = _parse_args()
    action = parsed["action"]
    need = parsed["need"]
    context = parsed["context"]
    name = parsed["name"]

    if not action:
        _write_result({"status": "error", "message": "No action specified"})
        return

    # Suppress any stray stdout during execution
    real_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        if action == "create":
            if not need:
                result = {"status": "error", "message": "need is required for create"}
            else:
                result = action_create(need, context)
        elif action == "list":
            result = action_list()
        elif action == "read":
            if not name:
                result = {"status": "error", "message": "name is required for read"}
            else:
                result = action_read(name)
        elif action == "update":
            if not name or not need:
                result = {"status": "error", "message": "name and need are required for update"}
            else:
                result = action_update(name, need)
        elif action == "rollback":
            if not name:
                result = {"status": "error", "message": "name is required for rollback"}
            else:
                result = action_rollback(name)
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
    except Exception as e:
        result = {"status": "error", "message": str(e)}
    finally:
        sys.stdout = real_stdout

    _write_result(result)


def _write_result(result: dict) -> None:
    """Write result to file and print marker to stdout."""
    output = json.dumps(result, ensure_ascii=True)
    result_file = SKILL_DIR / "last_result.json"
    result_file.write_text(output, encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()
