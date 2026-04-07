#!/usr/bin/env python3
"""Development workflow helper — scaffold, git, dependencies."""

import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECTS_DIR = Path("D:/Projects")

SCAFFOLDS: dict[str, dict] = {
    "nextjs": {
        "files": {
            "package.json": '{"name": "{{NAME}}", "private": true, "scripts": {"dev": "next dev", "build": "next build"}, "dependencies": {"next": "latest", "react": "latest", "react-dom": "latest"}}',
            "tsconfig.json": '{"compilerOptions": {"target": "es5", "lib": ["dom", "esnext"], "strict": true, "jsx": "preserve"}, "include": ["**/*.ts", "**/*.tsx"]}',
            "app/layout.tsx": 'export default function RootLayout({ children }: { children: React.ReactNode }) {\n  return <html><body>{children}</body></html>\n}',
            "app/page.tsx": 'export default function Home() {\n  return <h1>Hello World</h1>\n}',
            ".gitignore": "node_modules/\n.next/\n.env\n",
        },
    },
    "python": {
        "files": {
            "requirements.txt": "",
            "src/__init__.py": "",
            "src/main.py": '#!/usr/bin/env python3\n\ndef main() -> None:\n    print("Hello World")\n\nif __name__ == "__main__":\n    main()\n',
            "tests/__init__.py": "",
            ".gitignore": "__pycache__/\n*.pyc\nvenv/\n.env\n",
        },
    },
    "node": {
        "files": {
            "package.json": '{"name": "{{NAME}}", "version": "1.0.0", "main": "src/index.js", "scripts": {"start": "node src/index.js"}}',
            "src/index.js": 'console.log("Hello World");\n',
            ".gitignore": "node_modules/\n.env\n",
        },
    },
}


def action_scaffold(name: str, project_type: str = "python") -> dict:
    if project_type not in SCAFFOLDS:
        return {"status": "error", "message": f"Unknown type: {project_type}. Use: {list(SCAFFOLDS.keys())}"}
    project_dir = PROJECTS_DIR / name
    if project_dir.exists():
        return {"status": "error", "message": f"Directory already exists: {project_dir}"}
    scaffold = SCAFFOLDS[project_type]
    created = []
    for rel_path, content in scaffold["files"].items():
        fp = project_dir / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content.replace("{{NAME}}", name), encoding="utf-8")
        created.append(rel_path)
    return {"status": "created", "name": name, "type": project_type, "path": str(project_dir), "files": created}


def action_git_status(path: str) -> dict:
    p = Path(path).resolve()
    git_dir = p / ".git"
    if not git_dir.exists():
        return {"status": "error", "message": f"Not a git repo: {path}"}
    result: dict = {"is_git_repo": True, "path": str(p)}
    head = git_dir / "HEAD"
    if head.exists():
        c = head.read_text().strip()
        result["branch"] = c[16:] if c.startswith("ref: refs/heads/") else c[:8] + "... (detached)"
    config = git_dir / "config"
    if config.exists():
        result["remotes"] = [l.strip()[6:] for l in config.read_text().splitlines() if l.strip().startswith("url = ")]
    return result


def action_deps(path: str) -> dict:
    p = Path(path).resolve()
    pkg = p / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = list(data.get("dependencies", {}).keys())
            dev = list(data.get("devDependencies", {}).keys())
            return {"type": "node", "file": "package.json", "dependencies": deps, "dev_dependencies": dev, "total": len(deps) + len(dev)}
        except (json.JSONDecodeError, OSError) as e:
            return {"status": "error", "message": str(e)}
    req = p / "requirements.txt"
    if req.exists():
        try:
            lines = req.read_text(encoding="utf-8").splitlines()
            deps = [l.strip().split("==")[0].split(">=")[0] for l in lines if l.strip() and not l.startswith("#")]
            return {"type": "python", "file": "requirements.txt", "dependencies": deps, "total": len(deps)}
        except OSError as e:
            return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "No package.json or requirements.txt found"}


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: dev.py <action> [args]", "actions": {"scaffold": "dev.py scaffold <name> [type]", "git-status": "dev.py git-status <path>", "deps": "dev.py deps <path>"}}))
        sys.exit(1)
    action = sys.argv[1]
    if action == "scaffold":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        ptype = sys.argv[3] if len(sys.argv) > 3 else "python"
        result = action_scaffold(name, ptype) if name else {"status": "error", "message": "Project name required"}
    elif action == "git-status":
        result = action_git_status(sys.argv[2] if len(sys.argv) > 2 else ".")
    elif action == "deps":
        result = action_deps(sys.argv[2] if len(sys.argv) > 2 else ".")
    else:
        result = {"status": "error", "message": f"Unknown action: {action}"}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
