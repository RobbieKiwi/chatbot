"""Spans of time: when a fact occurred, and the periods that summarise facts."""

from datetime import date

from pydantic import BaseModel

from memorylayers.models.vocab import PeriodKind, Precision

ONGOING_END = date(9999, 12, 31)  # end of an era that has not ended


class OccurredRange(BaseModel):
    """When a fact happened. Both ends inclusive; both None for unknown and timeless facts."""

    start: date | None
    end: date | None
    precision: Precision


class Bucket(BaseModel):
    """A summarised span of time: a calendar bucket or an era."""

    name: str  # "2026-W40", "2026-10", "2026 Q3", "2026", or an era's name
    kind: PeriodKind
    start: date
    end: date  # inclusive
