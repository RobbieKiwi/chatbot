"""Where mood keeps its state and logs."""

import os
from pathlib import Path

from mood.models.paths import MoodPaths

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent


def data_root() -> Path:
    return Path(os.environ.get("MOOD_DATA_ROOT", PACKAGE_ROOT / "data"))


def mood_paths(*, parent: str) -> MoodPaths:
    root = data_root() / parent
    return MoodPaths(parent=parent, root=root, config=root / "config.json", sessions=root / "sessions", logs=root / "logs")
