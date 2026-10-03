"""What the assistant reads when a conversation starts or resumes."""

from datetime import datetime, timedelta

from memorylayers.domain.briefs import render_turns
from memorylayers.models.conversation import ConversationState
from memorylayers.models.transcript import Turn
from persona.models import PersonaNames


def choose_conversation(*, conversations: list[ConversationState], now: datetime, idle_hours: float) -> ConversationState | None:
    """The most recent conversation, if it was active within idle_hours."""
    if not conversations:
        return None
    latest = conversations[-1]
    return latest if now - latest.last_activity <= timedelta(hours=idle_hours) else None


def recent_turns(*, processed: list[Turn], unprocessed: list[Turn], threshold_chars: int, recent_count: int) -> list[Turn]:
    """The unprocessed turns verbatim (bounded by the threshold), topped up from processed ones to recent_count."""
    shown: list[Turn] = []
    used = 0
    for turn in reversed(unprocessed):
        if shown and used + len(turn.text) > threshold_chars:
            break
        shown.insert(0, turn)
        used += len(turn.text)
    missing = recent_count - len(shown)
    return (processed[-missing:] if missing > 0 and processed else []) + shown


def assemble_resume(*, high_level_summary: str | None, joined: bool, rolling_summary: str, previous_summary: str | None, turns: list[Turn], warnings: list[str], names: PersonaNames) -> str:
    parts = [f"WARNING: {warning}" for warning in warnings]
    parts += ["## High-level summary", high_level_summary or "(none yet)"]
    if joined:
        parts += ["## This conversation so far", rolling_summary or "(nothing filed yet)", "## Recent turns", render_turns(turns=turns, names=names)]
    else:
        parts += ["## Last conversation", previous_summary or "(this is the first conversation)"]
    return "\n\n".join(parts)
