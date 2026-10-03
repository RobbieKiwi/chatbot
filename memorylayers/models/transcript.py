"""The visible conversation, read from Claude Code transcripts."""

from datetime import datetime

from pydantic import BaseModel

from memorylayers.models.vocab import Role


class Turn(BaseModel):
    """One visible message: user text or assistant text, never reasoning or tool traffic."""

    role: Role
    text: str
    at: datetime  # local time
    session_id: str
    line: int  # transcript line index


class ScribeWindow(BaseModel):
    context: list[Turn]  # already filed; shown again for continuity
    new: list[Turn]
    end: dict[str, int]  # session id -> processed line once this window is committed


class ConversationTurns(BaseModel):
    processed: list[Turn]
    unprocessed: list[Turn]
    ends: dict[str, int]  # session id -> complete lines in its transcript
