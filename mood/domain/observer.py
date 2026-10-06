"""The observer's brief, and reading its reply out of claude's JSON envelope."""

import json
from string import Template

from pydantic import ValidationError

from mood.domain.render import render_mood, render_thoughts
from mood.models.mood import MoodState, ObserverReply
from persona.domain.names import user_label
from persona.models import PersonaNames


class ObserverReplyError(ValueError):
    """The observer answered with something that is not a valid mood nudge."""


def build_observer_brief(*, template: str, state: MoodState, turns: str, names: PersonaNames, scales: str) -> str:
    """`scales` is the persona's mood-scale table, which the observer judges the turns against."""
    return Template(template).substitute(
        mood=render_mood(state=state),
        thoughts=render_thoughts(state=state) or "(none yet)",
        turns=turns,
        scales=scales,
        user=user_label(names=names),
        assistant=names.assistant_name,
    )


def parse_observer_output(*, output: str) -> ObserverReply:
    """`claude -p --output-format json` wraps the model's text in an envelope; the text may hold prose or a code fence around the JSON."""
    try:
        envelope = json.loads(output)
    except json.JSONDecodeError as error:
        raise ObserverReplyError(f"claude output is not JSON: {output[:200]!r}") from error
    if not isinstance(envelope, dict) or envelope.get("is_error") or not isinstance(envelope.get("result"), str):
        raise ObserverReplyError(f"claude reported no result: {output[:200]!r}")
    text = envelope["result"]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ObserverReplyError(f"no JSON object in the reply: {text[:200]!r}")
    try:
        return ObserverReply.model_validate_json(text[start : end + 1])
    except ValidationError as error:
        raise ObserverReplyError(str(error)) from error
