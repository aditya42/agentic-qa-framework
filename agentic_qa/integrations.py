"""Explicit opt-in Jira and TestRail publishing."""
import os
import requests

def publish_jira(summary: str, description: str) -> str:
    base = os.environ["JIRA_BASE_URL"].rstrip("/")
    payload = {"fields": {"project": {"key": os.environ["JIRA_PROJECT_KEY"]},
               "summary": summary[:255], "description": description[:30000],
               "issuetype": {"name": os.getenv("JIRA_ISSUE_TYPE", "Bug")}}}
    response = requests.post(f"{base}/rest/api/2/issue", json=payload,
                             auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]), timeout=20)
    response.raise_for_status()
    return response.json()["key"]

def publish_testrail(cases: list[dict]) -> list[int]:
    base = os.environ["TESTRAIL_BASE_URL"].rstrip("/")
    section = int(os.environ["TESTRAIL_SECTION_ID"])
    auth = (os.environ["TESTRAIL_EMAIL"], os.environ["TESTRAIL_API_KEY"])
    created = []
    for case in cases:
        payload = {"title": case["title"], "custom_steps": "\n".join(case["steps"]),
                   "custom_expected": "\n".join(case["expected"])}
        response = requests.post(f"{base}/index.php?/api/v2/add_case/{section}",
                                 json=payload, auth=auth, timeout=20)
        response.raise_for_status()
        created.append(response.json()["id"])
    return created
