"""
Jira service.

Posts comments to Jira issues using the Jira REST API v2.
Uses v2 for broad compatibility with both Jira Cloud and Server/DC.
"""

import requests
from requests.auth import HTTPBasicAuth

from app.config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN


def post_comment(issue_key: str, comment_text: str) -> dict:
    """
    Post a comment to a Jira issue.

    Uses REST API v2 with plain-text body for compatibility
    with both Jira Cloud and Jira Server/Data Center.
    """
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/comment"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

    payload = {"body": comment_text}

    response = requests.post(url, json=payload, headers=headers, auth=auth)

    if response.status_code not in (200, 201):
        raise Exception(
            f"Failed to post comment to {issue_key}: "
            f"{response.status_code} {response.text}"
        )

    return response.json()


def get_issue(issue_key: str) -> dict:
    """
    Fetch basic issue details from Jira.
    """
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"

    headers = {"Accept": "application/json"}
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch issue {issue_key}: "
            f"{response.status_code} {response.text}"
        )

    return response.json()
