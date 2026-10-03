"""Launching the runner: shared by the hook and resume, and free of SQLModel."""

from datetime import datetime

from memorylayers.adapters.locks import read_lock
from memorylayers.adapters.paths import PROJECT_ROOT
from memorylayers.adapters.processes import pid_alive, spawn_detached
from memorylayers.domain.due import lock_status
from memorylayers.models.paths import ParentPaths
from memorylayers.models.vocab import WorkerKind
from memorylayers.models.worker import LockStatus


def spawn_runner(*, paths: ParentPaths, command: list[str]) -> None:
    spawn_detached(args=command, cwd=PROJECT_ROOT, log_path=paths.logs / "runner.log")


def kind_is_free(*, paths: ParentPaths, kind: WorkerKind, now: datetime) -> bool:
    record = read_lock(paths=paths, kind=kind)
    alive = record is not None and pid_alive(pid=record.pid)
    return lock_status(record=record, alive=alive, now=now) is not LockStatus.LIVE
