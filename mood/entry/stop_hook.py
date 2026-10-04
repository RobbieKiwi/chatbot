"""Stop hook: after each of the assistant's replies, launch the observer that nudges its mood, unless one is already running for this session."""

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

from mood.adapters.locks import observer_lock_path, release_lock, try_lock
from mood.adapters.paths import PROJECT_ROOT, mood_paths
from mood.adapters.processes import spawn_detached
from mood.adapters.sessions import load_config, load_mood
from mood.entry.common import log_exception
from mood.models.paths import MoodPaths

LOCK_GRACE = timedelta(minutes=1)  # beyond the observer's own timeout


class StopPayload(BaseModel):
    session_id: str
    transcript_path: Path


def observe_command(*, parent: str, session_id: str, transcript_path: Path) -> list[str]:
    return [sys.executable, "-m", "mood", "observe", "--parent", parent, "--session", session_id, "--transcript", str(transcript_path)]


def handle_stop(*, payload: StopPayload, paths: MoodPaths, now: datetime, spawn: Callable[[list[str]], None]) -> None:
    if load_mood(paths=paths, session_id=payload.session_id) is None:
        return
    lock = observer_lock_path(paths=paths, session_id=payload.session_id)
    stale_after = timedelta(seconds=load_config(paths=paths).observer_timeout_s) + LOCK_GRACE
    if not try_lock(path=lock, now=now, stale_after=stale_after):
        return
    try:
        spawn(observe_command(parent=paths.parent, session_id=payload.session_id, transcript_path=payload.transcript_path))
    except BaseException:
        release_lock(path=lock)
        raise


def spawn_observer(command: list[str]) -> None:
    spawn_detached(args=command, cwd=PROJECT_ROOT, log_path=mood_paths(parent=command[command.index("--parent") + 1]).logs / "observer_process.log")


def main(*, argv: list[str], stdin_bytes: bytes) -> None:
    parser = argparse.ArgumentParser(prog="python -m mood.entry.stop_hook")
    parser.add_argument("--parent", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return
    paths = mood_paths(parent=args.parent)
    try:
        handle_stop(payload=StopPayload.model_validate_json(stdin_bytes), paths=paths, now=datetime.now(UTC), spawn=lambda command: spawn_observer(command))
    except Exception:
        log_exception(paths=paths, name="stop_hook")


if __name__ == "__main__":
    main(argv=sys.argv[1:], stdin_bytes=sys.stdin.buffer.read())
    raise SystemExit(0)
