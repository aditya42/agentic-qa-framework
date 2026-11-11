import json
from agentic_qa.audit import record

def test_audit_excludes_unknown_fields(tmp_path):
    path = tmp_path / "audit.jsonl"
    record(path, run_id="123", event="run_finished", status="failed",
           details={"case_count": 3, "GROQ_API_KEY": "secret"})
    obj = json.loads(path.read_text())
    assert obj["details"] == {"case_count": 3}
    assert "secret" not in path.read_text()
