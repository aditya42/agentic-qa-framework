# Agentic QA Automation Framework

LangChain + LangGraph + Groq + Python + Playwright + Pytest. This is a proof of concept, not a production-certified autonomous test runner.

## Workflow
Functional requirements -> requirement analysis -> test design -> Python Playwright generation -> AST validation -> Docker execution -> failure diagnosis -> at most one repair -> re-execution -> JUnit evidence.

## Quick start
Requires Python 3.11+, Docker, and a Groq API key.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GROQ_API_KEY
docker build -f Dockerfile.sandbox -t agentic-qa-sandbox:local .
python main.py examples/login.txt
```

On Windows, activate with `.venv\\Scripts\\activate`. The Docker image already contains Playwright browsers; host browser installation is not needed.

## Optional integrations
TestRail: set TESTRAIL_BASE_URL, TESTRAIL_SECTION_ID, TESTRAIL_EMAIL, TESTRAIL_API_KEY and invoke `python main.py examples/login.txt --publish-testrail`.

Jira: set JIRA_BASE_URL, JIRA_PROJECT_KEY, JIRA_EMAIL, JIRA_API_TOKEN (and optionally JIRA_ISSUE_TYPE) and invoke `python main.py examples/login.txt --create-jira-bug`. Jira issues are attempted only for LLM-classified product defects. Verify defects manually before enabling this flag.

## GitHub Actions
The push/PR job runs unit tests and builds the sandbox image. The manually dispatched job also runs Groq-driven test generation. Create a GitHub environment named `qa`; add `GROQ_API_KEY` as a repository/environment secret and `BASE_URL` as a variable. Configure `QA_ALLOWED_HOSTS` with an explicit comma-separated list of approved hosts (default in sample: `www.saucedemo.com`). The CLI rejects unauthorized `BASE_URL` hosts before model calls. Optionally set environment variable `GROQ_MODEL=openai/gpt-oss-120b` to override the default. The old `llama-3.3-70b-versatile` model was retired for standard accounts in August 2026. Startup validates the model against Groq's available-models endpoint. Do not commit credentials.

## Repair memory
Validated repairs are stored in `artifacts/repairs.sqlite3`. A repair is remembered after two successful runs of the revised test. This database is **local to the runner**; GitHub-hosted runners do not preserve it across runs. External durable storage or an explicitly reviewed artifact restore process is needed for persistent cross-run learning in CI.

## Security limitations
The AST check is a basic filter, **not** a security boundary. Docker restricts capabilities, processes, memory, CPU and filesystem access, but the default bridge network still permits outbound access. Run generated tests only against an authorized test target. For a production rollout, enforce destination allowlisting via a controlled egress proxy/firewall, use an isolated runner, avoid passing secrets into generated code, pin dependency/action versions, and review any automated repair before merging. Do not run this framework against sensitive production systems.

## Tests
```bash
python -m pytest -q tests
```

The code has not been verified against a live Groq API, Jira, TestRail, or end-to-end browser execution in this session.

## Architecture documentation
- [Requirements specification](docs/01-requirements.md)
- [High-level design](docs/02-hld.md)
- [Low-level design](docs/03-lld.md)
- [Security and operations](docs/04-security-operations.md)

**Production readiness:** This project is being hardened, but is **not yet production-ready**. The host allowlist is a preflight configuration check only; it does not restrict outbound connections from generated browser code. See the security checklist before deploying on trusted networks.
