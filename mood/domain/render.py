"""The mood the assistant reads on every message."""

from mood.models.mood import Axis, MoodState


def render_mood(*, state: MoodState) -> str:
    feelings = sorted(Axis, key=lambda axis: -round(state.value(axis=axis)))  # stable: ties keep the scales' order
    parts = " · ".join(f"{axis.value} {round(state.value(axis=axis))}" for axis in feelings)
    return f'<mood presence="{round(state.presence)}/10">{parts}</mood>'
