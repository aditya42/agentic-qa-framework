import hashlib
import pytest
from types import SimpleNamespace
from agentic_qa.repair_policy import validate_repair, RepairApprovalRequired, is_approved
from agentic_qa.graph import repair, after_repair

ORIGINAL = """def test_login():
    assert 1 == 1
"""
SAFE = """import re
def test_login():
    value = re.compile("x")
    assert 1 == 1
"""
WEAKENED = """def test_login():
    assert True
"""

def test_safe_non_assertion_change():
    assert validate_repair(ORIGINAL, SAFE) == SAFE

def test_assertion_weakened_blocked():
    with pytest.raises(RepairApprovalRequired, match="assertion"):
        validate_repair(ORIGINAL, WEAKENED)

def test_removed_test_blocked():
    with pytest.raises(RepairApprovalRequired, match="inventory"):
        validate_repair(ORIGINAL, "def test_other():\n    assert 1 == 1\n")

def test_invalid_import_blocked():
    with pytest.raises(ValueError):
        validate_repair(ORIGINAL, "import subprocess\n" + ORIGINAL)

def test_repair_node_stops_unapproved_change(monkeypatch):
    monkeypatch.delenv("QA_REPAIR_APPROVAL_FILE", raising=False)
    state = {"code": ORIGINAL, "stdout": "failed",
             "diagnosis": SimpleNamespace(category="test_defect", revised_code=WEAKENED)}
    result = repair(state)
    assert "code" not in result
    assert result["repairs"] == 1
    assert after_repair({**state, **result}) == "end"

def test_code_bound_approval(tmp_path):
    path = tmp_path / "approvals.txt"
    digest = hashlib.sha256((ORIGINAL + "\0" + WEAKENED).encode()).hexdigest()
    path.write_text(digest + "\n")
    assert is_approved(ORIGINAL, WEAKENED, str(path))
    assert not is_approved(ORIGINAL, SAFE, str(path))
