"""Local evidence-backed MCP server, read only and suitable for demos."""
import json
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

server = FastMCP("agentic-qa-evidence")

class ReleaseQuery(BaseModel):
    release_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")

def _load(release_id: str) -> dict:
    ReleaseQuery(release_id=release_id)
    base = Path(os.getenv("QA_EVIDENCE_DIR", "examples/release-evidence")).resolve()
    data = json.loads((base / f"{release_id}.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("release_id") != release_id:
        raise ValueError("Invalid release evidence")
    return data

@server.tool()
def get_defect_evidence(release_id: str) -> dict:
    """Retrieve recorded defects associated with a release."""
    data = _load(release_id)
    return {"release_id": release_id, "defects": data["defects"]}

@server.tool()
def get_test_coverage(release_id: str) -> dict:
    """Retrieve required and executed test IDs for exact coverage analysis."""
    data = _load(release_id)
    return {"release_id": release_id, "required_tests": data["required_tests"], "executed_tests": data["executed_tests"]}

@server.tool()
def get_failure_diagnostics(release_id: str) -> dict:
    """Retrieve JUnit-backed execution report and categorized failure evidence."""
    data = _load(release_id)
    return {"release_id": release_id, "report": data["report"], "failures": data.get("failures", [])}

if __name__ == "__main__":
    server.run(transport="stdio")
