"""Guard 1: the system under test has no code path to the answer key."""
import ast, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _code_only(src):
    """Strip docstrings/comments so the guard checks executable code, not prose."""
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module, ast.AsyncFunctionDef)) and ast.get_docstring(n):
            n.body = n.body[1:] or [ast.Pass()]
    return ast.unparse(tree)

def test_harness_never_references_labels():
    for p in (ROOT / "harness").rglob("*.py"):
        code = _code_only(p.read_text())
        assert not re.search(r"labels", code, re.I), f"{p} references labels/ in executable code"

def test_prompts_carry_no_answer_key():
    for p in (ROOT / "harness" / "prompts").glob("*.md"):
        src = p.read_text().lower()
        assert "fault_id" not in src and "expected_verdict" not in src and "canonical_remediation" not in src, p

def test_grounded_prompt_has_no_config_slot():
    src = (ROOT / "harness" / "prompts" / "arm_grounded.md").read_text()
    assert "{{CONFIG}}" not in src, "grounded arm must never receive raw config"
