import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from memorylayers.adapters.locks import read_lock, remove_lock, try_create_lock
from memorylayers.adapters.processes import pid_alive, spawn_detached
from memorylayers.models.paths import ParentPaths
from memorylayers.models.vocab import WorkerKind
from memorylayers.models.worker import RunRecord

NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)


def test_checking_a_live_pid_does_not_kill_it() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert pid_alive(pid=child.pid)
        assert pid_alive(pid=child.pid)
        assert child.poll() is None
    finally:
        child.kill()
        child.wait()
    assert not pid_alive(pid=child.pid)


def test_spawned_processes_run_detached(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    spawn_detached(args=[sys.executable, "-c", f"open({str(marker)!r}, 'w').write('ok')"], cwd=tmp_path, log_path=tmp_path / "spawn.log")
    deadline = time.monotonic() + 10
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert marker.read_text() == "ok"


def test_locks_are_exclusive(paths: ParentPaths) -> None:
    record = RunRecord(run_id="r1", kind=WorkerKind.SCRIBE, pid=1, started_at=NOW, deadline=NOW + timedelta(minutes=5))
    assert try_create_lock(paths=paths, record=record)
    assert not try_create_lock(paths=paths, record=record.model_copy(update={"run_id": "r2"}))
    held = read_lock(paths=paths, kind=WorkerKind.SCRIBE)
    assert held is not None and held.run_id == "r1"
    remove_lock(paths=paths, kind=WorkerKind.SCRIBE)
    assert read_lock(paths=paths, kind=WorkerKind.SCRIBE) is None
