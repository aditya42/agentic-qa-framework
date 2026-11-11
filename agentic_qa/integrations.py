"""Explicit opt-in Jira and TestRail publishing."""
import os
import hashlib
import requests

def require_approval():
    if os.getenv("QA_PUBLISH_APPROVED") != "true":
        raise PermissionError("External publishing requires QA_PUBLISH_APPROVED=true after human approval")


def publish_jira(summary: str, description: str) -> str:
    require_approval()
    base = os.environ["JIRA_BASE_URL"].rstrip("/")
    project = os.environ["JIRA_PROJECT_KEY"]
    fingerprint = hashlib.sha256((project + ":" + summary).encode()).hexdigest()[:16]
    label = "agentic-qa-" + fingerprint
    search = requests.get(f"{base}/rest/api/2/search",
                          params={"jql": f'project = "{project}" AND labels = "{label}"', "maxResults": 1},
                          auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]), timeout=20)
    search.raise_for_status()
    existing = search.json().get("issues", [])
    if existing:
        return existing[0]["key"]
    payload = {"fields": {"project": {"key": os.environ["JIRA_PROJECT_KEY"]},
               "summary": summary[:255], "description": description[:30000],
               "issuetype": {"name": os.getenv("JIRA_ISSUE_TYPE", "Bug")}, "labels": [label]}}
    response = requests.post(f"{base}/rest/api/2/issue", json=payload,
                             auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]), timeout=20)
    response.raise_for_status()
    return response.json()["key"]

def publish_testrail(cases: list[dict]) -> list[int]:
    require_approval()
    base = os.environ["TESTRAIL_BASE_URL"].rstrip("/")
    section = int(os.environ["TESTRAIL_SECTION_ID"])
    auth = (os.environ["TESTRAIL_EMAIL"], os.environ["TESTRAIL_API_KEY"])
    project = os.environ["TESTRAIL_PROJECT_ID"]
    existing_titles = {}
    offset = 0
    while True:
        response = requests.get(
            f"{base}/index.php?/api/v2/get_cases/{project}&section_id={section}&limit=250&offset={offset}",
            auth=auth, timeout=20)
        response.raise_for_status()
        payload = response.json()
        batch = payload if isinstance(payload, list) else payload.get("cases", [])
        for item in batch:
            existing_titles[item["title"]] = item["id"]
        if len(batch) < 250:
            break
        offset += len(batch)
    created = []
    for case in cases:
        if case["title"] in existing_titles:
            created.append(existing_titles[case["title"]])
            continue
        payload = {"title": case["title"], "custom_steps": "\n".join(case["steps"]),
                   "custom_expected": "\n".join(case["expected"])}
        response = requests.post(f"{base}/index.php?/api/v2/add_case/{section}",
                                 json=payload, auth=auth, timeout=20)
        response.raise_for_status()
        created.append(response.json()["id"])
    return created
