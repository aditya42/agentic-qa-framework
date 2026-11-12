import ast
from agentic_qa.playwright_compat import normalize_playwright_assertions


def test_rewrites_exact_failing_pattern_without_weaker_expectations():
    source = '''from playwright.sync_api import expect
def test_invalid_login():
    error_msg = page.locator("[data-test=error]")
    expect(error_msg).to_be_visible()
    expect(error_msg).to_have_text(
        lambda txt: "Epic sadface" in txt
    )
    expect(error_msg).to_have_text(lambda text: "Username is required" in text)
'''
    normalized = normalize_playwright_assertions(source)
    assert "expect(error_msg).to_contain_text('Epic sadface')" in normalized
    assert "expect(error_msg).to_contain_text('Username is required')" in normalized
    assert "expect(error_msg).to_be_visible()" in normalized
    assert "lambda" not in normalized
    assert normalize_playwright_assertions(normalized) == normalized
    ast.parse(normalized)


def test_does_not_touch_exact_text_assertions_or_other_calls():
    source = '''def test_login():
    expect(error).to_have_text("Epic sadface: Username is required")
    expect(error).to_contain_text("Username")
'''
    assert normalize_playwright_assertions(source) == source


def test_dynamic_lambda_is_not_rewritten():
    source = '''def test_login():
    expect(error).to_have_text(lambda txt: "Something" not in txt)
    expect(error).to_have_text(lambda txt: expected in txt)
    expect(error).to_have_text(lambda txt: txt == "exact")
'''
    assert normalize_playwright_assertions(source) == source


def test_keeps_unicode_and_original_comments():
    source = '''def test_login():
    message = "café"  # keep comment
    expect(error).to_have_text(lambda text: "Échec" in text)
'''
    normalized = normalize_playwright_assertions(source)
    assert '# keep comment' in normalized
    assert "to_contain_text('Échec')" in normalized
    ast.parse(normalized)


def test_unrelated_expect_call_is_not_changed():
    source = '''def test_login():
    custom.to_have_text(lambda txt: "foo" in txt)
'''
    assert normalize_playwright_assertions(source) == source


def test_generate_normalizes_response_before_execution(monkeypatch):
    from types import SimpleNamespace
    from agentic_qa import graph
    raw = '''from playwright.sync_api import expect
def test_login():
    expect(error).to_have_text(lambda txt: "Epic sadface" in txt)
'''
    fake_llm = SimpleNamespace(invoke=lambda _prompt: SimpleNamespace(content=raw))
    monkeypatch.setattr(graph, "llm", lambda: fake_llm)
    cases = SimpleNamespace(model_dump_json=lambda: '{"cases":[]}')
    result = graph.generate({"requirement": "Check login error", "cases": cases})
    assert ".to_contain_text('Epic sadface')" in result["code"]
    assert "lambda" not in result["code"]
