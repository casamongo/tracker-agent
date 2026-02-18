"""
LLM service.

Generates structured Jira updates and leadership summaries
from track context using Anthropic Claude.
"""

import json

import anthropic

from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_jira_updates(track_context: dict) -> dict:
    """
    Generate structured Jira updates for all milestones in a track.
    """
    milestones_json = json.dumps(track_context.get("milestones", []), indent=2)
    notes_text = track_context.get("notes_text", "No notes available.")

    prompt = f"""You have been given:
1. A list of milestones for a project track
2. The full text of the track's notes document

Your job: For each milestone, generate a structured Jira status update.

MILESTONES:
{milestones_json}

NOTES DOCUMENT:
{notes_text}

RULES:
- Map information from the notes document to the correct milestone.
- If the notes document does not mention a milestone, use the milestone's
  existing status and any previous status update to generate a reasonable update.
- Be factual. Do not invent progress that isn't supported by the notes.
- current_status: A concise summary of where the milestone stands right now (2-3 sentences max).
- target_date: The milestone's target completion date (use the date from the milestone data).
- blockers: A list of blockers or risks. If there are no blockers or risks, return ["None"].
- The leadership_summary should be a single executive-level sentence
  summarizing the milestone status — no task-level detail.

Return ONLY valid JSON in this exact format (no markdown, no explanation):

{{
  "updates": [
    {{
      "jira_id": "the milestone's jira_id",
      "milestone": "the milestone name",
      "current_status": "Concise status of where this milestone stands.",
      "target_date": "The target date",
      "blockers": ["blocker 1", "blocker 2"] or ["None"],
      "leadership_summary": "Single executive sentence."
    }}
  ]
}}
"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system="You are a program management reporting agent.",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    content = response.content[0].text.strip()

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
