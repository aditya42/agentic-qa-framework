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
    """Collect complete assertion calls, not merely the inner expect(locator)."""
    matches = []
    for item in ast.walk(node):
        if isinstance(item, ast.Assert):
            matches.append(item)
        elif isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
            receiver = item.func.value
            if (isinstance(receiver, ast.Call)
                    and isinstance(receiver.func, ast.Name)
                    and receiver.func.id == "expect"):
                matches.append(item)
    return matches

def _calls(node):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]

def _is_literal_change(before, after):
    """Conservatively block changing hardcoded assertion literals."""
    return ast.dump(before, include_attributes=False) != ast.dump(after, include_attributes=False)

def validate_repair(original: str, candidate: str) -> str:
    from .graph import validate
    validate(candidate)
    from .playwright_compat import normalize_playwright_assertions
    # Normalize only one audited equivalent Playwright API rewrite, on both sides.
    # Other changes to assertion methods, operands or expected strings still block.
    old = ast.parse(normalize_playwright_assertions(original))
    new = ast.parse(normalize_playwright_assertions(candidate))
    old_tests, new_tests = _tests(old), _tests(new)
    if not old_tests or old_tests.keys() != new_tests.keys():
        raise RepairApprovalRequired("Repair changed the test inventory")
    for name, old_test in old_tests.items():
        new_test = new_tests[name]
        before, after = _assertions(old_test), _assertions(new_test)
        if len(before) != len(after):
            raise RepairApprovalRequired(f"Repair changed assertion count in {name}")
        # Entire assertion expressions must match after approved normalization.
        # This rejects changed expected values and removal of Playwright checks.
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
