from datetime import UTC, date, datetime, timedelta

from memorylayers.domain.due import lock_status, must_settle, record_failure, scribe_due, summariser_due
from memorylayers.domain.permissions import allowed_tools
from memorylayers.models.conversation import PendingNote
from memorylayers.models.views import RefreshStatus
from memorylayers.models.vocab import WorkerKind
from memorylayers.models.worker import LockStatus, RunRecord, WorkerHealth

NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)
WEEK = date(2026, 9, 28)


def test_scribe_due_at_the_threshold() -> None:
    assert not scribe_due(unprocessed_chars=7999, threshold_chars=8000)
    assert scribe_due(unprocessed_chars=8000, threshold_chars=8000)


def test_summariser_due_on_new_facts_or_a_new_week() -> None:
    assert summariser_due(status=RefreshStatus(facts_since_refresh=10, fact_count=50, calendar_week_start=WEEK), refresh_after_facts=10, today_week_start=WEEK)
    assert not summariser_due(status=RefreshStatus(facts_since_refresh=9, fact_count=50, calendar_week_start=WEEK), refresh_after_facts=10, today_week_start=WEEK)
    assert summariser_due(status=RefreshStatus(facts_since_refresh=0, fact_count=50, calendar_week_start=date(2026, 9, 21)), refresh_after_facts=10, today_week_start=WEEK)
    assert not summariser_due(status=RefreshStatus(facts_since_refresh=0, fact_count=0, calendar_week_start=None), refresh_after_facts=10, today_week_start=WEEK)


def test_pending_notes_settle_after_enough_runs_or_idleness() -> None:
    assert not must_settle(note=PendingNote(number=1, text="x", runs_survived=1), settle_runs=2, idle=False)
    assert must_settle(note=PendingNote(number=1, text="x", runs_survived=2), settle_runs=2, idle=False)
    assert must_settle(note=PendingNote(number=1, text="x"), settle_runs=2, idle=True)


def test_lock_status() -> None:
    record = RunRecord(run_id="r", kind=WorkerKind.SCRIBE, pid=5, started_at=NOW, deadline=NOW + timedelta(minutes=30))
    assert lock_status(record=None, alive=False, now=NOW) is LockStatus.FREE
    assert lock_status(record=record, alive=True, now=NOW) is LockStatus.LIVE
    assert lock_status(record=record, alive=False, now=NOW) is LockStatus.ABANDONED
    assert lock_status(record=record, alive=True, now=NOW + timedelta(hours=1)) is LockStatus.ABANDONED


def test_failures_stop_at_the_limit() -> None:
    health = WorkerHealth()
    for _ in range(3):
        record_failure(health=health, limit=3, reason="no commit")
    assert health.consecutive_failures == 3
    assert health.stopped_reason is not None and "no commit" in health.stopped_reason


def test_each_worker_gets_reads_plus_its_own_writes() -> None:
    scribe = allowed_tools(kind=WorkerKind.SCRIBE)
    assert "Bash(.venv/Scripts/python -m memorylayers store:*)" in scribe
    assert "Bash(.venv/Scripts/python -m freshtopics log:*)" in scribe
    assert "Bash(.venv/Scripts/python -m memorylayers recall:*)" in scribe
    assert not any("tag-summary" in tool for tool in scribe)
    assert allowed_tools(kind=WorkerKind.MIGRATOR) == []
