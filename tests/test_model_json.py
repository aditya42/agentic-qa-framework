import json
import pytest
from types import SimpleNamespace
from unittest.mock import patch
from agentic_qa.model_json import parse_model_json
from agentic_qa.models import Cases, Diagnosis
from agentic_qa.graph import design, diagnose

SAMPLE = {"cases": [{"id": "TC-001", "title": "Valid login",
                     "steps": ["Open login page", "Submit credentials"],
                     "expected": ["Inventory page appears"]}]}

def test_parse_plain_json():
    result = parse_model_json(json.dumps(SAMPLE), Cases)
    assert result.cases[0].id == "TC-001"

def test_parse_json_fence():
    result = parse_model_json("```json\n" + json.dumps(SAMPLE) + "\n```", Cases)
    assert len(result.cases) == 1

@pytest.mark.parametrize("payload", [
    "", "Here is JSON: " + json.dumps(SAMPLE), '{"cases": [}', '{"name":"Cases","arguments":{}}',
    '{"cases":[]}', '{"cases":[{"id":"a"}]}', '{"cases":[],"unexpected":true}'
])
def test_reject_invalid_cases(payload):
    with pytest.raises(ValueError):
        parse_model_json(payload, Cases)

def test_diagnosis_optional_code():
    data = {"category": "environment", "explanation": "Timeout"}
    assert parse_model_json(json.dumps(data), Diagnosis).revised_code is None

def test_design_calls_plain_llm_not_tool_schema():
    model = SimpleNamespace(invoke=lambda _: SimpleNamespace(content=json.dumps(SAMPLE)))
    with patch("agentic_qa.graph.llm", return_value=model):
        response = design({"requirement": "Login works", "analysis": "Test login"})
    assert response["cases"].cases[0].title == "Valid login"

def test_diagnose_calls_plain_llm_not_tool_schema(tmp_path):
    model = SimpleNamespace(invoke=lambda _: SimpleNamespace(content=json.dumps({
        "category": "environment", "explanation": "Sandbox unavailable",
        "revised_code": None
    })))
    with patch("agentic_qa.graph.llm", return_value=model):
        result = diagnose({"requirement":"Login", "code":"def test_login(): assert True",
                           "stdout":"Docker unavailable"})
    assert result["diagnosis"].category == "environment"
