"""
Generate preview endpoint.

Reads sheet data, fetches notes documents, and generates
AI-powered Jira update drafts for human review.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import GenerateRequest
from app.services import sheets, docs, parser, llm

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])


@router.post("/generate-preview")
def generate_preview(request: GenerateRequest):
    """
    Generate AI-powered Jira update previews for tracks in a tracker sheet.
    """
    # Step 1: Read sheet
    try:
        rows = sheets.read_sheet(request.sheet_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read sheet: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="Sheet is empty or has no data rows.")

    # Step 2: Validate schema
    headers = list(rows[0].keys())
    missing = parser.validate_schema(headers)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Sheet is missing required columns: {', '.join(missing)}",
        )

    # Step 3: Parse into hierarchy
    parsed_tracks = parser.parse_sheet_rows(rows)
    logger.info(
        "Parsed %d track(s) with milestones: %s",
        len(parsed_tracks),
        [(t["track"], len(t["milestones"])) for t in parsed_tracks],
    )

    if not parsed_tracks:
        raise HTTPException(status_code=400, detail="No tracks found in sheet.")

    # Step 4: Filter to specific track if requested
    if request.track_name:
        parsed_tracks = [
            t for t in parsed_tracks
            if t["track"].lower() == request.track_name.lower()
        ]
        if not parsed_tracks:
            raise HTTPException(
                status_code=404,
                detail=f"Track '{request.track_name}' not found in sheet.",
            )

    # Step 5: Generate updates for each track
    results = []

    for track in parsed_tracks:
        # Fetch notes document if link exists
        notes_text = ""
        if track.get("notes_link"):
            try:
                notes_text = docs.get_doc_text(track["notes_link"])
            except Exception as e:
                notes_text = f"[Error fetching notes: {e}]"

        track["notes_text"] = notes_text

        # Skip tracks with no milestones
        if not track.get("milestones"):
            continue

        # Generate AI updates
        try:
            ai_result = llm.generate_jira_updates(track)
            logger.info("Generated %d update(s) for track '%s'", len(ai_result.get("updates", [])), track["track"])
            results.append(ai_result)
        except Exception as e:
            logger.error("LLM generation failed for track '%s': %s", track["track"], e)
            results.append({
                "workstream": track.get("workstream", ""),
                "track": track.get("track", ""),
                "error": str(e),
                "updates": [],
            })

    return {"results": results}
