"""The conversation the page shows."""

from datetime import datetime

from pydantic import BaseModel


class WebchatState(BaseModel):
    """The current conversation: one Claude Code session that was opened with /chatbot."""

    session_id: str
    started_at: datetime
