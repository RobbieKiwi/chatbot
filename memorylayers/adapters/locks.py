"""One lock file per worker kind, holding the run record of the run in flight."""

import os
from pathlib import Path

from pydantic import ValidationError

from memorylayers.adapters.state_files import read_model, write_model
from memorylayers.models.paths import ParentPaths
from memorylayers.models.vocab import WorkerKind
from memorylayers.models.worker import RunRecord


def _lock_path(*, paths: ParentPaths, kind: WorkerKind) -> Path:
    return paths.locks / f"{kind.value}.json"


def read_lock(*, paths: ParentPaths, kind: WorkerKind) -> RunRecord | None:
    """The run record, or None when there is no lock or it is being written this instant."""
    try:
        return read_model(path=_lock_path(paths=paths, kind=kind), model=RunRecord)
    except (ValidationError, OSError):
        return None


def try_create_lock(*, paths: ParentPaths, record: RunRecord) -> bool:
    path = _lock_path(paths=paths, kind=record.kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except (FileExistsError, PermissionError):  # Windows raises PermissionError while a lock file is being deleted
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as lock:
        lock.write(record.model_dump_json(indent=2))
    return True


def write_lock(*, paths: ParentPaths, record: RunRecord) -> None:
    write_model(path=_lock_path(paths=paths, kind=record.kind), value=record)


def remove_lock(*, paths: ParentPaths, kind: WorkerKind) -> None:
    _lock_path(paths=paths, kind=kind).unlink(missing_ok=True)
