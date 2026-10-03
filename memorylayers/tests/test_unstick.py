from datetime import UTC, datetime, timedelta

from memorylayers.adapters.locks import read_lock, try_create_lock
from memorylayers.adapters.state_files import load_conversation, load_summariser_health, save_conversation, update_summariser_health
from memorylayers.models.conversation import ConversationState
from memorylayers.models.paths import ParentPaths
from memorylayers.models.vocab import WorkerKind
from memorylayers.models.worker import RunRecord, WorkerHealth
from memorylayers.scripts.unstick import unstick

NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)


def test_unstick_clears_stops_and_dead_locks(paths: ParentPaths) -> None:
    save_conversation(paths=paths, state=ConversationState(id="c1", started_at=NOW, last_activity=NOW, scribe_health=WorkerHealth(consecutive_failures=3, stopped_reason="x")))
    update_summariser_health(paths=paths, change=lambda health: setattr(health, "stopped_reason", "y"))
    try_create_lock(paths=paths, record=RunRecord(run_id="r", kind=WorkerKind.SCRIBE, pid=-1, started_at=NOW, deadline=NOW + timedelta(minutes=5)))
    unstick(parent="pk")
    assert load_conversation(paths=paths, conversation_id="c1").scribe_health == WorkerHealth()
    assert load_summariser_health(paths=paths) == WorkerHealth()
    assert read_lock(paths=paths, kind=WorkerKind.SCRIBE) is None
