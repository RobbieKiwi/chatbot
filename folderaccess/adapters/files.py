"""Atomic text writes, so a reader never sees a half-written file."""

import os
import time
from pathlib import Path


def write_text_atomically(*, path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    for _ in range(50):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:  # Windows: another process has the file open for a moment
            time.sleep(0.01)
    os.replace(temporary, path)
