"""A conversation with a parent skill, spanning one or more Claude sessions."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from memorylayers.models.worker import WorkerHealth


class SessionLink(BaseModel):
    session_id: str
    transcript_path: Path
    processed_line: int = 0  # index of the first transcript line no scribe has filed


class PendingNote(BaseModel):
    """A fact still forming, parked until it settles."""

    number: int
    text: str
    runs_survived: int = 0


class ConversationState(BaseModel):
    id: str
    started_at: datetime
    last_activity: datetime
    sessions: list[SessionLink] = Field(default_factory=list)
    rolling_summary: str = ""
    ledger: list[int] = Field(default_factory=list)  # ids of facts written in this conversation
    pending_notes: list[PendingNote] = Field(default_factory=list)
    hints_shown: list[str] = Field(default_factory=list)
    messages_seen: int = 0  # messages the hook has seen in this conversation
    scribe_health: WorkerHealth = Field(default_factory=WorkerHealth)


class PendingRegistration(BaseModel):
    """A session that typed the parent's slash command and awaits `resume`."""

    session_id: str
    transcript_path: Path
    seen_at: datetime


class SessionRegistry(BaseModel):
    pending: PendingRegistration | None = None
    sessions: dict[str, str] = Field(default_factory=dict)  # session id -> conversation id
