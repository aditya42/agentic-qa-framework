# Low-Level Design (LLD)

**Status:** Documents existing code and proposed production contracts.

## 1. Current repository modules
| Module | Responsibility | Current implementation |
|---|---|---|
| `main.py` | CLI entry point, model preflight, integration flags, exit status | Implemented |
| `agentic_qa/graph.py` | LangGraph state, nodes, routing, AST filter | Implemented |
| `agentic_qa/models.py` | Case, Cases, Diagnosis Pydantic schemas | Implemented |
| `agentic_qa/model_access.py` | Verify configured Groq model | Implemented |
| `agentic_qa/sandbox.py` | Run Pytest inside Docker | Implemented, needs egress hardening |
| `agentic_qa/learning.py` | SQLite validated repair examples | Local-only |
| `agentic_qa/integrations.py` | Optional Jira and TestRail publishing | Basic, no idempotency |
| `tests/` | Unit tests for parser, policy and learning | Partial |
| `.github/workflows/qa.yml` | CI unit job and manual agentic job | Implemented |

## 2. Proposed package layout
```text
agentic_qa/
  graph.py                # orchestration, conditional edges
  models.py               # Pydantic schemas
  config.py               # typed settings and approved targets (new)
  policy.py               # URL, code, repair and publication policies (new)
  model_access.py         # Groq model preflight
  sandbox.py              # disposable execution
  evidence.py             # JUnit parsing, JSON summary, artifact manifests (new)
  learning.py             # validated repair memory
  integrations.py         # Jira/TestRail adapters
  audit.py                # structured sanitized events (new)
  agents/                 # split out if graph.py becomes difficult to maintain
docs/
  01-requirements.md
  02-hld.md
  03-lld.md
  04-security-operations.md
```
Avoid introducing extra services or agents without a measurable need.

## 3. LangGraph state contract
Existing fields: `requirement: str`, `analysis: str`, `cases: Cases`, `code: str`, `stdout: str`, `passed: bool`, `diagnosis: Diagnosis`, `repairs: int`, `original_failure: str`.

Target additional fields:
```python
class RunMetadata(BaseModel):
    run_id: str
    requirement_sha256: str
    model_id: str
    target_url: str
    started_at: str
    trace_id: str

class ExecutionResult(BaseModel):
    status: Literal["passed", "failed", "blocked", "error"]
    total: int
    passed: int
    failed: int
    skipped: int
    duration_ms: int
    junit_path: str | None
    evidence_sha256: str | None

class Decision(BaseModel):
    action: Literal["execute", "repair", "stop", "request_approval"]
    reason: str
    policy_version: str
```

Use immutable run metadata and explicitly typed stage outputs rather than parsing free-form console output.

## 4. Graph transitions
```text
START -> analyze -> design -> generate -> validate -> execute
execute(pass) -> report -> END
execute(fail, repair_budget>0, category=test_defect) -> repair -> validate -> execute
execute(fail, other category) -> report -> END
validate(deny) -> report(blocked) -> END
model_error -> report(error) -> END
```
The current implementation has validation embedded in `execute`; extraction into a policy node is recommended.

### Invariants
- `repairs <= max_repairs` (default 1).
- Never turn a product defect into a test-code repair.
- Two passing validations required before learning.
- A successful graph traversal does not imply successful tests.
- No test may be executed on the host as a fallback.
- Repair history is advisory data, not trusted instructions.

## 5. API and command contracts
Current CLI:
```bash
python main.py examples/login.txt
python main.py examples/login.txt --publish-testrail
python main.py examples/login.txt --create-jira-bug
```

Proposed CLI extensions:
```text
--target-url <approved URL>
--max-repairs <0..2>
--run-id <uuid>
--report-json <path>
--dry-run-publish
```
These flags are **not yet implemented**.

Proposed report JSON:
```json
{
  "schema_version": "1.0",
  "run_id": "uuid",
  "requirement_sha256": "hex",
  "model_id": "openai/gpt-oss-120b",
  "status": "failed",
  "case_count": 5,
  "execution": {"passed": 0, "failed": 5, "skipped": 0},
  "repair_attempts": 1,
  "diagnosis_category": "test_defect",
  "artifact_paths": ["artifacts/junit.xml", "artifacts/execution.log"]
}
```

## 6. Execution sandbox
Current command invokes `docker run` with read-only filesystem, dropped capabilities, no-new-privileges, CPU/memory/PID limits, and mounted source/evidence directories. It currently uses `--network=bridge`, which is **not a production egress policy**.

Target execution controls:
- Runner isolated from sensitive corporate network.
- Network access restricted to explicitly approved target and necessary DNS via firewall/proxy.
- Ephemeral nonroot UID, no Docker socket mount, no privileged containers.
- Timeouts, output-size limits, disk quotas and ephemeral test identities.
- Run-specific artifact directory to prevent evidence overwrites.
- Image pinned by digest, scanned, signed and updated through reviewed PRs.

## 7. Repair memory schema
Current SQLite table: `repairs(id, signature, failure_excerpt, repair_excerpt, validated_at)`.

Proposed durable schema:
```sql
CREATE TABLE repair_examples (
  id TEXT PRIMARY KEY,
  requirement_hash TEXT NOT NULL,
  failure_signature TEXT NOT NULL,
  code_before_hash TEXT NOT NULL,
  code_after_hash TEXT NOT NULL,
  classification TEXT NOT NULL,
  validation_count INTEGER NOT NULL,
  approved_by TEXT,
  approval_timestamp TEXT,
  status TEXT NOT NULL CHECK (status IN ('proposed','approved','revoked')),
  created_at TEXT NOT NULL
);
CREATE INDEX ix_repair_signature ON repair_examples(failure_signature, status);
```
Only approved examples with `validation_count >= 2` may be retrieved. Use parameterized queries and support revocation.

## 8. Integration contracts
**Jira:** `publish_jira(summary, description) -> issue_key`. Future: lookup by deterministic fingerprint before create; rate-limit handling, retries with backoff, redaction and structured failure status. An LLM diagnosis alone is insufficient to create a production bug.

**TestRail:** `publish_testrail(cases) -> list[int]`. Future: stable external IDs, upsert behavior, field-template compatibility and rollback/reconciliation for partial publishing.

Never log tokens or credentials. Publish only when explicit workflow flags and approval policy both permit it.

## 9. Error taxonomy
| Error | Result | Retry |
|---|---|---|
| Invalid requirement | blocked | No |
| Model unavailable/auth failure | error | No until config fixed |
| Model timeout/429 | error | Bounded exponential backoff |
| Invalid generated Python | blocked or test_defect | One bounded regeneration |
| Sandbox unavailable | error | No host fallback |
| Test assertion failure | failed | Diagnose; repair only test defects |
| Application defect | failed | No automatic expectation rewrite |
| Jira/TestRail outage | publish_failed | Retry with idempotency key |

## 10. Testing strategy
- Unit: schema validation, policy deny/allow, route decisions, CLI exit codes.
- Contract: mocked Groq responses, Jira/TestRail request/response schema.
- Integration: Docker sandbox with known passing/failing test modules.
- Security: malicious generated code, disallowed imports, prohibited egress, secrets in logs.
- E2E: fixed SauceDemo login acceptance criteria with deterministic evidence.
- Regression: verify known previously repaired cases remain stable.

## 11. Observability
Emit JSON events for `run_started`, `cases_generated`, `code_validated`, `execution_completed`, `repair_proposed`, `repair_validated`, `run_finished`. Include run ID, stage, elapsed time, outcome, model ID and policy decision; redact inputs and secrets. Measure test pass rate, invalid-generation rate, repair success rate, false-green rate, token consumption and cost.

## 12. Implementation checklist
See [SRS](01-requirements.md) and [Operations](04-security-operations.md). Mark features implemented only after corresponding automated tests and a reproducible CI run.
