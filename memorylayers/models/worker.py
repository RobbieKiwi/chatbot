"""Headless worker runs: their locks and their health."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from memorylayers.models.vocab import WorkerKind


class WorkerHealth(BaseModel):
    consecutive_failures: int = 0
    stopped_reason: str | None = None  # set once failures reach the limit; launching stops


class LockStatus(StrEnum):
    FREE = "free"
    LIVE = "live"
    ABANDONED = "abandoned"  # its process died or overran its deadline


class RunRecord(BaseModel):
    """A worker run in flight, stored as its kind's lock file."""

    run_id: str
    kind: WorkerKind
    pid: int
    started_at: datetime
    deadline: datetime
    conversation_id: str | None = None
    window_end: dict[str, int] = Field(default_factory=dict)  # session id -> processed line once committed
    pending_at_start: list[int] = Field(default_factory=list)
    through_revision: int | None = None
    calendar_week_start: date | None = None
    expired_periods: list[str] = Field(default_factory=list)
    committed: bool = False
