"""Where one parent skill's mood state lives on disk."""

from pathlib import Path

from pydantic import BaseModel


class MoodPaths(BaseModel):
    parent: str
    root: Path
    config: Path
    sessions: Path  # one state file per Claude session
    locks: Path  # one observer lock per session
    logs: Path
