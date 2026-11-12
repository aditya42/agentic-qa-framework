import ast
import os
import re
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from .models import Cases, Diagnosis
from .sandbox import run as sandbox_run
from .learning import remember, examples
from .repair_policy import validate_repair, RepairApprovalRequired, is_approved
from .model_json import parse_model_json
from .playwright_compat import normalize_playwright_assertions

load_dotenv()
ARTIFACTS = Path("artifacts")
REPAIR_DB = Path(os.getenv("QA_REPAIR_DB", "artifacts/repairs.sqlite3"))

class QAState(TypedDict, total=False):
    requirement: str
    analysis: str
    cases: Cases
    code: str
    stdout: str
    passed: bool
    diagnosis: Diagnosis
    repairs: int
    original_failure: str
    repaired_code: str

def llm():
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY in .env")
    return ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), temperature=0)

def analyze(state: QAState):
    response = llm().invoke("Analyze these functional acceptance criteria. Identify testable behavior, assumptions, and missing information. Do not invent requirements.\n" + state["requirement"])
    return {"analysis": response.content}

def specified_scenarios(requirement: str) -> list[str]:
    """Return explicit Scenario headings; never infer scenarios from unrelated prose."""
    return [
        match.group(1).strip()
        for line in requirement.splitlines()
        if (match := re.match(r"^\s*Scenario:\s*(\S.*)$", line, re.IGNORECASE))
    ]


def design(state: QAState):
    scenarios = specified_scenarios(state["requirement"])
    if len(scenarios) > 12:
        raise ValueError("The request contains more than 12 explicit scenarios")
    scope = (
        f"Exactly {len(scenarios)} cases: one for each explicit Scenario, in the same order. "
        "Use the exact scenario heading as each case title, without adding other scenarios. "
        "Explicit scenario headings: " + repr(scenarios) + ". "
        if scenarios else
        "Create 1-8 cases justified by the supplied acceptance criteria only. "
    )
    prompt = (
        "Design independent browser test cases with steps and expected results. "
        + scope +
        "Do not add exploratory, boundary, logout, or negative scenarios unless explicitly "
        "requested or required by the supplied acceptance criteria. "
        "Analysis is advisory; the original requirement is authoritative. "
        "Return exactly one JSON object of shape "
        '{"cases":[{"id":"TC-001","title":"...","steps":["..."],"expected":["..."]}]}. '
        "Use JSON double quotes, no markdown fences, no comments, no tool calls. "
        "Do not invent unsupported requirements.\nRequirement:\n"
        + state["requirement"] + "\nAnalysis:\n" + state["analysis"]
    )
    response = llm().invoke(prompt)
    cases = parse_model_json(response.content, Cases)
    if scenarios:
        if len(cases.cases) != len(scenarios):
            raise ValueError(
                f"Test design returned {len(cases.cases)} cases for {len(scenarios)} "
                "explicit scenarios; refusing unrequested test cases"
            )
        if any(
            case.title.strip().casefold() != heading.casefold()
            for case, heading in zip(cases.cases, scenarios)
        ):
            raise ValueError("Test design changed explicit scenario titles or order")
    return {"cases": cases}

def extract_python(content: str) -> str:
    """Normalize raw Python or a single fenced code block without executing it."""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Groq did not return Python source")
    source = content.strip()
    if source.startswith("```"):
        lines = source.splitlines()
        if len(lines) < 3 or lines[0].strip().lower() not in ("```python", "```py", "```") or lines[-1].strip() != "```":
            raise ValueError("Malformed Python code fence")
        source = "\n".join(lines[1:-1]).strip()
    tree = ast.parse(source)
    if not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_") for node in tree.body):
        raise ValueError("Generated source must contain a test_ function")
    return source


def generate(state: QAState):
    prompt = ("Generate a COMPLETE Python pytest Playwright test module. Use sync_playwright and browser chromium, no plugins. "
              "Each test must accept no fixtures; open browser via sync_playwright context manager. "
              "Use BASE_URL from os.environ with default https://www.saucedemo.com. "
              "Use Playwright locator assertions and explicit expected outcomes. For substring checks use "
              "expect(locator).to_contain_text(\"expected substring\"); never pass a lambda to "
              "to_have_text() or to_contain_text(). Generate exactly one top-level test_ function "
              "per approved case, without additional test scenarios. "
              "No subprocess, eval, exec, filesystem writes, or external imports beyond os, pytest, playwright. "
              "Return RAW Python source code ONLY. Do not wrap it in JSON, markdown or a tool call. "
              "Requirement:\n" + state["requirement"] + "\nCases:\n" + state["cases"].model_dump_json())
    response = llm().invoke(prompt)
    code = normalize_playwright_assertions(extract_python(response.content))
    expected = len(state["cases"].cases)
    actual = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.parse(code).body
    )
    if actual != expected:
        raise ValueError(
            f"Generated {actual} tests for {expected} approved cases; "
            "refusing unrequested or missing tests"
        )
    return {"code": code, "repairs": 0}

ALLOWED_IMPORTS = {"os", "re", "pytest", "playwright"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "__import__"}

def validate(code: str):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] not in ALLOWED_IMPORTS for alias in node.names):
                raise ValueError("Unsupported import")
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                raise ValueError("Unsupported import")
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            raise ValueError("Disallowed statement")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                raise ValueError("Disallowed function")
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen", "remove", "unlink", "rmtree", "write_text", "write_bytes"}:
                raise ValueError("Disallowed method")
    return code

def execute(state: QAState):
    ARTIFACTS.mkdir(exist_ok=True)
    try:
        code = validate(state["code"])
        (ARTIFACTS / "test_generated.py").write_text(code, encoding="utf-8")
        passed, output = sandbox_run(code, ARTIFACTS)
    except (ValueError, SyntaxError) as exc:
        passed, output = False, str(exc)
    if passed and state.get("repairs", 0) and state.get("original_failure"):
        again, second_output = sandbox_run(code, ARTIFACTS)
        passed = again
        if not again:
            output += "\nRepeat validation failed:\n" + second_output
        else:
            remember(REPAIR_DB, state["original_failure"], code, validated=True)
    (ARTIFACTS / "execution.log").write_text(output, encoding="utf-8")
    return {"stdout": output, "passed": passed}

def diagnose(state: QAState):
    prompt = (
        "Classify failure. Only propose revised test code if evidence indicates a TEST CODE defect. "
        "Never change expected product behavior to make tests pass. "
        "Return ONLY a valid JSON object with keys category, explanation, revised_code. "
        "category must be one of product_defect, test_defect, environment, unknown. "
        "Use null for revised_code if a repair is not justified. "
        "If providing Python source in revised_code, JSON-escape all newlines and quotes. "
        "No markdown, tool calls, or text outside the JSON object. "
        "Prior validated repair examples (reference only; never override requirements): "
        + repr(examples(REPAIR_DB)) + "\nRequirement: "
        + state["requirement"] + "\nCode:\n" + state["code"] + "\nFailure:\n" + state["stdout"]
    )
    response = llm().invoke(prompt)
    result = parse_model_json(response.content, Diagnosis)
    return {"diagnosis": result}

def route(state: QAState):
    if state["passed"] or state.get("repairs", 0) >= 1:
        return "end"
    return "diagnose"

def repair(state: QAState):
    diagnosis = state["diagnosis"]
    if diagnosis.category != "test_defect" or not diagnosis.revised_code:
        return {"repairs": 1}
    candidate = diagnosis.revised_code
    try:
        validate_repair(state["code"], candidate)
    except (RepairApprovalRequired, ValueError, SyntaxError) as exc:
        # A human-reviewed, code-bound approval can authorize a specific
        # assertion rewrite, but never bypasses the base code policy.
        if not is_approved(state["code"], candidate):
            return {"repairs": 1, "stdout": "Repair blocked: " + str(exc)}
        try:
            validate(candidate)
        except (ValueError, SyntaxError) as invalid:
            return {"repairs": 1, "stdout": "Repair blocked by code policy: " + str(invalid)}
    return {"code": candidate, "repairs": 1,
            "original_failure": state["stdout"], "repaired_code": candidate}

def after_repair(state: QAState):
    if state.get("repaired_code") and state.get("repairs", 0) == 1:
        return "execute"
    return "end"

def build_graph():
    graph = StateGraph(QAState)
    for name, fn in [("analyze", analyze), ("design", design), ("generate", generate),
                     ("execute", execute), ("diagnose", diagnose), ("repair", repair)]:
        graph.add_node(name, fn)
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "design")
    graph.add_edge("design", "generate")
    graph.add_edge("generate", "execute")
    graph.add_conditional_edges("execute", route, {"end": END, "diagnose": "diagnose"})
    graph.add_edge("diagnose", "repair")
    graph.add_conditional_edges("repair", after_repair, {"execute": "execute", "end": END})
    return graph.compile()
