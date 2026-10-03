"""When workers are due, and what a failed run does to a worker's health."""

from datetime import date, datetime

from memorylayers.models.conversation import PendingNote
from memorylayers.models.views import RefreshStatus
from memorylayers.models.worker import LockStatus, RunRecord, WorkerHealth


def scribe_due(*, unprocessed_chars: int, threshold_chars: int) -> bool:
    return unprocessed_chars >= threshold_chars


def summariser_due(*, status: RefreshStatus, refresh_after_facts: int, today_week_start: date) -> bool:
    if status.fact_count == 0:
        return False
    return status.facts_since_refresh >= refresh_after_facts or status.calendar_week_start != today_week_start


def must_settle(*, note: PendingNote, settle_runs: int, idle: bool) -> bool:
    return idle or note.runs_survived >= settle_runs


def lock_status(*, record: RunRecord | None, alive: bool, now: datetime) -> LockStatus:
    if record is None:
        return LockStatus.FREE
    return LockStatus.LIVE if alive and now < record.deadline else LockStatus.ABANDONED


def record_failure(*, health: WorkerHealth, limit: int, reason: str) -> None:
    health.consecutive_failures += 1
    if health.consecutive_failures >= limit:
        health.stopped_reason = f"{reason} ({health.consecutive_failures} failures in a row)"
