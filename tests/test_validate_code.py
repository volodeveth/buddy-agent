"""Tests for buddy-meta/validate_code.py."""

import sys
from pathlib import Path

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-meta"
sys.path.insert(0, str(SKILL_PATH))

import validate_code

VALID = '#!/usr/bin/env python3\nimport sys\nimport json\n\ndef main():\n    print(json.dumps({"ok": True}))\n\nif __name__ == "__main__":\n    main()\n'


class TestValidate:
    def test_valid(self):
        assert validate_code.validate(VALID)["valid"] is True

    def test_forbidden_import(self):
        code = VALID.replace("import json", "import json\nimport subprocess")
        r = validate_code.validate(code)
        assert r["valid"] is False and any("subprocess" in e for e in r["errors"])

    def test_eval_forbidden(self):
        code = VALID.replace('{"ok": True}', 'eval("1+1")')
        assert validate_code.validate(code)["valid"] is False

    def test_no_main(self):
        assert validate_code.validate("import sys\nprint('hi')")["valid"] is False

    def test_syntax_error(self):
        assert validate_code.validate("def broken(:\n  pass")["valid"] is False

    def test_too_long(self):
        assert validate_code.validate(VALID + "\n# pad\n" * 900)["valid"] is False

    def test_stats(self):
        assert validate_code.validate(VALID)["stats"]["functions"] >= 1
