import json
import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from agentic_qa.structured_json import parse_model_json
from agentic_qa.models import Cases
from agentic_qa.graph import design

CASE = {"cases":[{"id":"TC-001","title":"Valid login","steps":["Enter credentials"],"expected":["Inventory opens"]}]}

def test_valid_json():
    assert parse_model_json(json.dumps(CASE), Cases).cases[0].id == "TC-001"

def test_json_fence():
    assert parse_model_json("```json\n"+json.dumps(CASE)+"\n```", Cases).cases[0].title == "Valid login"

def test_tool_wrapper_from_prior_provider_output():
    wrapped = {"name":"Cases","arguments":CASE}
    assert parse_model_json(json.dumps(wrapped), Cases).cases[0].id == "TC-001"

@pytest.mark.parametrize("invalid", [
    "", "not json", '{"cases":[', '{"cases":[]}', '[]',
    '{"cases":[{"id":"one","steps":[],"expected":[]}]}',
    '```json\n{"cases": []}',
])
def test_invalid_json_rejected(invalid):
    with pytest.raises(ValueError):
        parse_model_json(invalid, Cases)

def test_design_invokes_plain_llm_instead_of_structured_tool_call():
    result = Mock()
    result.content = json.dumps(CASE)
    model = Mock()
    model.invoke.return_value = result
    with patch("agentic_qa.graph.llm", return_value=model):
        cases = design({"requirement":"login","analysis":"check success"})["cases"]
    assert cases.cases[0].id == "TC-001"
    model.with_structured_output.assert_not_called()
