"""MCP release qualification CLI, distinct from the test generation CLI."""
import argparse
import json
from pathlib import Path
from agentic_qa.mcp_tools import gateway_from_env
from agentic_qa.release_graph import run_release
from agentic_qa.release_governance import QualificationDecision, approve, write_json

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("qualify")
    check.add_argument("release_id")
    check.add_argument("--output", type=Path, default=Path("artifacts/release"))
    review = sub.add_parser("approve")
    review.add_argument("--qualification", type=Path, required=True)
    review.add_argument("--approval", type=Path, required=True)
    review.add_argument("--output", type=Path, default=Path("artifacts/release/approval-result.json"))
    args = parser.parse_args()
    if args.action == "qualify":
        decision = run_release(args.release_id, gateway_from_env(), args.output)
        print(json.dumps(decision, indent=2))
        if decision["recommendation"] != "ready_for_review":
            raise SystemExit(1)
    else:
        decision = QualificationDecision.model_validate_json(args.qualification.read_text(encoding="utf-8"))
        approval = json.loads(args.approval.read_text(encoding="utf-8"))
        outcome = approve(decision, approval)
        write_json(args.output, outcome)
        print(json.dumps(outcome, indent=2))

if __name__ == "__main__":
    main()
