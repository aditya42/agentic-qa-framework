import os
from unittest.mock import Mock, patch
import pytest
from agentic_qa.model_access import verify_model

def test_accessible_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    response = Mock()
    response.json.return_value = {"data": [{"id": "openai/gpt-oss-120b"}]}
    response.raise_for_status.return_value = None
    with patch("agentic_qa.model_access.requests.get", return_value=response):
        assert verify_model() == "openai/gpt-oss-120b"

def test_unavailable_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "retired-model")
    response = Mock()
    response.json.return_value = {"data": [{"id": "openai/gpt-oss-120b"}]}
    with patch("agentic_qa.model_access.requests.get", return_value=response):
        with pytest.raises(RuntimeError, match="not available"):
            verify_model()

def test_missing_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        verify_model()
