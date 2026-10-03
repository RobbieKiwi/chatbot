"""resume: register this session, print where the conversation stands, and catch the scribe up."""

import argparse
from datetime import timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from memorylayers.adapters.paths import PROJECT_ROOT
from memorylayers.adapters.processes import find_claude, runner_command
from memorylayers.adapters.state_files import list_conversations, load_config, load_registry, load_summariser_health, save_conversation, update_conversation, update_registry
from memorylayers.adapters.transcripts import newest_session, read_conversation_turns
from memorylayers.domain.resume import assemble_resume, choose_conversation, recent_turns
from memorylayers.entry.common import CLI, CliError, add_parent, now_utc, paths_of
from memorylayers.entry.launch import spawn_runner
from memorylayers.models.conversation import ConversationState, SessionLink
from memorylayers.models.vocab import WorkerKind
from persona.adapters.files import load_names

REGISTRATION_WINDOW = timedelta(minutes=10)
HOME = Path.home()


def register(*, subparsers: Any) -> None:
    resume = subparsers.add_parser("resume", help="Start or resume the conversation: summaries, recent turns, catch-up.")
    add_parent(parser=resume)
    resume.set_defaults(handler=_resume)


def _attach(*, state: ConversationState, session_id: str, transcript: Path, now: Any) -> None:
    if all(link.session_id != session_id for link in state.sessions):
        state.sessions.append(SessionLink(session_id=session_id, transcript_path=transcript))
    state.last_activity = now


def _resume(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    config = load_config(paths=paths)
    tz = ZoneInfo(config.local_timezone)
    now = now_utc()
    warnings: list[str] = []
    pending = load_registry(paths=paths).pending
    if pending is not None and now - pending.seen_at <= REGISTRATION_WINDOW:
        session_id, transcript = pending.session_id, pending.transcript_path
    else:
        found = newest_session(project_dir=PROJECT_ROOT, home=HOME)
        if found is None:
            raise CliError(f"no session to register: start the conversation with /{paths.parent}")
        session_id, transcript = found
        warnings.append("registered the newest transcript in this project; the hook recorded no registration")
    conversations = list_conversations(paths=paths)
    current = choose_conversation(conversations=conversations, now=now, idle_hours=config.idle_hours)
    joined = current is not None
    if current is not None:
        current = update_conversation(paths=paths, conversation_id=current.id, change=lambda state: _attach(state=state, session_id=session_id, transcript=transcript, now=now))
    else:
        current = ConversationState(id=f"{now.astimezone(tz):%Y-%m-%d-%H%M%S}", started_at=now, last_activity=now)
        _attach(state=current, session_id=session_id, transcript=transcript, now=now)
        save_conversation(paths=paths, state=current)
    conversation_id = current.id

    def link(registry: Any) -> None:
        registry.sessions[session_id] = conversation_id
        registry.pending = None

    update_registry(paths=paths, change=link)

    claude = find_claude(executable=config.claude_executable)
    if claude is None:
        warnings.append(f"{config.claude_executable!r} is not on PATH: memory will not be filed until it is")
    stopped = [state.id for state in list_conversations(paths=paths) if state.scribe_health.stopped_reason]
    if stopped or load_summariser_health(paths=paths).stopped_reason:
        warnings.append(f"memory workers stopped after repeated failures; see {CLI} status --parent {paths.parent}, then run .venv/Scripts/python -m memorylayers.scripts.unstick")

    turns = read_conversation_turns(state=current, tz=tz)
    shown = recent_turns(processed=turns.processed, unprocessed=turns.unprocessed, threshold_chars=config.scribe_threshold_chars, recent_count=config.recent_turns)
    previous = conversations[-1].rolling_summary if conversations and not joined else None
    high_level = paths.summary.read_text(encoding="utf-8") if paths.summary.exists() else None
    print(
        assemble_resume(
            high_level_summary=high_level,
            joined=joined,
            rolling_summary=current.rolling_summary,
            previous_summary=previous,
            turns=shown,
            warnings=warnings,
            names=load_names(),
        )
    )
    tails = any(read_conversation_turns(state=state, tz=tz, include_processed=False).unprocessed for state in list_conversations(paths=paths))
    if claude is not None and tails:
        spawn_runner(paths=paths, command=runner_command(parent=paths.parent, kind=WorkerKind.SCRIBE, catch_up=True))
