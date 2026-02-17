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

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes import generate, post, sheet

app = FastAPI(
    title="Tracker Agent",
    description="Agentic AI reporting engine for project trackers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)
app.include_router(post.router)
app.include_router(sheet.router)

# Serve static frontend assets
_static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(str(_static_dir / "index.html"))
