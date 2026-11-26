# MCP-enabled release qualification

This extension complements the existing Groq/Playwright test design and repair graph. It **does not autonomously deploy or certify production releases**.

## Architecture

```text
GitHub repository_dispatch / workflow_dispatch event (release ID)
  -> LangGraph retrieve_evidence
       -> MCP get_defect_evidence(release_id)
       -> MCP get_test_coverage(release_id)
       -> MCP get_failure_diagnostics(release_id)
  -> LangGraph qualify_release
       -> fail-closed JUnit evidence and count reconciliation
       -> calculate required-test coverage
       -> classify unresolved Sev1/Sev2/blocker defects as release blockers
  -> qualification.json + events.jsonl (audit artifacts)
  -> separate reviewer approval bound to exact evidence SHA-256
```

The MCP client uses explicit typed tool calls, allowlisted read-only tool names, an operator-configured stdio server, bounded responses and timeouts. Models do not choose executables or issue approval actions. The included MCP server reads **local demo JSON evidence**, not live Jira, TestRail or CI data. Swap the server for an authenticated, read-only enterprise adapter that implements the three named tool contracts to use real systems.

## Local demo

Install Python 3.11+ and run:

```bash
pip install -r requirements-release.txt
export QA_MCP_COMMAND=python
export QA_MCP_ARGS_JSON='["-m", "agentic_qa.mcp_server"]'
python release_cli.py qualify demo-1
python -m pytest -q tests
```

The example snapshot passes the deterministic checks and returns `ready_for_review`. It is **not** automatically approved.

The event-driven workflow is `.github/workflows/release-qualification.yml`: trigger manually, or send an authenticated GitHub `repository_dispatch` event of type `qa-release-candidate` with `client_payload.release_id`. The workflow performs only evaluation and evidence upload; it never deploys. Evidence snapshots must be supplied from a trusted source for release IDs other than `demo-1`.

For explicit reviewer sign-off, write a JSON file with fields `release_id`, `evidence_sha256` (from `qualification.json`), `reviewer`, and `decision: "approve"`, then run:

```bash
python release_cli.py approve --qualification artifacts/release/qualification.json --approval path/to/reviewed-approval.json
```

A locally typed reviewer name is **not identity verification**. In production, gate that separate approval invocation behind a protected GitHub Environment with required reviewers or another authenticated authorization service. Store approval and evidence records durably and enforce trusted provenance and immutability. Never use the demonstration CLI as a deployment permission system.

## Current limitations

Events are GitHub-triggered and journaled locally, not delivered through a durable message broker. The gateway starts a new MCP stdio session for each read. Failure diagnostics are retrieved as structured evidence; the existing test-execution LangGraph diagnoses code/test failures, while release qualification applies deterministic gates. Live integrations, authenticated evidence sources, stronger data provenance, concurrency/idempotency hardening, and production-grade monitoring are future work. This remains a prototype.
