"""Plumbing shared by mood's hooks and command line."""

import traceback
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from mood.models.paths import MoodPaths


class HookPayload(BaseModel):
    session_id: str
    transcript_path: Path
    prompt: str = ""


def is_registration_prompt(*, prompt: str, parent: str) -> bool:
    stripped = prompt.strip()
    return stripped == f"/{parent}" or stripped.startswith(f"/{parent} ") or f"<command-name>/{parent}</command-name>" in stripped


def log(*, paths: MoodPaths, name: str, message: str) -> None:
    try:
        paths.logs.mkdir(parents=True, exist_ok=True)
        with (paths.logs / f"{name}.log").open("a", encoding="utf-8") as file:
            file.write(f"{datetime.now(UTC).isoformat()} {message}\n")
    except OSError:
        pass


def log_exception(*, paths: MoodPaths, name: str) -> None:
    log(paths=paths, name=name, message=traceback.format_exc())
