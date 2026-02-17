"""
Parser for Tracker Schema v1.

Hierarchy:
  Workstream
    └── Track
          ├── Milestone
          ├── Milestone
          └── Milestone

Required columns:
  WorkType, Description, Status, Target Date, Milestone Owner,
  Jira ID, Notes, Status Update, Comments
"""

from typing import Any

REQUIRED_COLUMNS = [
    "WorkType",
    "Description",
    "Status",
    "Target Date",
    "Milestone Owner",
    "Jira ID",
    "Notes",
    "Status Update",
    "Comments",
]


def validate_schema(headers: list[str]) -> list[str]:
    """Validate that all required columns exist. Returns list of missing columns."""
    missing = [col for col in REQUIRED_COLUMNS if col not in headers]
    return missing


def parse_sheet_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Parse flat sheet rows into hierarchical structure.
    """
    workstream = None
    current_track = None
    tracks: list[dict[str, Any]] = []

    for row in rows:
        work_type = (row.get("WorkType") or "").strip()

        if work_type == "Workstream":
            workstream = (row.get("Description") or "").strip()

        elif work_type == "Track":
            current_track = {
                "workstream": workstream or "",
                "track": (row.get("Description") or "").strip(),
                "track_status": (row.get("Status") or "").strip(),
                "notes_link": (row.get("Notes") or "").strip(),
                "milestones": [],
            }
            tracks.append(current_track)

        elif work_type == "Milestone" and current_track is not None:
            jira_id = (row.get("Jira ID") or "").strip()
            if not jira_id:
                continue  # Skip milestones without Jira IDs

            milestone = {
                "name": (row.get("Description") or "").strip(),
                "status": (row.get("Status") or "").strip(),
                "target_date": (row.get("Target Date") or "").strip(),
                "owner": (row.get("Milestone Owner") or "").strip(),
                "jira_id": jira_id,
                "previous_status_update": (row.get("Status Update") or "").strip(),
            }
            current_track["milestones"].append(milestone)

    return tracks
