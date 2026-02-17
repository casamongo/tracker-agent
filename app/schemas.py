from pydantic import BaseModel
from typing import List, Optional


class Milestone(BaseModel):
    name: str
    status: Optional[str] = None
    target_date: Optional[str] = None
    owner: Optional[str] = None
    jira_id: str
    previous_status_update: Optional[str] = None


class TrackContext(BaseModel):
    workstream: str
    track: str
    track_status: Optional[str] = None
    notes_link: Optional[str] = None
    notes_text: Optional[str] = None
    milestones: List[Milestone] = []


class JiraUpdate(BaseModel):
    jira_id: str
    milestone: str
    progress_summary: List[str]
    recent_changes: List[str]
    next_steps: List[str]
    leadership_summary: str


class GenerateResponse(BaseModel):
    workstream: str
    track: str
    updates: List[JiraUpdate]


class GenerateRequest(BaseModel):
    sheet_id: str
    track_name: Optional[str] = None  # If None, generate for all tracks


class PostToJiraRequest(BaseModel):
    jira_id: str
    comment: str


class UpdateSheetRequest(BaseModel):
    sheet_id: str
    track_name: str
    leadership_summary: str
