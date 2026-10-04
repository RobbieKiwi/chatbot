"""UserPromptSubmit hook: a message starting with fb: is filed as feedback on the assistant and blocked, so it never reaches the assistant."""

import argparse
import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from clauderecords.turns import last_text_turns, render_turns
from feedback.adapters.paths import feedback_path, logs_dir
from feedback.adapters.store import editing_feedback
from feedback.domain.commands import parse_feedback
from feedback.domain.filing import file_feedback
from feedback.models.commands import EmptyFeedback
from persona.adapters.files import load_names
from persona.domain.names import user_label
from persona.models import PersonaError

CONTEXT_TURNS = 10


class HookPayload(BaseModel):
    session_id: str
    transcript_path: Path
    prompt: str = ""


def _block(*, reason: str) -> str:
    return json.dumps({"decision": "block", "reason": reason})


def handle_prompt(*, payload: HookPayload, path: Path, now: datetime) -> str:
    command = parse_feedback(prompt=payload.prompt)
    if command is None:
        return ""
    if isinstance(command, EmptyFeedback):
        return _block(reason="say what you'd like changed")
    try:
        names = load_names()
    except PersonaError as error:
        return _block(reason=f"feedback not filed: {error}")
    turns = last_text_turns(transcript_path=payload.transcript_path, count=CONTEXT_TURNS)
    context = render_turns(turns=turns, user_name=user_label(names=names), assistant_name=names.assistant_name)
    with editing_feedback(path=path) as feedback:
        item_id = file_feedback(feedback=feedback, command=command, context=context, now=now)
    return _block(reason=f"feedback #{item_id} logged")


def _log(*, message: str) -> None:
    try:
        logs_dir().mkdir(parents=True, exist_ok=True)
        with (logs_dir() / "hook.log").open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now(UTC).isoformat()} {message}\n")
    except OSError:
        pass


def main(*, argv: list[str], stdin_bytes: bytes) -> str:
    parser = argparse.ArgumentParser(prog="python -m feedback.entry.hook")
    parser.add_argument("--parent", required=True)
    try:
        args = parser.parse_args(argv)
        payload = HookPayload.model_validate_json(stdin_bytes)
        return handle_prompt(payload=payload, path=feedback_path(parent=args.parent), now=datetime.now(UTC))
    except SystemExit:
        return ""
    except Exception:
        _log(message=traceback.format_exc())
        return ""


if __name__ == "__main__":
    output = main(argv=sys.argv[1:], stdin_bytes=sys.stdin.buffer.read())
    if output:
        sys.stdout.buffer.write(output.encode("utf-8"))
    raise SystemExit(0)
