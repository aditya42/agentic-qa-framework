from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from agentic_qa.sandbox import run

def test_rejects_unisolated_network_in_strict_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_REQUIRE_ISOLATED_NETWORK", "1")
    monkeypatch.setenv("QA_SANDBOX_NETWORK", "bridge")
    with patch("agentic_qa.sandbox.subprocess.run") as subprocess:
        with pytest.raises(ValueError, match="dedicated"):
            run("def test_ok(): assert True", tmp_path)
        subprocess.assert_not_called()

def test_docker_failure_does_not_run_on_host(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_REQUIRE_ISOLATED_NETWORK", "0")
    monkeypatch.setenv("QA_SANDBOX_NETWORK", "bridge")
    with patch("agentic_qa.sandbox.subprocess.run", side_effect=FileNotFoundError):
        passed, output = run("def test_ok(): assert True", tmp_path)
    assert not passed
    assert "Docker executable not found" in output

def test_removes_stale_junit_before_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_REQUIRE_ISOLATED_NETWORK", "0")
    monkeypatch.setenv("QA_SANDBOX_NETWORK", "bridge")
    junit = tmp_path / "junit.xml"
    junit.write_text("<testsuite><testcase name='stale'/></testsuite>")
    with patch("agentic_qa.sandbox.subprocess.run", return_value=SimpleNamespace(returncode=1, stdout="failed", stderr="")):
        passed, _ = run("def test_ok(): assert True", tmp_path)
    assert not passed
    assert not junit.exists()

def test_disallows_invalid_network_name(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_SANDBOX_NETWORK", "bridge;rm -rf /")
    with pytest.raises(ValueError, match="Invalid"):
        run("def test_ok(): assert True", tmp_path)
