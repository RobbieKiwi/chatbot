"""Where feedback keeps its data and logs."""

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def data_root() -> Path:
    return Path(os.environ.get("FEEDBACK_DATA_ROOT", PACKAGE_ROOT / "data"))


def feedback_path(*, parent: str) -> Path:
    return data_root() / f"{parent}.json"


def logs_dir() -> Path:
    return data_root() / "logs"
