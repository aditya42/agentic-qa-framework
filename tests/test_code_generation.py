import pytest
from agentic_qa.graph import extract_python


def test_unfenced_python():
    result = extract_python("def test_example():\n    assert 1 == 1")
    assert result.startswith("def test_example")


def test_fenced_python():
    result = extract_python("```python\ndef test_example():\n    assert True\n```")
    assert "assert True" in result
    assert "```" not in result


@pytest.mark.parametrize("bad", [
    "",
    "```python\ndef test_bad():\n    assert True",
    "{\"name\": \"code\", \"arguments\": \"```python\"}",
    "def test_bad(:",
])
def test_invalid_code_rejected(bad):
    with pytest.raises((SyntaxError, ValueError)):
        extract_python(bad)
