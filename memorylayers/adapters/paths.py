"""Where memorylayers keeps its data, prompts and the project it serves."""

import os
from pathlib import Path

from memorylayers.models.paths import ParentPaths

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent


def data_root() -> Path:
    return Path(os.environ.get("MEMORYLAYERS_DATA_ROOT", PACKAGE_ROOT / "data"))


def parent_paths(*, parent: str) -> ParentPaths:
    root = data_root() / parent
    return ParentPaths(
        parent=parent,
        root=root,
        db=root / "memory.db",
        summary=root / "summary.md",
        config=root / "config.json",
    )
