"""Explicit user scenarios define the permitted test design scope."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agentic_qa.graph import design, specified_scenarios

REQUIREMENT = (
    "Application: https://www.saucedemo.com/\n"
    "Scenario: Successful login.\n"
    "Given a user is on the login page\n"
    "When the user logs in\n"
    "Then the inventory page appears\n"
    "Scenario: Invalid login.\n"
    "Given a user enters wrong credentials\n"
    "Then an error is displayed\n"
)


def case(title, number):
    return {"id": f"TC-{number:03}", "title": title, "steps": ["Act"],
            "expected": ["Specified outcome"]}


def fake_model(cases):
    return SimpleNamespace(invoke=lambda prompt: SimpleNamespace(content=json.dumps({"cases": cases})))


def test_explicit_scenarios_extracted_in_order():
    assert specified_scenarios(REQUIREMENT) == ["Successful login.", "Invalid login."]


def test_design_accepts_exact_requested_scenarios():
    cases = [case("Successful login.", 1), case("Invalid login.", 2)]
    with patch("agentic_qa.graph.llm", return_value=fake_model(cases)):
        result = design({"requirement": REQUIREMENT, "analysis": "No more requirements"})
    assert [item.title for item in result["cases"].cases] == ["Successful login.", "Invalid login."]


def test_design_rejects_unrequested_logout_scenario():
    cases = [
        case("Successful login.", 1),
        case("Invalid login.", 2),
        case("Logout after successful login.", 3),
    ]
    with patch("agentic_qa.graph.llm", return_value=fake_model(cases)):
        with pytest.raises(ValueError, match="refusing unrequested"):
            design({"requirement": REQUIREMENT, "analysis": "Explore logout"})


def test_design_rejects_changed_scenario_title():
    cases = [case("Successful login.", 1), case("Logout.", 2)]
    with patch("agentic_qa.graph.llm", return_value=fake_model(cases)):
        with pytest.raises(ValueError, match="titles or order"):
            design({"requirement": REQUIREMENT, "analysis": ""})


def test_without_explicit_scenarios_preserves_generic_generation():
    assert specified_scenarios("Verify successful login") == []
    with patch("agentic_qa.graph.llm", return_value=fake_model([case("Login works", 1)])):
        assert len(design({"requirement": "Verify successful login", "analysis": ""})["cases"].cases) == 1
