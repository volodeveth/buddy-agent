#!/usr/bin/env python3
"""Static analysis validator for generated skill code.
Checks for forbidden imports, patterns, file writes, and template structure."""

import sys
import io
import json
import ast
import re
from pathlib import Path

if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent

# --- Safety Rules ---

FORBIDDEN_IMPORT_NAMES = {
    "subprocess", "shutil", "ctypes", "cffi", "socket",
    "multiprocessing", "threading", "signal", "pty", "termios",
    "importlib", "code", "codeop", "compileall",
}

FORBIDDEN_FROM_IMPORTS = {
    ("os", "system"), ("os", "popen"), ("os", "exec"),
    ("os", "execv"), ("os", "execve"), ("os", "spawn"),
    ("os", "fork"), ("os", "kill"),
    ("builtins", "__import__"),
}

FORBIDDEN_PATTERNS = [
    (r"os\.system\s*\(", "os.system() call"),
    (r"os\.popen\s*\(", "os.popen() call"),
    (r"subprocess\.\w+\s*\(", "subprocess usage"),
    (r"(?<!\w)eval\s*\(", "eval() call"),
    (r"(?<!\w)exec\s*\(", "exec() call"),
    (r"__import__\s*\(", "__import__() call"),
    (r"shutil\.", "shutil usage"),
]

# Patterns that produce warnings, not errors (legitimate in many skills)
WARNED_PATTERNS = [
    (r"\.write_text\s*\(", "Path.write_text() — file write"),
    (r"\.write_bytes\s*\(", "Path.write_bytes() — file write"),
    (r"\.unlink\s*\(", "file deletion"),
    (r"\.rmdir\s*\(", "directory deletion"),
]

ALLOWED_IMPORTS = {
    "json", "sys", "io", "pathlib", "urllib", "urllib.request",
    "urllib.parse", "urllib.error", "datetime", "re", "math",
    "hashlib", "base64", "collections", "csv", "os.path", "os",
    "typing", "dataclasses", "enum", "functools", "itertools",
    "textwrap", "string", "decimal", "fractions",
    "requests", "httpx", "bs4", "html", "html.parser",
    "asyncio", "playwright", "playwright.sync_api", "playwright.async_api",
    "tempfile", "time", "struct", "abc", "contextlib",
    "uuid", "secrets", "random", "copy", "operator",
    "xml", "xml.etree", "xml.etree.ElementTree",
}

MAX_LINES = 800


def _load_config() -> dict:
    """Load meta_skill_rules from security config if available."""
    config_path = PROJECT_ROOT / "skills" / "buddy-security" / "security_config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("meta_skill_rules", {})
    return {}


def _load_allowed_domains(config: dict) -> list[str]:
    """Get allowed network domains from config or defaults."""
    return config.get("allowed_network_domains", [
        "api.privatbank.ua", "api.openweathermap.org",
        "api.duckduckgo.com", "api.github.com", "wttr.in",
    ])


def validate(code: str, allowed_domains: list[str] | None = None) -> dict:
    """Validate Python source code against safety rules.

    Returns: {"valid": bool, "errors": [...], "warnings": [...]}
    """
    errors: list[str] = []
    warnings: list[str] = []

    config = _load_config()
    if allowed_domains is None:
        allowed_domains = _load_allowed_domains(config)

    # --- Line count ---
    lines = code.strip().split("\n")
    max_lines = config.get("max_script_lines", MAX_LINES)
    if len(lines) > max_lines:
        errors.append(f"Script has {len(lines)} lines, max allowed is {max_lines}")

    # --- AST Parse ---
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # --- Check imports ---
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_module = alias.name.split(".")[0]
                if top_module in FORBIDDEN_IMPORT_NAMES:
                    errors.append(f"Forbidden import: {alias.name} (line {node.lineno})")
                elif alias.name not in ALLOWED_IMPORTS and top_module not in ALLOWED_IMPORTS:
                    warnings.append(f"Unusual import: {alias.name} (line {node.lineno})")

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top_module = module.split(".")[0]
            if top_module in FORBIDDEN_IMPORT_NAMES:
                errors.append(f"Forbidden import: from {module} (line {node.lineno})")
            for alias in (node.names or []):
                if (module, alias.name) in FORBIDDEN_FROM_IMPORTS:
                    errors.append(f"Forbidden import: from {module} import {alias.name} (line {node.lineno})")

    # --- Regex pattern check (hard errors) ---
    for pattern, description in FORBIDDEN_PATTERNS:
        matches = list(re.finditer(pattern, code))
        for match in matches:
            line_num = code[:match.start()].count("\n") + 1
            errors.append(f"Forbidden pattern: {description} (line {line_num})")

    # --- Regex pattern check (soft warnings) ---
    for pattern, description in WARNED_PATTERNS:
        matches = list(re.finditer(pattern, code))
        for match in matches:
            line_num = code[:match.start()].count("\n") + 1
            warnings.append(f"Pattern note: {description} (line {line_num})")

    # --- Template structure check ---
    has_main = any(
        isinstance(node, ast.FunctionDef) and node.name == "main"
        for node in ast.walk(tree)
    )
    if not has_main:
        errors.append("Missing main() function")

    has_json_dumps = "json.dumps" in code
    if not has_json_dumps:
        warnings.append("No json.dumps found — output should be JSON")

    has_sys_argv = "sys.argv" in code
    if not has_sys_argv:
        warnings.append("No sys.argv usage — input should come from CLI args")

    has_name_main = 'if __name__ == "__main__"' in code or "if __name__ == '__main__'" in code
    if not has_name_main:
        errors.append('Missing if __name__ == "__main__" guard')

    # --- URL domain check (warnings only — domains are checked at runtime) ---
    url_pattern = r'https?://([a-zA-Z0-9._-]+)'
    urls = re.findall(url_pattern, code)
    for domain in urls:
        if domain in ("example.com", "www.example.com"):
            continue
        if not any(domain.endswith(allowed) for allowed in allowed_domains):
            warnings.append(f"Network domain not in default whitelist: {domain}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "lines": len(lines),
            "imports": len([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]),
            "functions": len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
        }
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: validate_code.py <python_file_or_code> [--inline]"}))
        sys.exit(1)

    source = sys.argv[1]
    inline = "--inline" in sys.argv

    if inline:
        # Source is the code itself (passed as argument)
        code = source
    else:
        # Source is a file path
        path = Path(source)
        if not path.exists():
            print(json.dumps({"error": f"File not found: {source}"}))
            sys.exit(1)
        code = path.read_text(encoding="utf-8")

    result = validate(code)
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
