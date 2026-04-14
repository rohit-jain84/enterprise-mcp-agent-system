"""Shared Pydantic models for the enterprise MCP agent system."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Team ---


class TeamMember(BaseModel):
    username: str
    full_name: str
    email: str
    role: str
    team: str
    capacity_points: int = Field(description="Story points capacity per sprint")
    current_load: int = Field(description="Currently assigned story points")


# --- GitHub ---


class PRReview(BaseModel):
    reviewer: str
    state: str  # approved, changes_requested, pending
    submitted_at: str | None = None
    body: str | None = None


class CICheck(BaseModel):
    name: str
    status: str  # passed, failed, running, pending
    duration_seconds: int | None = None
    url: str | None = None


class PullRequest(BaseModel):
    id: int
    number: int
    repo: str
    title: str
    description: str
    state: str  # open, merged, closed, draft
    author: str
    branch: str
    base_branch: str = "main"
    created_at: str
    updated_at: str
    merged_at: str | None = None
    reviewers: list[PRReview] = []
    ci_status: str = "pending"  # passed, failed, running, pending
    labels: list[str] = []
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    linked_issues: list[str] = []
    diff_summary: str | None = None


class IssueComment(BaseModel):
    author: str
    body: str
    created_at: str


class Issue(BaseModel):
    id: int
    number: int
    repo: str
    title: str
    body: str
    state: str  # open, closed
    author: str
    assignees: list[str] = []
    labels: list[str] = []
    created_at: str
    updated_at: str
    closed_at: str | None = None
    comments: list[IssueComment] = []
    linked_prs: list[int] = []
    milestone: str | None = None


class Commit(BaseModel):
    sha: str
    repo: str
    branch: str
    message: str
    author: str
    timestamp: str
    additions: int = 0
    deletions: int = 0
    files_changed: list[str] = []


class CIStatus(BaseModel):
    ref: str
    repo: str
    status: str  # passed, failed, running, pending
    checks: list[CICheck] = []
    started_at: str | None = None
    completed_at: str | None = None
    commit_sha: str | None = None


# --- Project Management ---


class TicketComment(BaseModel):
    author: str
    body: str
    created_at: str


class Ticket(BaseModel):
    id: str  # e.g., PAY-189
    project: str
    title: str
    description: str
    type: str  # bug, feature, improvement, task
    status: str  # todo, in_progress, in_review, done, blocked
    priority: str  # P0, P1, P2, P3
    assignee: str | None = None
    reporter: str
    story_points: int | None = None
    sprint: str | None = None
    labels: list[str] = []
    created_at: str
    updated_at: str
    linked_prs: list[dict[str, Any]] = []
    comments: list[TicketComment] = []
    blocked_by: list[str] = []
    blocks: list[str] = []


class Sprint(BaseModel):
    id: str
    name: str
    project: str
    state: str  # active, completed, planned
    start_date: str
    end_date: str
    goal: str
    tickets: list[str] = []  # ticket IDs
    committed_points: int = 0
    completed_points: int = 0


class VelocityEntry(BaseModel):
    sprint_id: str
    sprint_name: str
    committed_points: int
    completed_points: int
    carry_over_points: int = 0


# --- Calendar ---


class Attendee(BaseModel):
    username: str
    full_name: str
    response_status: str = "accepted"  # accepted, declined, tentative


class ActionItem(BaseModel):
    assignee: str
    description: str
    due_date: str | None = None
    status: str = "open"  # open, done


class MeetingNotes(BaseModel):
    meeting_id: str
    recorded_by: str
    discussion_points: list[str] = []
    decisions: list[str] = []
    action_items: list[ActionItem] = []


class Meeting(BaseModel):
    id: str
    title: str
    meeting_type: str  # standup, sprint_planning, retro, one_on_one, design_review
    date: str
    start_time: str
    end_time: str
    organizer: str
    attendees: list[Attendee] = []
    location: str = "Google Meet"
    description: str = ""
    recurring: bool = False
    notes: MeetingNotes | None = None


class TimeSlot(BaseModel):
    start_time: str
    end_time: str
    status: str = "busy"  # busy, free
    meeting_id: str | None = None


class DayAvailability(BaseModel):
    date: str
    slots: list[TimeSlot] = []
