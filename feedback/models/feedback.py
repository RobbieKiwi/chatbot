"""Feedback on the assistant's behaviour, and the prompt changes made in answer to it. An item's status is derived from the changes, never stored."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Verdict(StrEnum):
    """What a change did for an item."""

    PARTLY = "partly"
    RESOLVED = "resolved"


class Status(StrEnum):
    OPEN = "open"  # no verdict yet, or a note after the latest verdict
    PARTLY = "partly"
    RESOLVED = "resolved"


class Note(BaseModel):
    """A later `fb: #id` addition to an item."""

    model_config = ConfigDict(extra="forbid")

    at: datetime
    text: str
    context: str  # the turns before it, as plain text


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime
    text: str
    context: str  # the turns before it, as plain text
    notes: list[Note] = Field(default_factory=list)


class Change(BaseModel):
    """One coherent edit to the prompts, and the items it addressed."""

    model_config = ConfigDict(extra="forbid")

    id: int
    made_at: datetime
    summary: str
    files: list[str]
    addresses: dict[int, Verdict]  # item id -> verdict


class FeedbackFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[Item] = Field(default_factory=list)
    changes: list[Change] = Field(default_factory=list)
