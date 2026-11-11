import pytest
from unittest.mock import Mock, patch
from agentic_qa.integrations import publish_jira, publish_testrail

def test_publishing_requires_approval(monkeypatch):
    monkeypatch.delenv("QA_PUBLISH_APPROVED", raising=False)
    with pytest.raises(PermissionError):
        publish_jira("example", "detail")
    with pytest.raises(PermissionError):
        publish_testrail([])

def test_jira_reuses_existing_issue(monkeypatch):
    for key, value in {
        "QA_PUBLISH_APPROVED": "true", "JIRA_BASE_URL": "https://jira.example.com",
        "JIRA_PROJECT_KEY": "QA", "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "not-a-real-token",
    }.items():
        monkeypatch.setenv(key, value)
    response = Mock()
    response.json.return_value = {"issues": [{"key": "QA-123"}]}
    response.raise_for_status.return_value = None
    with patch("agentic_qa.integrations.requests.get", return_value=response), patch("agentic_qa.integrations.requests.post") as post:
        assert publish_jira("same bug", "details") == "QA-123"
        post.assert_not_called()

def test_testrail_reuses_existing_case(monkeypatch):
    for key, value in {
        "QA_PUBLISH_APPROVED": "true", "TESTRAIL_BASE_URL": "https://testrail.example.com",
        "TESTRAIL_SECTION_ID": "2", "TESTRAIL_PROJECT_ID": "1",
        "TESTRAIL_EMAIL": "test@example.com", "TESTRAIL_API_KEY": "fake",
    }.items():
        monkeypatch.setenv(key, value)
    response = Mock()
    response.json.return_value = {"cases": [{"title": "login", "id": 42}]}
    response.raise_for_status.return_value = None
    with patch("agentic_qa.integrations.requests.get", return_value=response), patch("agentic_qa.integrations.requests.post") as post:
        assert publish_testrail([{"title": "login", "steps": ["step"], "expected": ["ok"]}]) == [42]
        post.assert_not_called()
