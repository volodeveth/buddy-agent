#!/usr/bin/env python3
"""
Dev Helper Skill - Розробницький помічник для аналізу проєктів
Дії: scaffold, deps, git-status
"""
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SKILL_DIR = Path(__file__).parent.resolve()

def get_scaffold_structure(project_type: str = "nextjs") -> dict:
    """Повертає рекомендовану структуру проєкту."""
    structures = {
        "nextjs": {
            "project_type": "Next.js",
            "structure": [
                ".next/", "app/", "  layout.tsx", "  page.tsx", "  globals.css",
                "components/", "  ui/", "  layout/", "lib/", "  utils.ts",
                "hooks/", "types/", "public/", "next.config.js", "package.json", "tsconfig.json"
            ]
        },
        "python": {
            "project_type": "Python",
            "structure": [
                "src/", "  __init__.py", "  main.py", "  config.py",
                "  models/", "  routes/", "  services/", "tests/", "  __init__.py",
                "  test_main.py", "requirements.txt", "setup.py", ".env.example", "README.md"
            ]
        },
        "node": {
            "project_type": "Node.js",
            "structure": [
                "src/", "  index.js", "  config/", "  routes/", "  controllers/",
                "  models/", "  middleware/", "  utils/", "tests/", "  index.test.js",
                "package.json", ".env.example", "README.md"
            ]
        }
    }
    return structures.get(project_type, structures["nextjs"])

def read_dependencies(path: Path) -> dict:
    """Читає залежності з package.json або requirements.txt."""
    pkg_json = path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = list(data.get("dependencies", {}).keys())
            dev_deps = list(data.get("devDependencies", {}).keys())
            return {
                "project_type": "Node.js",
                "file": "package.json",
                "dependencies": deps,
                "devDependencies": dev_deps,
                "total_count": len(deps) + len(dev_deps)
            }
        except Exception as e:
            return {"error": f"Помилка читання package.json: {e}"}
    
    req_file = path / "requirements.txt"
    if req_file.exists():
        try:
            lines = req_file.read_text(encoding="utf-8").splitlines()
            deps = [
                line.strip().split("==")[0].split(">=")[0].split("<=")[0]
                for line in lines if line.strip() and not line.startswith("#")
            ]
            return {
                "project_type": "Python",
                "file": "requirements.txt",
                "dependencies": deps,
                "total_count": len(deps)
            }
        except Exception as e:
            return {"error": f"Помилка читання requirements.txt: {e}"}
    
    return {"error": "Файли залежностей не знайдено", "path": str(path)}

def check_git_status(path: Path) -> dict:
    """Перевіряє чи є шлях Git-репозиторієм."""
    git_dir = path / ".git"
    if not git_dir.exists():
        return {
            "is_git_repo": False,
            "path": str(path),
            "message": "Це не Git-репозиторій"
        }
    
    try:
        head_file = git_dir / "HEAD"
        branch = "unknown"
        if head_file.exists():
            content = head_file.read_text().strip()
            if content.startswith("ref: refs/heads/"):
                branch = content.replace("ref: refs/heads/", "")
        
        remotes = []
        config_file = git_dir / "config"
        if config_file.exists():
            for line in config_file.read_text().splitlines():
                if line.strip().startswith("url = "):
                    remotes.append(line.split("=", 1)[1].strip())
        
        return {
            "is_git_repo": True,
            "repo_name": path.name,
            "branch": branch,
            "remotes": remotes,
            "git_dir": str(git_dir)
        }
    except Exception as e:
        return {"is_git_repo": False, "error": str(e)}

def main():
    """Головна функція."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Необхідно вказати дію",
            "usage": "python dev-helper.py <action> [args]",
            "actions": {
                "scaffold": "python dev-helper.py scaffold <type>",
                "deps": "python dev-helper.py deps <path>",
                "git-status": "python dev-helper.py git-status <path>"
            },
            "types": ["nextjs", "python", "node"]
        }, ensure_ascii=False))
        return
    
    action = sys.argv[1].lower()
    
    if action == "scaffold":
        proj_type = sys.argv[2].lower() if len(sys.argv) > 2 else "nextjs"
        if proj_type not in ("nextjs", "python", "node"):
            print(json.dumps({
                "error": f"Невідомий тип проєкту: {proj_type}",
                "valid_types": ["nextjs", "python", "node"]
            }, ensure_ascii=False))
            return
        result = get_scaffold_structure(proj_type)
    elif action == "deps":
        if len(sys.argv) < 3:
            print(json.dumps({
                "error": "Необхідно вказати шлях до проєкту",
                "usage": "python dev-helper.py deps <path>"
            }, ensure_ascii=False))
            return
        path = Path(sys.argv[2]).resolve()
        if not path.exists():
            print(json.dumps({"error": f"Шлях не існує: {path}"}, ensure_ascii=False))
            return
        result = read_dependencies(path)
    elif action == "git-status":
        if len(sys.argv) < 3:
            print(json.dumps({
                "error": "Необхідно вказати шлях до репозиторію",
                "usage": "python dev-helper.py git-status <path>"
            }, ensure_ascii=False))
            return
        path = Path(sys.argv[2]).resolve()
        if not path.exists():
            print(json.dumps({"error": f"Шлях не існує: {path}"}, ensure_ascii=False))
            return
        result = check_git_status(path)
    else:
        result = {"error": f"Невідома дія: {action}"}
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
