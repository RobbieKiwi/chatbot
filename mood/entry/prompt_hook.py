"""UserPromptSubmit hook: rolls the assistant's mood when a conversation starts and shows it, with its private thoughts, on every message."""

import argparse
import random
import sys
from datetime import UTC, datetime
from random import Random

from mood.adapters.paths import mood_paths
from mood.adapters.sessions import load_mood, save_mood
from mood.domain.render import render_for_assistant
from mood.domain.roll import roll_mood
from mood.entry.common import HookPayload, is_registration_prompt, log_exception
from mood.models.paths import MoodPaths


def handle_prompt(*, payload: HookPayload, paths: MoodPaths, now: datetime, rng: Random) -> str:
    if is_registration_prompt(prompt=payload.prompt, parent=paths.parent):
        state = roll_mood(rng=rng, now=now)
        save_mood(paths=paths, session_id=payload.session_id, state=state)
        return render_for_assistant(state=state)
    state = load_mood(paths=paths, session_id=payload.session_id)
    return render_for_assistant(state=state) if state else ""


def main(*, argv: list[str], stdin_bytes: bytes) -> str:
    parser = argparse.ArgumentParser(prog="python -m mood.entry.prompt_hook")
    parser.add_argument("--parent", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return ""
    paths = mood_paths(parent=args.parent)
    try:
        return handle_prompt(payload=HookPayload.model_validate_json(stdin_bytes), paths=paths, now=datetime.now(UTC), rng=random.Random())
    except Exception:
        log_exception(paths=paths, name="prompt_hook")
        return ""


if __name__ == "__main__":
    output = main(argv=sys.argv[1:], stdin_bytes=sys.stdin.buffer.read())
    if output:
        sys.stdout.buffer.write(output.encode("utf-8"))
    raise SystemExit(0)
