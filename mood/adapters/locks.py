"""One observer lock per session, so a slow observer is never joined by a second."""

import os
from datetime import datetime, timedelta
from pathlib import Path

from mood.models.paths import MoodPaths


def observer_lock_path(*, paths: MoodPaths, session_id: str) -> Path:
    return paths.locks / f"{session_id}.lock"


def _taken_at(*, path: Path) -> datetime | None:
    try:
        return datetime.fromisoformat(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def try_lock(*, path: Path, now: datetime, stale_after: timedelta) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):  # Windows raises PermissionError while a lock file is being deleted
            taken = _taken_at(path=path)
            if taken is not None and now - taken < stale_after:
                return False
            path.unlink(missing_ok=True)  # stale, or unreadable mid-write: break it once
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as lock:
            lock.write(now.isoformat())
        return True
    return False


def release_lock(*, path: Path) -> None:
    path.unlink(missing_ok=True)
