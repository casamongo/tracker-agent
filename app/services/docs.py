"""
Google Docs service.

Reads the full text content of a Google Doc given its URL or document ID.
"""

import re

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import GOOGLE_SERVICE_ACCOUNT_FILE

SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]


def _get_docs_service():
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("docs", "v1", credentials=credentials)


def extract_doc_id(url_or_id: str) -> str:
    """
    Extract the Google Doc ID from a URL or return as-is if already an ID.
    """
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)
    return url_or_id.strip()


def _read_structural_elements(elements: list) -> str:
    """Recursively extract text from Google Docs structural elements."""
    text_parts: list[str] = []

    for element in elements:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            for elem in paragraph.get("elements", []):
                text_run = elem.get("textRun")
                if text_run:
                    text_parts.append(text_run.get("content", ""))

        elif "table" in element:
            table = element["table"]
            for row in table.get("tableRows", []):
                for cell in row.get("tableCells", []):
                    text_parts.append(
                        _read_structural_elements(cell.get("content", []))
                    )

        elif "sectionBreak" in element:
            pass  # skip section breaks

    return "".join(text_parts)


def get_doc_text(url_or_id: str) -> str:
    """
    Fetch the full plain-text content of a Google Doc.
    """
    doc_id = extract_doc_id(url_or_id)
    service = _get_docs_service()
    document = service.documents().get(documentId=doc_id).execute()

    body = document.get("body", {})
    content = body.get("content", [])

    return _read_structural_elements(content)
