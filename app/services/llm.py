"""
LLM service.

Generates structured Jira updates and leadership summaries
from track context using a multi-agent orchestrator.
"""

import json

from app.services.agents import run_orchestrator


def generate_jira_updates(track_context: dict) -> dict:
    """
    Generate structured Jira updates for all milestones in a track.
    Delegates to the orchestrator which coordinates three sub-agents:
      1. extract_facts   – raw fact extraction from notes
      2. summarize_facts – polished summaries per guidelines
      3. format_updates  – final structured JSON
    """
    milestones_json = json.dumps(track_context.get("milestones", []), indent=2)
    notes_text = track_context.get("notes_text", "No notes available.")

    content = run_orchestrator(milestones_json, notes_text)

    # Handle potential markdown code fences in response
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    result = json.loads(content)

    # Attach workstream and track metadata
    result["workstream"] = track_context.get("workstream", "")
    result["track"] = track_context.get("track", "")

    return result
