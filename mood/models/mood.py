"""The assistant's mood within one Claude session: five feelings and how openly they show. Every scale runs 0–10; the persona's PERSONA.md describes their levels."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Axis(StrEnum):
    """The scales the observer nudges. Feelings read 0 as the feeling's absence."""

    CHEERFULNESS = "cheerfulness"
    PLAYFULNESS = "playfulness"
    IRRITATION = "irritation"
    MELANCHOLY = "melancholy"
    RESTLESSNESS = "restlessness"


Scale = Annotated[float, Field(ge=0, le=10)]
Nudge = Annotated[float, Field(ge=-3, le=3)]


class MoodUpdate(BaseModel):
    at: datetime
    deltas: dict[Axis, float]  # as applied, after the clamp
    presence_delta: float  # as applied, drift included
    reason: str  # the observer's


class MoodState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cheerfulness: Scale
    playfulness: Scale
    irritation: Scale
    melancholy: Scale
    restlessness: Scale
    presence: Scale  # how openly the mood shows
    presence_base: Scale  # the rolled presence, which presence drifts back towards
    rolled_at: datetime
    updated_at: datetime
    history: list[MoodUpdate] = Field(default_factory=list)
    thoughts: list[str] = Field(default_factory=list)  # the assistant's private inner monologue in its own voice: what is on its mind, what it wants next, what it is holding back

    def value(self, *, axis: Axis) -> float:
        return getattr(self, axis.value)


class ObserverReply(BaseModel):
    """What the observer judged from the last turns. Extra keys are ignored; out-of-range numbers are invalid."""

    deltas: dict[Axis, Nudge] = Field(default_factory=dict)
    presence_delta: Nudge = 0.0
    probing: bool = False  # the user is asking about the assistant's feelings or what is on its mind
    reason: str = ""
    thoughts: list[str] | None = None  # the rewritten private thoughts; None keeps the current ones
