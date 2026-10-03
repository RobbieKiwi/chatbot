import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from memorylayers.adapters.locks import try_create_lock
from memorylayers.models.paths import ParentPaths
from memorylayers.models.vocab import WorkerKind
from memorylayers.models.worker import RunRecord

Run = Callable[[list[str]], tuple[int, str, str]]


def test_status_reports_an_abandoned_lock(paths: ParentPaths, run_cli: Run) -> None:
    finished = subprocess.run([sys.executable, "-c", "pass"], check=True)
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    now = datetime.now(UTC)
    try_create_lock(paths=paths, record=RunRecord(run_id="scribe-1", kind=WorkerKind.SCRIBE, pid=dead.pid, started_at=now, deadline=now + timedelta(minutes=30)))
    code, out, _ = run_cli(["status"])
    assert code == 0 and finished.returncode == 0
    assert "scribe: abandoned" in out
    assert "summariser: idle" in out
    assert "summariser health: ok" in out
