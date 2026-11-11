"""Deterministic JUnit parsing and auditable run summaries."""
import hashlib
import json
import os
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

def junit_counts(path: Path) -> dict:
    if not path.is_file():
        return {"status": "missing", "total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    if not cases:
        return {"status": "empty", "total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    failed = sum(case.find("failure") is not None for case in cases)
    errors = sum(case.find("error") is not None for case in cases)
    skipped = sum(case.find("skipped") is not None for case in cases)
    return {"status": "valid", "total": len(cases), "passed": len(cases) - failed - errors - skipped,
            "failed": failed, "errors": errors, "skipped": skipped}

def write_report(artifacts: Path, requirement: str, model: str, result: dict) -> dict:
    artifacts.mkdir(parents=True, exist_ok=True)
    counts = junit_counts(artifacts / "junit.xml")
    passed = result.get("passed") is True and counts["status"] == "valid" and counts["passed"] > 0 and counts["failed"] == 0 and counts["errors"] == 0
    diagnosis = result.get("diagnosis")
    report = {
        "schema_version": "1.0", "run_id": os.getenv("GITHUB_RUN_ID") or str(uuid.uuid4()),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "requirement_sha256": hashlib.sha256(requirement.encode("utf-8")).hexdigest(),
        "model_id": model, "status": "passed" if passed else "failed",
        "case_count": len(result["cases"].cases), "execution": counts,
        "repair_attempts": result.get("repairs", 0),
        "diagnosis_category": diagnosis.category if diagnosis else None,
        "generated_code_sha256": hashlib.sha256(result.get("code", "").encode()).hexdigest(),
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
