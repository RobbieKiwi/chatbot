"""The visible text of a Claude Code conversation."""

from enum import StrEnum

from pydantic import BaseModel


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class TextTurn(BaseModel):
    """One visible message: user text or assistant text, never reasoning, tool traffic or hook output."""

    role: Role
    text: str
