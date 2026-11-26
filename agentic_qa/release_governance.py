"""Deterministic release-quality gate; human approval never delegated to agents."""
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field

class QualificationInput(BaseModel):
    release_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    report: dict[str, Any]
    defects: list[dict[str, Any]] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    executed_tests: list[str] = Field(default_factory=list)

class QualificationDecision(BaseModel):
    release_id: str
    recommendation: Literal["ready_for_review", "blocked"]
    reasons: list[str]
    coverage_percent: float
    evidence_sha256: str
    human_approval_required: bool = True

def qualify(data: QualificationInput) -> QualificationDecision:
    reasons = []
    counts = data.report.get("execution")
    if not isinstance(counts, dict) or counts.get("status") != "valid":
        reasons.append("Missing or invalid JUnit execution evidence")
        counts = {}
    fields = [counts.get(k) for k in ("total", "passed", "failed", "errors", "skipped")]
    if any(type(n) is not int or n < 0 for n in fields) or (all(type(n) is int for n in fields) and sum(fields[1:]) != fields[0]):
        reasons.append("Invalid test count totals")
    total, passed, failed, errors, skipped = fields
    if type(total) is not int or total <= 0:
        reasons.append("No executed test cases")
    if data.report.get("status") != "passed" or type(passed) is not int or passed <= 0 or failed != 0 or errors != 0 or skipped != 0:
        reasons.append("Test results are not fully passing")
    required = set(data.required_tests)
    executed = set(data.executed_tests)
    if not required:
        reasons.append("No required test inventory provided")
    missing = sorted(required - executed)
    if missing:
        reasons.append(f"{len(missing)} required tests lack execution evidence")
    coverage = round(100 * len(required & executed) / len(required), 2) if required else 0.0
    if coverage < 100:
        reasons.append("Required test coverage is below 100%")
    unresolved = [d for d in data.defects if str(d.get("severity", "")).lower() in ("critical", "blocker", "sev1", "sev2") and str(d.get("status", "")).lower() not in ("closed", "resolved", "done")]
    if unresolved:
        reasons.append(f"{len(unresolved)} unresolved high-severity defects")
    digest = hashlib.sha256(json.dumps(data.model_dump(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return QualificationDecision(release_id=data.release_id, recommendation="blocked" if reasons else "ready_for_review", reasons=reasons, coverage_percent=coverage, evidence_sha256=digest)

def approve(decision: QualificationDecision, approval: dict[str, Any]) -> dict[str, Any]:
    if decision.recommendation != "ready_for_review":
        raise PermissionError("Blocked qualification cannot be approved")
    if approval.get("release_id") != decision.release_id or not hmac.compare_digest(str(approval.get("evidence_sha256", "")), decision.evidence_sha256):
        raise PermissionError("Approval is not bound to current evidence")
    reviewer = approval.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip() or reviewer.lower() in ("agent", "automation", "system"):
        raise PermissionError("Named human reviewer required")
    if approval.get("decision") != "approve":
        raise PermissionError("Release not approved")
    return {"release_id": decision.release_id, "status": "approved_by_human", "reviewer": reviewer, "evidence_sha256": decision.evidence_sha256, "recorded_at": datetime.now(timezone.utc).isoformat()}

def write_json(path: Path, payload: BaseModel | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload.model_dump() if isinstance(payload, BaseModel) else payload, indent=2), encoding="utf-8")
