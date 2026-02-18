"""
Multi-agent orchestrator using Claude tool use.

Three sub-agents coordinated by an orchestrator:
  1. extract_facts   – pulls raw facts from notes, mapped to milestones
  2. summarize_facts – rewrites facts using summarization guidelines
  3. format_updates  – produces final structured JSON for Jira
"""

import json
from pathlib import Path

import anthropic

from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

GUIDELINES_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "summarization_guidelines.txt"

# ── Tool definitions exposed to the orchestrator ────────────────────────

TOOLS = [
    {
        "name": "extract_facts",
        "description": (
            "Extract raw factual observations from the notes document and map "
            "them to the relevant milestones. Call this first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "milestones_json": {
                    "type": "string",
                    "description": "JSON string of milestones to extract facts for.",
                },
                "notes_text": {
                    "type": "string",
                    "description": "Full text of the notes document.",
                },
            },
            "required": ["milestones_json", "notes_text"],
        },
    },
    {
        "name": "summarize_facts",
        "description": (
            "Take extracted facts and rewrite them into polished summaries "
            "following the project's summarization guidelines. Call this after extract_facts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "extracted_facts_json": {
                    "type": "string",
                    "description": "JSON string of extracted facts from extract_facts.",
                },
            },
            "required": ["extracted_facts_json"],
        },
    },
    {
        "name": "format_updates",
        "description": (
            "Take summarized content and format it into the final structured JSON "
            "for Jira posting. Call this after summarize_facts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summarized_json": {
                    "type": "string",
                    "description": "JSON string of summarized updates from summarize_facts.",
                },
            },
            "required": ["summarized_json"],
        },
    },
]


# ── Sub-agent implementations ───────────────────────────────────────────

def _run_extract_facts(milestones_json: str, notes_text: str) -> str:
    """Sub-agent 1: fact extraction."""
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0.1,
        system=(
            "You are a fact-extraction agent. Your only job is to read the notes "
            "document and pull out every concrete, factual observation that relates "
            "to the given milestones. Do not summarize or paraphrase — just extract "
            "raw facts. Return valid JSON."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"MILESTONES:\n{milestones_json}\n\n"
                    f"NOTES DOCUMENT:\n{notes_text}\n\n"
                    "For each milestone, extract raw facts from the notes. "
                    "If the notes do not mention a milestone, note that explicitly.\n\n"
                    "Return JSON:\n"
                    '{"facts": [{"jira_id": "...", "milestone": "...", "raw_facts": ["fact1", "fact2"]}, ...]}'
                ),
            }
        ],
    )
    return response.content[0].text


def _load_guidelines() -> str:
    """Load summarization guidelines from the prompts directory."""
    if GUIDELINES_PATH.exists():
        return GUIDELINES_PATH.read_text()
    return "No custom guidelines found. Use professional, concise language."


def _run_summarize_facts(extracted_facts_json: str) -> str:
    """Sub-agent 2: summarization with guidelines."""
    guidelines = _load_guidelines()

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0.2,
        system=(
            "You are a summarization agent. Rewrite raw extracted facts into "
            "polished, executive-ready summaries. Follow the guidelines strictly.\n\n"
            f"SUMMARIZATION GUIDELINES:\n{guidelines}"
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"EXTRACTED FACTS:\n{extracted_facts_json}\n\n"
                    "For each milestone, produce:\n"
                    "- progress_summary: 2-4 bullet points\n"
                    "- recent_changes: 2-4 bullet points\n"
                    "- next_steps: 2-4 bullet points\n"
                    "- leadership_summary: one executive sentence\n\n"
                    "Return valid JSON:\n"
                    '{"summaries": [{"jira_id": "...", "milestone": "...", '
                    '"progress_summary": [...], "recent_changes": [...], '
                    '"next_steps": [...], "leadership_summary": "..."}, ...]}'
                ),
            }
        ],
    )
    return response.content[0].text


def _run_format_updates(summarized_json: str) -> str:
    """Sub-agent 3: final formatting."""
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0.0,
        system=(
            "You are a formatting agent. Take the summarized updates and return "
            "them in the exact JSON schema required. Do not change the content — "
            "only ensure the structure is correct. Return ONLY valid JSON, no markdown."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"SUMMARIZED UPDATES:\n{summarized_json}\n\n"
                    "Return ONLY valid JSON in this exact format:\n"
                    '{"updates": [{"jira_id": "...", "milestone": "...", '
                    '"progress_summary": ["..."], "recent_changes": ["..."], '
                    '"next_steps": ["..."], "leadership_summary": "..."}]}'
                ),
            }
        ],
    )
    return response.content[0].text


# Dispatch table
_TOOL_HANDLERS = {
    "extract_facts": lambda inputs: _run_extract_facts(
        inputs["milestones_json"], inputs["notes_text"]
    ),
    "summarize_facts": lambda inputs: _run_summarize_facts(
        inputs["extracted_facts_json"]
    ),
    "format_updates": lambda inputs: _run_format_updates(
        inputs["summarized_json"]
    ),
}


# ── Orchestrator loop ───────────────────────────────────────────────────

def run_orchestrator(milestones_json: str, notes_text: str) -> dict:
    """
    Run the orchestrator agent which coordinates sub-agents via tool use.
    Returns the final structured updates dict.
    """
    messages = [
        {
            "role": "user",
            "content": (
                "Generate Jira updates for the following milestones using the notes document.\n\n"
                f"MILESTONES:\n{milestones_json}\n\n"
                f"NOTES DOCUMENT:\n{notes_text}\n\n"
                "Steps:\n"
                "1. Call extract_facts to pull raw facts from the notes\n"
                "2. Call summarize_facts to produce polished summaries\n"
                "3. Call format_updates to produce the final JSON\n"
                "4. Return the final JSON result as your response"
            ),
        }
    ]

    # Agentic loop — keep going until the orchestrator produces a final text response
    max_iterations = 10
    for _ in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            temperature=0.0,
            system=(
                "You are an orchestrator agent. You coordinate three specialist tools "
                "to generate Jira milestone updates. Call them in order: "
                "extract_facts → summarize_facts → format_updates. "
                "After format_updates returns, output the final JSON as your response."
            ),
            tools=TOOLS,
            messages=messages,
        )

        # If the model is done (no more tool calls), break
        if response.stop_reason == "end_turn":
            break

        # Process tool calls
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in assistant_content:
            if block.type == "tool_use":
                handler = _TOOL_HANDLERS.get(block.name)
                if handler:
                    result = handler(block.input)
                else:
                    result = json.dumps({"error": f"Unknown tool: {block.name}"})

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

        messages.append({"role": "user", "content": tool_results})
    else:
        raise RuntimeError("Orchestrator did not converge within max iterations")

    # Extract final text from the response
    final_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_text += block.text

    return final_text.strip()
