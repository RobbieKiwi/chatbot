"""Atomic JSON writes and a cross-process lock, for a file the hook and the CLI both edit."""

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel


def write_model(*, path: Path, value: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    temporary.write_text(value.model_dump_json(indent=2), encoding="utf-8")
    for _ in range(50):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:  # Windows: another process has the file open for a moment
            time.sleep(0.01)
    os.replace(temporary, path)


@contextmanager
def file_lock(*, path: Path, timeout_s: float = 5.0) -> Iterator[None]:
    """A sidecar file created exclusively. A holder that died is broken after the timeout."""
    lock = path.with_name(f"{path.name}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except (FileExistsError, PermissionError):  # Windows reports a lock file mid-delete as PermissionError
            if time.monotonic() > deadline:
                lock.unlink(missing_ok=True)
                deadline = time.monotonic() + timeout_s
            time.sleep(0.002)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)
