import pytest
from agentic_qa.graph import validate

@pytest.mark.parametrize("code", ["import subprocess", "eval('1')", "open('file','w')", "import pathlib"])
def test_rejects_unsafe_code(code):
    with pytest.raises(ValueError):
        validate(code)

def test_accepts_normal_test_code():
    assert validate("import os\nfrom playwright.sync_api import sync_playwright\ndef test_a():\n    assert True")


def test_allows_stdlib_regular_expressions_for_url_assertions():
    source = "import re\nfrom playwright.sync_api import expect\ndef test_url():\n    assert re.search('inventory', 'inventory.html')"
    assert validate(source) == source
