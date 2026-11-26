import pytest
from pydantic import ValidationError
from agentic_qa.release_governance import QualificationInput, qualify, approve
from agentic_qa.release_graph import build_release_graph
from agentic_qa.mcp_tools import ToolCall, EvidenceQuery, gateway_from_env

def evidence():
    return QualificationInput(release_id="demo", report={"status": "passed", "execution": {"status": "valid", "total": 2, "passed": 2, "failed": 0, "errors": 0, "skipped": 0}}, defects=[], required_tests=["TC1", "TC2"], executed_tests=["TC1", "TC2"])

def test_clean_evidence_waits_for_review():
    result = qualify(evidence())
    assert result.recommendation == "ready_for_review"
    assert result.coverage_percent == 100
    assert result.human_approval_required
    assert approve(result, {"release_id": "demo", "evidence_sha256": result.evidence_sha256, "reviewer": "qa-lead", "decision": "approve"})["status"] == "approved_by_human"

def test_missing_coverage_and_unresolved_critical_defects_block():
    data = evidence()
    data.executed_tests = ["TC1"]
    data.defects = [{"severity": "Sev1", "status": "Open"}]
    result = qualify(data)
    assert result.recommendation == "blocked"
    assert result.coverage_percent == 50
    with pytest.raises(PermissionError):
        approve(result, {"release_id": "demo", "evidence_sha256": result.evidence_sha256, "reviewer": "qa-lead", "decision": "approve"})

def test_missing_junit_and_inconsistent_counts_block():
    data = evidence()
    data.report = {}
    assert qualify(data).recommendation == "blocked"
    data.report = {"status": "passed", "execution": {"status": "valid", "total": 4, "passed": 2, "failed": 0, "errors": 0, "skipped": 0}}
    assert qualify(data).recommendation == "blocked"

def test_approval_cannot_reuse_old_evidence_or_robot():
    result = qualify(evidence())
    with pytest.raises(PermissionError):
        approve(result, {"release_id": "demo", "evidence_sha256": "old", "reviewer": "qa-lead", "decision": "approve"})
    with pytest.raises(PermissionError):
        approve(result, {"release_id": "demo", "evidence_sha256": result.evidence_sha256, "reviewer": "agent", "decision": "approve"})

def test_allowlisted_structured_tools_and_release_id():
    with pytest.raises(ValidationError):
        ToolCall(name="delete_issues", arguments={"release_id": "demo"})
    with pytest.raises(ValidationError):
        EvidenceQuery(release_id="../secret")

def test_operator_mcp_configuration_is_required(monkeypatch):
    monkeypatch.delenv("QA_MCP_COMMAND", raising=False)
    with pytest.raises(ValueError):
        gateway_from_env()

class FakeGateway:
    def call(self, request):
        assert request.arguments == {"release_id": "demo"}
        data = evidence()
        if request.name == "get_defect_evidence":
            return {"release_id": "demo", "defects": data.defects}
        if request.name == "get_test_coverage":
            return {"release_id": "demo", "required_tests": data.required_tests, "executed_tests": data.executed_tests}
        return {"release_id": "demo", "report": data.report, "failures": []}

def test_langgraph_orchestrates_mcp_tools_and_events():
    result = build_release_graph(FakeGateway()).invoke({"release_id": "demo", "events": []})
    assert result["assessment"]["recommendation"] == "ready_for_review"
    assert [event["event"] for event in result["events"]] == ["evidence_retrieved", "release_qualified"]
