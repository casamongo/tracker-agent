"""
Tracker Agent Backend

A schema-driven reporting engine that:
1. Reads project tracker spreadsheets (Tracker Schema v1)
2. Fetches linked Notes documents from Google Docs
3. Generates structured Jira updates via LLM
4. Allows human review before posting
5. Posts approved updates to Jira
6. Writes leadership summaries back to the tracker sheet
"""

from fastapi import FastAPI
from app.routes import generate, post

app = FastAPI(
    title="Tracker Agent",
    description="Agentic AI reporting engine for project trackers",
    version="0.1.0",
)

app.include_router(generate.router)
app.include_router(post.router)


@app.get("/health")
def health():
    return {"status": "ok"}
