"""Clear worker stops and abandoned locks after fixing whatever made runs fail. Run: uv run python -m memorylayers.scripts.unstick"""

from datetime import UTC, datetime

from memorylayers.adapters.locks import read_lock, remove_lock
from memorylayers.adapters.paths import parent_paths
from memorylayers.adapters.processes import pid_alive
from memorylayers.adapters.state_files import list_conversations, update_conversation, update_summariser_health
from memorylayers.domain.due import lock_status
from memorylayers.models.vocab import WorkerKind
from memorylayers.models.worker import LockStatus, WorkerHealth


def unstick(*, parent: str) -> None:
    paths = parent_paths(parent=parent)
    for state in list_conversations(paths=paths):
        if state.scribe_health != WorkerHealth():
            update_conversation(paths=paths, conversation_id=state.id, change=lambda conversation: setattr(conversation, "scribe_health", WorkerHealth()))
            print(f"cleared the scribe for conversation {state.id}")

    def clear(health: WorkerHealth) -> None:
        health.consecutive_failures, health.stopped_reason = 0, None

    update_summariser_health(paths=paths, change=clear)
    now = datetime.now(UTC)
    for kind in (WorkerKind.SCRIBE, WorkerKind.SUMMARISER, WorkerKind.CONSOLIDATOR):
        record = read_lock(paths=paths, kind=kind)
        if record is not None and lock_status(record=record, alive=pid_alive(pid=record.pid), now=now) is not LockStatus.LIVE:
            remove_lock(paths=paths, kind=kind)
            print(f"removed the abandoned {kind} lock ({record.run_id})")
    print("Workers will launch again on the next message.")


if __name__ == "__main__":
    unstick(parent="chatbot")
