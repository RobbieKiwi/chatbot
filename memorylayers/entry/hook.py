"""UserPromptSubmit hook: memory hints for the persona, and the launch of due workers. It never blocks a message."""

import argparse
import sys
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from memorylayers.adapters.hook_store import read_hint_index, read_refresh_status
from memorylayers.adapters.paths import parent_paths
from memorylayers.adapters.processes import find_claude, runner_command
from memorylayers.adapters.state_files import load_config, load_conversation, load_registry, load_summariser_health, update_conversation, update_registry
from memorylayers.adapters.transcripts import read_conversation_turns
from memorylayers.domain.due import scribe_due, summariser_due
from memorylayers.domain.hints import HINT_LIMIT, match_hints, render_hints
from memorylayers.domain.window import unprocessed_chars
from memorylayers.entry.launch import kind_is_free, spawn_runner
from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import ConversationState, PendingRegistration
from memorylayers.models.paths import ParentPaths
from memorylayers.models.vocab import WorkerKind
from memorylayers.tools.calendar import week_start
from memorylayers.tools.date_mentions import period_names_mentioned

Spawn = Callable[[list[str]], None]


class HookPayload(BaseModel):
    session_id: str
    transcript_path: Path
    prompt: str = ""


def is_registration_prompt(*, prompt: str, parent: str) -> bool:
    stripped = prompt.strip()
    return stripped == f"/{parent}" or stripped.startswith(f"/{parent} ") or f"<command-name>/{parent}</command-name>" in stripped


def _launch_due(*, paths: ParentPaths, config: MemoryConfig, state: ConversationState, now: datetime, spawn: Spawn) -> None:
    tz = ZoneInfo(config.local_timezone)
    if not state.scribe_health.stopped_reason:
        turns = read_conversation_turns(state=state, tz=tz, include_processed=False)
        if scribe_due(unprocessed_chars=unprocessed_chars(turns=turns.unprocessed), threshold_chars=config.scribe_threshold_chars) and kind_is_free(paths=paths, kind=WorkerKind.SCRIBE, now=now):
            spawn(runner_command(parent=paths.parent, kind=WorkerKind.SCRIBE, conversation_id=state.id))
    if load_summariser_health(paths=paths).stopped_reason:
        return
    today_week = week_start(day=now.astimezone(tz).date())
    status = read_refresh_status(db_path=paths.db)
    if summariser_due(status=status, refresh_after_facts=config.refresh_after_facts, today_week_start=today_week) and kind_is_free(paths=paths, kind=WorkerKind.SUMMARISER, now=now):
        spawn(runner_command(parent=paths.parent, kind=WorkerKind.SUMMARISER))


def handle_prompt(*, payload: HookPayload, paths: ParentPaths, now: datetime, spawn: Spawn, claude_available: Callable[[], bool]) -> str:
    if is_registration_prompt(prompt=payload.prompt, parent=paths.parent):
        pending = PendingRegistration(session_id=payload.session_id, transcript_path=payload.transcript_path, seen_at=now)
        update_registry(paths=paths, change=lambda registry: setattr(registry, "pending", pending))
        return ""
    conversation_id = load_registry(paths=paths).sessions.get(payload.session_id)
    if conversation_id is None:
        return ""
    config = load_config(paths=paths)
    today = now.astimezone(ZoneInfo(config.local_timezone)).date()
    shown = set(load_conversation(paths=paths, conversation_id=conversation_id).hints_shown)
    pointers = match_hints(
        message=payload.prompt,
        index=read_hint_index(db_path=paths.db, message=payload.prompt),
        mentions=period_names_mentioned(text=payload.prompt, today=today),
        shown=shown,
        limit=HINT_LIMIT,
    )

    def note(state: ConversationState) -> None:
        state.hints_shown.extend(pointer.key for pointer in pointers)
        state.last_activity = now

    state = update_conversation(paths=paths, conversation_id=conversation_id, change=note)
    if claude_available():
        _launch_due(paths=paths, config=config, state=state, now=now, spawn=spawn)
    else:
        _log(paths=paths, message=f"{config.claude_executable!r} not found; no workers launched")
    return render_hints(pointers=pointers)


def _log(*, paths: ParentPaths, message: str) -> None:
    try:
        paths.logs.mkdir(parents=True, exist_ok=True)
        with (paths.logs / "hook.log").open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now(UTC).isoformat()} {message}\n")
    except OSError:
        pass


def main(*, argv: list[str], stdin_bytes: bytes) -> str:
    parser = argparse.ArgumentParser(prog="python -m memorylayers.entry.hook")
    parser.add_argument("--parent", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return ""
    paths = parent_paths(parent=args.parent)
    try:
        payload = HookPayload.model_validate_json(stdin_bytes)
        executable = load_config(paths=paths).claude_executable
        return handle_prompt(
            payload=payload,
            paths=paths,
            now=datetime.now(UTC),
            spawn=lambda command: spawn_runner(paths=paths, command=command),
            claude_available=lambda: find_claude(executable=executable) is not None,
        )
    except Exception:
        _log(paths=paths, message=traceback.format_exc())
        return ""


if __name__ == "__main__":
    output = main(argv=sys.argv[1:], stdin_bytes=sys.stdin.buffer.read())
    if output:
        sys.stdout.buffer.write(output.encode("utf-8"))
    raise SystemExit(0)
