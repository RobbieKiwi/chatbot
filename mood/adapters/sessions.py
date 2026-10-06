"""One mood state file per Claude session, and the parent's mood config."""

import re
from pathlib import Path

from mood.adapters.files import read_model, write_model
from mood.models.config import MoodConfig
from mood.models.mood import MoodState
from mood.models.paths import MoodPaths

_SESSION_ID = re.compile(r"[A-Za-z0-9_-]+")


def _session_path(*, paths: MoodPaths, session_id: str) -> Path:
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError(f"unexpected session id {session_id!r}")
    return paths.sessions / f"{session_id}.json"


def load_mood(*, paths: MoodPaths, session_id: str) -> MoodState | None:
    return read_model(path=_session_path(paths=paths, session_id=session_id), model=MoodState)


def save_mood(*, paths: MoodPaths, session_id: str, state: MoodState) -> None:
    write_model(path=_session_path(paths=paths, session_id=session_id), value=state)


def latest_session_id(*, paths: MoodPaths) -> str | None:
    files = sorted(paths.sessions.glob("*.json"), key=lambda path: path.stat().st_mtime) if paths.sessions.is_dir() else []
    return files[-1].stem if files else None


def load_config(*, paths: MoodPaths) -> MoodConfig:
    return read_model(path=paths.config, model=MoodConfig) or MoodConfig()
