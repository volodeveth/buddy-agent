#!/usr/bin/env python3
"""Call DeepSeek V3.2 (or fallback) via OpenRouter for skill engineering.
DeepSeek V3.2 receives: need description + template + constraints.
DeepSeek V3.2 returns: complete skill (name, SKILL.md, Python code) as JSON."""

import sys
import io
import json
import os
import warnings
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Load config ---


def _load_env() -> None:
    """Load .env file if OPENROUTER_API_KEY not set."""
    _loader_path = SKILL_DIR.parent / "buddy-utils" / "env_loader.py"
    if _loader_path.exists():
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("env_loader", _loader_path)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.load_env()


def _load_meta_config() -> dict:
    """Load meta skill config from security_config.json."""
    config_path = PROJECT_ROOT / "skills" / "buddy-security" / "security_config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("meta_skill_rules", {})
    return {}


def _load_system_prompt(need: str, context: str, allowed_domains: list[str],
                        existing_skills: list[str]) -> str:
    """Load and fill system prompt template."""
    prompt_path = TEMPLATES_DIR / "system_prompt.txt"
    prompt = prompt_path.read_text(encoding="utf-8")
    prompt = prompt.replace("{{ALLOWED_DOMAINS}}", ", ".join(allowed_domains))
    prompt = prompt.replace("{{EXISTING_SKILLS}}", "\n".join(f"- {s}" for s in existing_skills))
    return prompt


def _get_existing_skills() -> list[str]:
    """List existing skill names from workspace."""
    skills_dir = PROJECT_ROOT / "skills"
    existing = []
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                existing.append(d.name)
    # Also check generated skills
    gen_dir = SKILL_DIR / "generated"
    if gen_dir.exists():
        for d in gen_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                existing.append(d.name)
    return existing


def call_model(model: str, system_prompt: str, user_prompt: str,
               max_tokens: int = 25000, temperature: float = 0.3) -> dict:
    """Call a model via OpenRouter API. Returns parsed response."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not set"}

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    data = json.dumps(payload).encode("utf-8")
    req = Request(OPENROUTER_URL, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("HTTP-Referer", "https://buddy-agent.local")
    req.add_header("X-Title", "Buddy Agent Meta Skill")

    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {body[:500]}"}
    except URLError as e:
        return {"error": f"Network error: {e.reason}"}

    content = result["choices"][0]["message"]["content"]
    finish_reason = result["choices"][0].get("finish_reason", "unknown")
    usage = result.get("usage", {})

    if finish_reason == "length":
        return {"error": f"Model output truncated (hit max_tokens). finish_reason=length, tokens_output={usage.get('completion_tokens', 0)}"}

    return {
        "content": content,
        "model_used": model,
        "tokens_input": usage.get("prompt_tokens", 0),
        "tokens_output": usage.get("completion_tokens", 0),
    }


SKILL_JSON_KEYS = [
    "skill_name", "description", "intents", "priority",
    "script_name", "script_code", "instructions",
]


def _extract_fields_fallback(content: str) -> dict:
    """Extract skill fields by finding key boundaries when JSON is broken.
    MiniMax often returns JSON with unescaped quotes inside script_code."""
    result = {}
    key_positions = []
    for key in SKILL_JSON_KEYS:
        pos = content.find(f'"{key}"')
        if pos >= 0:
            key_positions.append((pos, key))
    key_positions.sort()

    for i, (pos, key) in enumerate(key_positions):
        colon = content.index(":", pos + len(key) + 2)
        val_start = colon + 1
        while val_start < len(content) and content[val_start] in " \t\n\r":
            val_start += 1

        if i + 1 < len(key_positions):
            val_end = key_positions[i + 1][0]
            while val_end > val_start and content[val_end - 1] in " \t\n\r,":
                val_end -= 1
        else:
            val_end = content.rfind("}")
            while val_end > val_start and content[val_end - 1] in " \t\n\r,":
                val_end -= 1

        raw_value = content[val_start:val_end]
        try:
            result[key] = json.loads(raw_value)
            continue
        except (json.JSONDecodeError, ValueError):
            pass

        if raw_value.startswith('"'):
            inner = raw_value[1:]
            if inner.endswith('"'):
                inner = inner[:-1]
            inner = inner.replace("\\n", "\n").replace("\\t", "\t")
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
            result[key] = inner
        else:
            try:
                result[key] = int(raw_value)
            except ValueError:
                result[key] = raw_value

    if not result.get("skill_name"):
        return {"error": f"Could not extract skill fields from response: {content[:200]}"}
    return result


def parse_skill_response(content: str) -> dict:
    """Parse MiniMax response into skill definition. Handles JSON in markdown blocks."""
    debug_file = SKILL_DIR / "last_raw_response.txt"
    debug_file.write_text(content, encoding="utf-8")

    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    # Try direct JSON parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON object from text
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        raw = content[start:end]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Fallback: extract fields by key boundaries
        return _extract_fields_fallback(raw)

    return {"error": f"No JSON object found in response: {content[:200]}"}


def generate_skill(need: str, context: str = "",
                   correction_errors: list[str] | None = None) -> dict:
    """Generate a complete skill using MiniMax M2.7.

    Args:
        need: What the user needs (plain language)
        context: Original user message for context
        correction_errors: If retrying, the errors from previous attempt

    Returns: Parsed skill definition or error dict
    """
    _load_env()
    config = _load_meta_config()

    model = config.get("heavy_model", "deepseek/deepseek-chat-v3.2")
    fallback = config.get("fallback_model", "deepseek/deepseek-chat")
    allowed_domains = config.get("allowed_network_domains", [
        "api.privatbank.ua", "api.openweathermap.org",
        "api.duckduckgo.com", "api.github.com", "wttr.in",
    ])
    existing_skills = _get_existing_skills()

    system_prompt = _load_system_prompt(need, context, allowed_domains, existing_skills)

    if correction_errors:
        # Build specific fix instructions based on error types
        fix_hints = []
        for err in correction_errors:
            if "lines" in err and "max allowed" in err:
                fix_hints.append(
                    "CODE TOO LONG. You MUST shorten it: remove help/usage text, "
                    "inline simple methods, remove verbose docstrings, compress "
                    "action routing with a dispatch dict. Target under 700 lines."
                )
                break
        hint_text = "\n".join(fix_hints) if fix_hints else "Fix the code and return corrected JSON."

        user_prompt = (
            f"PREVIOUS ATTEMPT FAILED VALIDATION.\n"
            f"Errors: {json.dumps(correction_errors)}\n\n"
            f"{hint_text}\n\n"
            f"Original need: {need}\n"
            f"Context: {context}"
        )
    elif context.startswith("UPDATE_EXISTING:"):
        # Update mode: context contains the existing code
        existing_code = context[len("UPDATE_EXISTING:"):]
        user_prompt = (
            f"UPDATE an existing skill. Here is the current code:\n"
            f"```python\n{existing_code}\n```\n\n"
            f"Required changes: {need}\n\n"
            f"Return the COMPLETE updated skill as JSON (same format as creating new).\n"
            f"Keep the same skill_name, update only what's needed."
        )
    else:
        user_prompt = (
            f"Create a skill for this need:\n{need}\n\n"
            f"User's original message: {context}\n\n"
            f"Return ONLY a JSON object with the skill definition."
        )

    # Try primary model
    result = call_model(model, system_prompt, user_prompt)

    if "error" in result and fallback:
        # Try fallback model
        result = call_model(fallback, system_prompt, user_prompt)

    if "error" in result:
        return result

    skill_def = parse_skill_response(result["content"])
    if "error" in skill_def:
        return skill_def

    # Add metadata
    skill_def["model_used"] = result.get("model_used", model)
    skill_def["tokens_input"] = result.get("tokens_input", 0)
    skill_def["tokens_output"] = result.get("tokens_output", 0)

    return skill_def


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate skill via heavy model")
    parser.add_argument("--need", required=True, help="What the user needs")
    parser.add_argument("--context", default="", help="Original user message")
    parser.add_argument("--errors", default="", help="JSON array of errors from previous attempt")

    args = parser.parse_args()

    correction_errors = None
    if args.errors:
        try:
            correction_errors = json.loads(args.errors)
        except json.JSONDecodeError:
            correction_errors = [args.errors]

    result = generate_skill(args.need, args.context, correction_errors)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
