# Security, Operations and Production Readiness

**Status:** Required controls and operating procedures; not evidence of compliance.

## Threat model
| Threat | Example | Required mitigation |
|---|---|---|
| Prompt injection | Requirement asks agent to ignore controls | Treat all requirement/repair content as untrusted data; deterministic policy |
| Malicious generated code | Code reads files or exfiltrates data | Isolated runner, deny-by-default egress, read-only mounts, least privilege |
| Oracle corruption | Repair weakens assertion to pass | Assertion-diff policy, approval, double validation |
| Secret leakage | Credentials printed in logs | Secret redaction, short-lived credentials, no secrets in generated scripts |
| Supply-chain compromise | Dependency/action/image changes | Pinned hashes/digests, scanning, review, SBOM |
| Data retention | Logs contain user data | PII scrubbing, access control, retention and deletion |
| Duplicate tickets | Repeated runs create multiple Jira bugs | Fingerprint-based upsert and idempotency |
| Model drift | Provider changes behavior/model availability | Explicit model ID, model preflight, versioned evaluation set |

## Operational runbook
1. Verify GitHub environment `qa`, Groq secret and approved test target.
2. Run unit tests and build the sandbox; inspect CI quality gate.
3. Run manually against an authorized nonproduction target.
4. Review JUnit, generated source and failure evidence.
5. For test-code repairs, review the diff and confirm no expected-result weakening.
6. Approve publishing or merging separately; never auto-merge generated changes.
7. Record run ID, requirement hash, model, code hash and approvals.
8. Revoke a bad repair example and rerun the relevant regression suite.

## Minimum production gate
- [ ] Approved target allowlist enforced in sandbox networking
- [ ] Isolated runner and test-only credentials
- [ ] Secrets redaction and retention policy
- [ ] CI reports failed generated tests as failed
- [ ] Deterministic JUnit parsing and report schema
- [ ] Reproducible dependency and image pinning
- [ ] Audit trail with immutable run IDs
- [ ] Approval before test oracle changes and external publishing
- [ ] Idempotent Jira/TestRail integration
- [ ] Durable, reviewable repair memory with revocation
- [ ] Security tests and controlled end-to-end tests pass
- [ ] Release owner approval

## Incident response
Disable manual agentic workflow and publishing flags; rotate exposed tokens if applicable; preserve sanitized evidence and immutable hashes; identify affected runs; revoke untrusted repair examples; fix and test controls; restore only after QE and security approval.

## Current known gaps
- Docker bridge networking is not an egress allowlist.
- AST validation is not a secure code sandbox by itself.
- SQLite memory is ephemeral on GitHub-hosted runners.
- Jira/TestRail publishing is not idempotent.
- Generated tests may be semantically wrong even if they pass.
- Current GitHub Actions workflow does not enforce the complete production gate.
