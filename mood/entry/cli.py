"""mood's command line: the observer the Stop hook launches, and a report of a session's mood."""

import argparse
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

from clauderecords.turns import last_text_turns, render_turns
from mood.adapters.locks import observer_lock_path, release_lock
from mood.adapters.paths import PROJECT_ROOT, PROMPTS_DIR, mood_paths
from mood.adapters.processes import find_claude, run_observer_claude
from mood.adapters.sessions import latest_session_id, load_config, load_mood, save_mood
from mood.domain.clamp import apply_reply
from mood.domain.observer import ObserverReplyError, build_observer_brief, parse_observer_output
from mood.domain.render import render_mood_report
from mood.entry.common import log, log_exception
from mood.models.config import MoodConfig
from mood.models.paths import MoodPaths
from persona.adapters.files import load_names, read_mood_scales
from persona.domain.names import user_label
from persona.models import PersonaError


def observe(*, paths: MoodPaths, session_id: str, transcript_path: Path, config: MoodConfig, call_observer: Callable[[str], str], now: Callable[[], datetime]) -> None:
    names, scales = load_names(), read_mood_scales()
    state = load_mood(paths=paths, session_id=session_id)
    turns = last_text_turns(transcript_path=transcript_path, count=config.observer_turns)
    if state is None or not turns:
        return
    template = (PROMPTS_DIR / "observer.md").read_text(encoding="utf-8")
    rendered = render_turns(turns=turns, user_name=user_label(names=names), assistant_name=names.assistant_name)
    brief = build_observer_brief(template=template, state=state, turns=rendered, names=names, scales=scales)
    reply = parse_observer_output(output=call_observer(brief))
    latest = load_mood(paths=paths, session_id=session_id)
    if latest is None or latest.rolled_at != state.rolled_at:
        return  # rerolled while the observer ran: the fresh roll stands
    save_mood(paths=paths, session_id=session_id, state=apply_reply(state=latest, reply=reply, config=config, now=now()))


def show(*, paths: MoodPaths, session_id: str | None, history_count: int) -> str:
    session_id = session_id or latest_session_id(paths=paths)
    state = load_mood(paths=paths, session_id=session_id) if session_id else None
    if session_id is None or state is None:
        return f"no mood for {session_id or 'any session'} under {paths.sessions}"
    return render_mood_report(session_id=session_id, state=state, history_count=history_count)


def main(*, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m mood", description="The assistant's mood.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("observe", help="Nudge one session's mood from its last turns. Launched by the Stop hook, which holds the session's lock.")
    run.add_argument("--parent", required=True)
    run.add_argument("--session", required=True)
    run.add_argument("--transcript", required=True, type=Path)
    report = subparsers.add_parser("show", help="Print a session's mood as the assistant sees it, with its latest nudges and their reasons.")
    report.add_argument("--parent", default="chatbot")
    report.add_argument("--session", help="Session id; defaults to the most recently updated session.")
    report.add_argument("--history", type=int, default=5, help="How many of the latest nudges to list.")
    args = parser.parse_args(argv)
    paths = mood_paths(parent=args.parent)
    if args.command == "show":
        sys.stdout.buffer.write((show(paths=paths, session_id=args.session, history_count=args.history) + "\n").encode("utf-8"))
        return 0
    try:
        config = load_config(paths=paths)
        claude = find_claude(executable=config.claude_executable)
        if claude is None:
            log(paths=paths, name="observer", message=f"{config.claude_executable!r} not found; mood unchanged")
            return 1
        call = partial(run_observer_claude, claude=claude, model=config.observer_model, timeout_s=config.observer_timeout_s, cwd=PROJECT_ROOT)
        observe(paths=paths, session_id=args.session, transcript_path=args.transcript, config=config, call_observer=lambda brief: call(brief=brief), now=lambda: datetime.now(UTC))
    except (ObserverReplyError, PersonaError, subprocess.TimeoutExpired) as error:
        log(paths=paths, name="observer", message=f"mood unchanged: {error}")
        return 1
    except Exception:
        log_exception(paths=paths, name="observer")
        return 1
    finally:
        release_lock(path=observer_lock_path(paths=paths, session_id=args.session))
    return 0
