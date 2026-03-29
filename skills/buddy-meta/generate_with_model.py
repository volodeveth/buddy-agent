#!/usr/bin/env python3
"""Call MiniMax M2.7 (or fallback) via OpenRouter for skill engineering.
MiniMax receives: need description + template + constraints.
MiniMax returns: complete skill (name, SKILL.md, Python code) as JSON."""

import sys
import io
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Load config ---

_ENV_CANDIDATES = [
    PROJECT_ROOT / ".env",
    Path("D:/Myapps/buddy agent/.env"),
    Path.home() / ".openclaw" / "workspace" / ".env",
]


def _load_env() -> None:
    """Load .env file if OPENROUTER_API_KEY not set."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return
    for env_path in _ENV_CANDIDATES:
        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and val:
                            os.environ.setdefault(key, val)
            break


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


def parse_skill_response(content: str) -> dict:
    """Parse MiniMax response into skill definition. Handles JSON in markdown blocks."""
    # Try direct JSON parse
    content = content.strip()
    if content.startswith("```"):
        # Strip markdown code block
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
        return {"error": f"Could not parse model response as JSON: {content[:200]}"}


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

    model = config.get("heavy_model", "minimax/minimax-m2.7")
    fallback = config.get("fallback_model", "deepseek/deepseek-chat-v3.2")
    allowed_domains = config.get("allowed_network_domains", [
        "api.privatbank.ua", "api.openweathermap.org",
        "api.duckduckgo.com", "api.github.com", "wttr.in",
    ])
    existing_skills = _get_existing_skills()

    system_prompt = _load_system_prompt(need, context, allowed_domains, existing_skills)

    if correction_errors:
        user_prompt = (
            f"PREVIOUS ATTEMPT FAILED VALIDATION.\n"
            f"Errors: {json.dumps(correction_errors)}\n\n"
            f"Fix the code and return corrected JSON.\n\n"
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


def main():
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
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
