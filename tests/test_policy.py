import pytest
from agentic_qa.policy import validate_target

def test_approved_target():
    assert validate_target("https://www.saucedemo.com", "www.saucedemo.com") == "https://www.saucedemo.com"

@pytest.mark.parametrize("target", [
    "http://www.saucedemo.com",
    "https://evil.example",
    "https://www.saucedemo.com.evil.example",
    "https://user:pass@www.saucedemo.com",
    "https://www.saucedemo.com:444",
    "https://www.saucedemo.com/?token=abc",
])
def test_rejects_unapproved_target(target):
    with pytest.raises(ValueError):
        validate_target(target, "www.saucedemo.com")

def test_rejects_missing_allowlist():
    with pytest.raises(ValueError, match="QA_ALLOWED_HOSTS"):
        validate_target("https://www.saucedemo.com", "")
