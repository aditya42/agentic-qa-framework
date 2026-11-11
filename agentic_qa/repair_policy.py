"""Fail-closed structural review of AI-proposed test repairs.

This gate checks test inventory and assertion structure, but cannot prove semantic
equivalence of expected behavior. Manual approval is mandatory when these checks
cannot establish a safe, narrow repair.
"""
import ast
import hashlib
import os
from pathlib import Path

class RepairApprovalRequired(ValueError):
    pass

def _tests(tree):
    return {node.name: node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")}

def _assertions(node):
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Assert)
            or isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "expect"]

def _calls(node):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]

def _is_literal_change(before, after):
    """Conservatively block changing hardcoded assertion literals."""
    return ast.dump(before, include_attributes=False) != ast.dump(after, include_attributes=False)

def validate_repair(original: str, candidate: str) -> str:
    from .graph import validate
    validate(candidate)
    old = ast.parse(original)
    new = ast.parse(candidate)
    old_tests, new_tests = _tests(old), _tests(new)
    if not old_tests or old_tests.keys() != new_tests.keys():
        raise RepairApprovalRequired("Repair changed the test inventory")
    for name, old_test in old_tests.items():
        new_test = new_tests[name]
        before, after = _assertions(old_test), _assertions(new_test)
        if len(before) != len(after):
            raise RepairApprovalRequired(f"Repair changed assertion count in {name}")
        # Assertion AST is allowed to change only with explicit manual approval.
        # This blocks changing expectations and unsafe automatic assertion rewrites.
        if any(_is_literal_change(a, b) for a, b in zip(before, after)):
            raise RepairApprovalRequired(f"Repair changed assertion expression in {name}")
    return candidate

def is_approved(original: str, candidate: str, approvals: str | None = None) -> bool:
    """Approval is bound to both code versions and is never inferred from an env boolean."""
    digest = hashlib.sha256((original + "\0" + candidate).encode()).hexdigest()
    path = approvals or os.getenv("QA_REPAIR_APPROVAL_FILE")
    if not path:
        return False
    approved = Path(path)
    if not approved.is_file():
        return False
    return digest in {line.strip() for line in approved.read_text(encoding="utf-8").splitlines()}
