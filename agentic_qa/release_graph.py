"""Separate LangGraph release qualification workflow with event journal."""
import json
from pathlib import Path
from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph
from .mcp_tools import MCPToolGateway, ToolCall
from .release_governance import QualificationInput, qualify

class ReleaseState(TypedDict, total=False):
    release_id: str
    evidence: dict[str, Any]
    assessment: dict[str, Any]
    events: list[dict[str, str]]

def build_release_graph(gateway: MCPToolGateway):
    graph = StateGraph(ReleaseState)

    def retrieve(state: ReleaseState):
        rid = state["release_id"]
        evidence = {}
        for name in ("get_defect_evidence", "get_test_coverage", "get_failure_diagnostics"):
            evidence[name] = gateway.call(ToolCall(name=name, arguments={"release_id": rid}))
            if evidence[name].get("release_id") != rid:
                raise ValueError("MCP server returned evidence for a different release")
        return {"evidence": evidence, "events": [{"event": "evidence_retrieved", "release_id": rid}]}

    def assess(state: ReleaseState):
        evidence = state["evidence"]
        defects, coverage, execution = [evidence[k] for k in ("get_defect_evidence", "get_test_coverage", "get_failure_diagnostics")]
        if not isinstance(defects.get("defects"), list) or not isinstance(coverage.get("required_tests"), list) or not isinstance(coverage.get("executed_tests"), list) or not isinstance(execution.get("report"), dict):
            raise ValueError("Required MCP evidence is missing or malformed")
        data = QualificationInput(release_id=state["release_id"], report=execution["report"], defects=defects["defects"], required_tests=coverage["required_tests"], executed_tests=coverage["executed_tests"])
        decision = qualify(data)
        return {"assessment": decision.model_dump(), "events": state.get("events", []) + [{"event": "release_qualified", "release_id": state["release_id"], "status": decision.recommendation}]}

    graph.add_node("retrieve_evidence", retrieve)
    graph.add_node("qualify_release", assess)
    graph.add_edge(START, "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "qualify_release")
    graph.add_edge("qualify_release", END)
    return graph.compile()

def run_release(release_id: str, gateway: MCPToolGateway, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = build_release_graph(gateway).invoke({"release_id": release_id, "events": []})
    (output_dir / "qualification.json").write_text(json.dumps(result["assessment"], indent=2), encoding="utf-8")
    with (output_dir / "events.jsonl").open("a", encoding="utf-8") as stream:
        for event in result["events"]:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
    return result["assessment"]
