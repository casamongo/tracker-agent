"""
Google Sheets service.

Reads tracker spreadsheet data using a service account.
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import GOOGLE_SERVICE_ACCOUNT_FILE

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _get_sheets_service():
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=credentials)


def read_sheet(sheet_id: str, range_name: str = "Sheet1") -> list[dict[str, str]]:
    """
    Read all rows from a Google Sheet and return as list of dicts.

    The first row is treated as headers. Each subsequent row becomes a dict
    keyed by the header values.
    """
    service = _get_sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_name)
        .execute()
    )

    values = result.get("values", [])
    if len(values) < 2:
        return []

    headers = values[0]
    rows: list[dict[str, str]] = []

    for row_values in values[1:]:
        row_dict: dict[str, str] = {}
        for i, header in enumerate(headers):
            row_dict[header] = row_values[i] if i < len(row_values) else ""
        rows.append(row_dict)

    return rows


def update_cell(sheet_id: str, range_name: str, value: str) -> None:
    """
    Write a single value to a specific cell in the sheet.
    """
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=credentials)

    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption="RAW",
        body={"values": [[value]]},
    ).execute()
