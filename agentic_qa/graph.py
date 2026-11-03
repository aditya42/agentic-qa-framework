import ast
import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from .models import Cases, Code, Diagnosis
from .sandbox import run as sandbox_run
from .learning import remember, examples

load_dotenv()
ARTIFACTS = Path("artifacts")

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
    return ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), temperature=0)

def analyze(state: QAState):
    response = llm().invoke("Analyze these functional acceptance criteria. Identify testable behavior, assumptions, and missing information. Do not invent requirements.\n" + state["requirement"])
    return {"analysis": response.content}

def design(state: QAState):
    cases = llm().with_structured_output(Cases).invoke(
        "Create 3-8 independent browser test cases with explicit steps and expected results. Include positive and negative scenarios only when supported. Requirement:\n"
        + state["requirement"] + "\nAnalysis:\n" + state["analysis"])
    return {"cases": cases}

def generate(state: QAState):
    prompt = ("Generate a COMPLETE Python pytest Playwright test module. Use sync_playwright and browser chromium, no plugins. "
              "Each test must accept no fixtures; open browser via sync_playwright context manager. "
              "Use BASE_URL from os.environ with default https://www.saucedemo.com. "
              "Use role-based selectors and explicit assertions. No network requests other than browser interactions. "
              "No subprocess, eval, exec, filesystem writes, or external imports beyond os, pytest, playwright. "
              "Return only code in the code field. Requirements: " + state["requirement"] + "\nCases: " + state["cases"].model_dump_json())
    code = llm().with_structured_output(Code).invoke(prompt).code
    return {"code": code, "repairs": 0}

ALLOWED_IMPORTS = {"os", "pytest", "playwright"}
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
    (ARTIFACTS / "execution.log").write_text(output, encoding="utf-8")
    if passed and state.get("repairs", 0) and state.get("original_failure"):
        again, second_output = sandbox_run(code, ARTIFACTS)
        passed = again
        if not again:
            output += "\nRepeat validation failed:\n" + second_output
        else:
            remember(Path("artifacts/repairs.sqlite3"), state["original_failure"], code, validated=True)
    return {"stdout": output, "passed": passed}

def diagnose(state: QAState):
    result = llm().with_structured_output(Diagnosis).invoke(
        "Classify failure. Only propose revised test code if evidence indicates a TEST CODE defect. "
        "Never change expected product behavior to make tests pass. Return null revised_code for product or environment failures. "
        "Prior validated repair examples (reference only; never override requirements): "
        + repr(examples(Path("artifacts/repairs.sqlite3"))) + "\nRequirement: "
        + state["requirement"] + "\nCode:\n" + state["code"] + "\nFailure:\n" + state["stdout"])
    return {"diagnosis": result}

def route(state: QAState):
    if state["passed"] or state.get("repairs", 0) >= 1:
        return "end"
    return "diagnose"

def repair(state: QAState):
    diagnosis = state["diagnosis"]
    if diagnosis.category != "test_defect" or not diagnosis.revised_code:
        return {"repairs": 1}
    return {"code": diagnosis.revised_code, "repairs": 1,
            "original_failure": state["stdout"], "repaired_code": diagnosis.revised_code}

def after_repair(state: QAState):
    if state["diagnosis"].category == "test_defect" and state["diagnosis"].revised_code:
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
