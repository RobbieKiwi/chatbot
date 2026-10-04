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

    def value(self, *, axis: Axis) -> float:
        return getattr(self, axis.value)
