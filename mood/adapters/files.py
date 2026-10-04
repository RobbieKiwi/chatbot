"""Atomic JSON files for models."""

import os
import time
from pathlib import Path

from pydantic import BaseModel


def read_model[M: BaseModel](*, path: Path, model: type[M]) -> M | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return model.model_validate_json(text)


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
