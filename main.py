import argparse
import json
import os
from pathlib import Path
from agentic_qa.graph import build_graph
from agentic_qa.integrations import publish_jira, publish_testrail
from agentic_qa.model_access import verify_model
from agentic_qa.policy import validate_target
from agentic_qa.evidence import write_report
from agentic_qa.audit import record

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("requirement", type=Path)
    parser.add_argument("--publish-testrail", action="store_true")
    parser.add_argument("--create-jira-bug", action="store_true")
    args = parser.parse_args()
    validate_target(os.getenv('BASE_URL', 'https://www.saucedemo.com'))
    model = verify_model()
    print(f"Groq model access verified: {model}", flush=True)
    requirement = args.requirement.read_text(encoding="utf-8")
    run_id = os.getenv("GITHUB_RUN_ID", "local")
    record(Path("artifacts/audit.jsonl"), run_id=run_id, event="run_started", status="started")
    result = build_graph().invoke({"requirement": requirement, "repairs": 0})
    report = write_report(Path("artifacts"), requirement, model, result)
    record(Path("artifacts/audit.jsonl"), run_id=run_id, event="run_finished",
           status=report["status"], details={"case_count": report["case_count"], "repair_attempts": report["repair_attempts"]})
    diagnosis = result.get("diagnosis")
    print(json.dumps({"passed": result.get("passed"), "cases": len(result["cases"].cases),
                      "repairs": result.get("repairs", 0),
                      "diagnosis": {"category": diagnosis.category, "explanation": diagnosis.explanation} if diagnosis else None}, indent=2))
    if args.publish_testrail:
        print("TestRail case IDs:", publish_testrail([case.model_dump() for case in result["cases"].cases]))
    if args.create_jira_bug and not result.get("passed") and result.get("diagnosis") and result["diagnosis"].category == "product_defect":
        print("Jira issue:", publish_jira("Agentic QA: possible product defect", result["stdout"]))
    print("Artifacts: artifacts/test_generated.py, artifacts/execution.log, artifacts/junit.xml (if pytest ran)")
    if report["status"] != "passed":
        raise SystemExit("Agentic QA tests did not pass; see qa-evidence artifact")

if __name__ == "__main__":
    main()
