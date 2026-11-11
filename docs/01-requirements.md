# Software Requirements Specification (SRS)

**System:** Agentic QA Automation Framework  
**Status:** Target production requirements (not all implemented)  
**Version:** 1.0

## 1. Purpose and scope
Convert authorized, version-controlled functional requirements into traceable automated browser tests using a multi-agent workflow. Generate and validate executable tests, run them in an isolated environment, diagnose failures, optionally propose repairs, and produce auditable quality evidence. The initial implementation targets web UI via Python Playwright; API, mobile and TypeScript adapters are future extensions.

## 2. Stakeholders and roles
- **QE Architect:** defines governance, coverage strategy and quality gates.
- **QA Engineer:** submits requirements, reviews cases and proposed repairs.
- **Release Owner:** approves promotion and release decisions.
- **Platform Administrator:** manages runners, credentials, outbound network controls and retention.
- **CI service account:** runs approved pipelines with least privilege.

## 3. Functional requirements
| ID | Requirement | Priority | Acceptance criteria | Current status |
|---|---|---|---|---|
| FR-01 | Accept requirements from a UTF-8 file | P0 | Missing/unreadable input exits nonzero; input is recorded by digest | Partial |
| FR-02 | Analyze testable behavior and ambiguity | P0 | Analysis identifies assumptions; unsupported expectations not invented | Implemented, LLM-based |
| FR-03 | Produce structured positive/negative/boundary cases | P0 | Cases validate against Pydantic schema, bounded count | Partial |
| FR-04 | Maintain requirement-to-case-to-script traceability | P0 | Stable IDs in execution report and case catalog | Planned |
| FR-05 | Generate valid Playwright/Pytest code | P0 | Parser and policy checks pass before execution | Partial |
| FR-06 | Execute generated code only inside a restricted sandbox | P0 | No host execution fallback; resource limits and restricted egress | Partial; egress not restricted |
| FR-07 | Report per-test status and JUnit evidence | P0 | CI status reflects test result, not graph completion | Partial |
| FR-08 | Classify failure as test, product, environment or unknown | P0 | Evidence-based category and explanation | Implemented, LLM-based |
| FR-09 | Attempt bounded test-only repair | P1 | Max one attempt by default; never silently weaken expectations | Partial |
| FR-10 | Validate repair on two executions | P1 | Both runs pass before marking repair validated | Implemented locally |
| FR-11 | Require approval before publishing or merging repairs | P0 | No autonomous merge or production promotion | Planned |
| FR-12 | Publish to Jira/TestRail on explicit opt-in | P1 | Credentials scoped; duplicate suppression and retry policy | Partial; duplicate suppression absent |
| FR-13 | Persist validated repair knowledge across CI runs | P1 | Durable, versioned, reviewable, revocable records | Planned; local SQLite only |
| FR-14 | Support GitHub Actions invocation | P0 | Manual QA run and automatic static/unit CI | Implemented |
| FR-15 | Enforce approved target host | P0 | Reject unauthorized or production target before browser starts | Partial: CLI preflight only; no egress enforcement |
| FR-16 | Export run summary and audit trail | P0 | Run ID, model ID, input hash, code hash, result, decisions | Planned |

## 4. Nonfunctional requirements
| ID | Quality attribute | Target |
|---|---|---|
| NFR-01 | Security | No unrestricted shell; sandbox with enforced egress allowlist and no long-lived credentials |
| NFR-02 | Reliability | Explicit failure on incomplete execution, invalid evidence, or failed tests |
| NFR-03 | Reproducibility | Pinned dependencies, immutable container digest, recorded model/config versions |
| NFR-04 | Observability | Structured events, trace IDs, sanitized logs and evidence |
| NFR-05 | Performance | Configurable 180-second test execution budget; measured p50/p95 per stage |
| NFR-06 | Cost | Configurable model request budget, per-run token/cost metrics and retry caps |
| NFR-07 | Availability | CI runs independently; no mandatory database service for local use |
| NFR-08 | Maintainability | Unit tests for deterministic modules, typed contracts, small single-purpose modules |
| NFR-09 | Privacy | Redact secrets and personal data from prompts, logs and artifacts |
| NFR-10 | Retention | Configurable retention and deletion policy; no indefinite artifact storage |
| NFR-11 | Portability | Python 3.11+ and Linux Docker runners; documented Windows/macOS developer setup |
| NFR-12 | Governance | Human approval for changes to requirements, test expectations and releases |

Targets are proposed SLOs, not measured guarantees.

## 5. End-to-end acceptance scenarios
1. Valid login requirement yields valid cases and browser tests; JUnit XML is produced and the CI job passes only if tests pass.
2. A generated test has a syntax or unsupported-import error; execution is blocked, evidence retained and CI fails.
3. A locator/assertion defect is detected; one repair is proposed and executed twice; failure on either attempt blocks success.
4. A genuine application failure is classified as product defect; expected behavior is preserved and no silent repair is accepted.
5. A missing Groq key or unavailable model produces a clear preflight error before generation.
6. A prohibited target URL or attempted unauthorized egress is blocked before a browser connection.
7. An integration is unavailable; core results remain preserved and publishing is reported as a separate status.
8. A previously approved repair can be revoked; revoked examples are excluded from future retrieval.

## 6. Out of scope for initial production release
Autonomous merging, production-environment testing, unconstrained internet browsing, automatic secret discovery, self-modifying policy, unrestricted code execution, and deployment to live customer systems.

## 7. Release gates
- All unit, integration and sandbox policy tests pass.
- At least one controlled end-to-end test run passes with real browser evidence.
- CI reports failed tests as failure; no false-green builds.
- Threat model and network egress restrictions validated.
- Credentials, dependencies and supply-chain controls reviewed.
- Jira/TestRail idempotency, audit logs and approval policy validated before enabling publishing.
- Security review and QE owner sign-off recorded.
