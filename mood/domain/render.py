"""The mood and private thoughts the assistant reads on every message, the cue that turns them into action, and the report a person reads."""

from mood.models.mood import Axis, MoodState

STRONG_AT = 7  # a feeling this strong is a want the assistant acts on


def render_mood(*, state: MoodState) -> str:
    feelings = sorted(Axis, key=lambda axis: -round(state.value(axis=axis)))  # stable: ties keep the scales' order
    parts = " · ".join(f"{axis.value} {round(state.value(axis=axis))}" for axis in feelings)
    return f'<mood presence="{round(state.presence)}/10">{parts}</mood>'


def strongest_axes(*, state: MoodState) -> list[Axis]:
    """The feelings pulling hardest right now: every strong feeling, or the largest if none is."""
    feelings = sorted(Axis, key=lambda axis: -round(state.value(axis=axis)))
    return [axis for axis in feelings if round(state.value(axis=axis)) >= STRONG_AT] or feelings[:1]


def render_mood_cue(*, state: MoodState) -> str:
    pulls = ", ".join(f"{axis.value} {round(state.value(axis=axis))}" for axis in strongest_axes(state=state))
    return f"Strongest now: {pulls}. Let them decide what you do and where the conversation goes in this reply. Show them; never list your feelings."


def render_thoughts(*, state: MoodState) -> str:
    return "<thoughts>\n" + "\n".join(f"- {thought}" for thought in state.thoughts) + "\n</thoughts>" if state.thoughts else ""


def render_for_assistant(*, state: MoodState) -> str:
    """What the assistant reads on every message: the mood, its private thoughts, and the cue to act on both."""
    cue = render_mood_cue(state=state) + (" Your thoughts are private: act on them, never quote them." if state.thoughts else "")
    return "\n".join(part for part in (render_mood(state=state), render_thoughts(state=state), cue) if part)


def render_mood_report(*, session_id: str, state: MoodState, history_count: int) -> str:
    lines = [
        f"session {session_id}",
        f"rolled {state.rolled_at:%Y-%m-%d %H:%M} UTC, updated {state.updated_at:%H:%M} UTC, {len(state.history)} nudges",
        render_for_assistant(state=state),
    ]
    for update in state.history[-history_count:] if history_count > 0 else []:
        deltas = ", ".join(f"{axis.value} {delta:+.1f}" for axis, delta in update.deltas.items() if round(delta, 1))
        lines.append(f"  {update.at:%H:%M}  {update.reason}  ({deltas or 'no change'}; presence {update.presence_delta:+.1f})")
    return "\n".join(lines)
