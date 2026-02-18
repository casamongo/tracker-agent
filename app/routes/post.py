"""
Post endpoints.

Handles posting approved updates to Jira and writing
leadership summaries back to the tracker sheet.
"""

from fastapi import APIRouter, HTTPException

from app.schemas import PostToJiraRequest, UpdateSheetRequest
from app.services import jira, sheets

router = APIRouter(tags=["post"])


@router.post("/post-to-jira")
def post_to_jira(request: PostToJiraRequest):
    """
    Post an approved comment to a Jira issue.
    """
    try:
        result = jira.post_comment(request.jira_id, request.comment)
        return {"status": "posted", "jira_id": request.jira_id, "response": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to post to Jira {request.jira_id}: {e}",
        )


@router.post("/update-sheet-summary")
def update_sheet_summary(request: UpdateSheetRequest):
    """
    Write a leadership summary to the Status Update column
    of the milestone row identified by its Jira ID.
    """
    try:
        from app.services.parser import normalize_jira_key

        rows = sheets.read_sheet(request.sheet_id)

        # Find the milestone row by matching Jira ID
        normalized_request_id = normalize_jira_key(request.jira_id.strip())
        milestone_row_index = None
        for i, row in enumerate(rows):
            work_type = (row.get("WorkType") or "").strip()
            jira_id = (row.get("Jira ID") or "").strip()
            if work_type == "Milestone" and normalize_jira_key(jira_id) == normalized_request_id:
                # +2 because: +1 for header row, +1 for 1-based indexing
                milestone_row_index = i + 2
                break

        if milestone_row_index is None:
            raise HTTPException(
                status_code=404,
                detail=f"Milestone with Jira ID '{request.jira_id}' not found in sheet.",
            )

        # Find the Status Update column letter
        headers = list(rows[0].keys())
        if "Status Update" not in headers:
            raise HTTPException(
                status_code=400,
                detail="Sheet does not have a 'Status Update' column.",
            )

        col_index = headers.index("Status Update")
        col_letter = chr(ord("A") + col_index)  # Works for columns A-Z

        cell_range = f"Sheet1!{col_letter}{milestone_row_index}"
        sheets.update_cell(request.sheet_id, cell_range, request.leadership_summary)

        return {
            "status": "updated",
            "cell": cell_range,
            "summary": request.leadership_summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update sheet: {e}")
