"""
Sheet reading endpoint.

Returns raw tracker sheet rows for the frontend dashboard table.
"""

from fastapi import APIRouter, HTTPException

from app.services import sheets, parser

router = APIRouter(tags=["sheet"])


@router.get("/read-sheet/{sheet_id}")
def read_sheet(sheet_id: str):
    """
    Read a tracker sheet and return validated, structured data
    for the dashboard table.
    """
    try:
        rows = sheets.read_sheet(sheet_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read sheet: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="Sheet is empty or has no data rows.")

    headers = list(rows[0].keys())
    missing = parser.validate_schema(headers)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Sheet is missing required columns: {', '.join(missing)}",
        )

    return {"rows": rows}
