"""Applying the observer's nudges with caps set by elapsed conversation, so the length of the conversation, not the observer, decides how far the mood can move."""

import math
from datetime import datetime

from mood.models.config import MoodConfig
from mood.models.mood import Axis, MoodState, MoodUpdate, ObserverReply

SCALE = 10.0


def _clip(*, value: float) -> float:
    return min(max(value, 0.0), SCALE)


def _capped(*, delta: float, cap: float) -> float:
    return min(max(delta, -cap), cap)


def apply_reply(*, state: MoodState, reply: ObserverReply, config: MoodConfig, now: datetime) -> MoodState:
    minutes = min(max((now - state.updated_at).total_seconds() / 60, 0.0), config.max_elapsed_minutes)
    axis_cap = minutes * SCALE / config.axis_swing_minutes
    presence_cap = minutes * SCALE / config.presence_swing_minutes

    values: dict[str, float] = {}
    applied: dict[Axis, float] = {}
    for axis in Axis:
        before = state.value(axis=axis)
        after = _clip(value=before + _capped(delta=reply.deltas.get(axis, 0.0), cap=axis_cap))
        values[axis.value] = after
        if after != before:
            applied[axis] = after - before

    home = state.presence_base - state.presence
    presence = _clip(value=state.presence + _capped(delta=reply.presence_delta, cap=presence_cap))
    if not reply.probing and reply.presence_delta * home <= 0:  # nothing pushes presence home, so it drifts there
        gap = state.presence_base - presence
        presence += math.copysign(min(abs(gap), minutes * config.presence_drift_per_minute), gap)

    thoughts = state.thoughts if reply.thoughts is None else [thought.strip() for thought in reply.thoughts if thought.strip()][: config.thoughts_limit]
    update = MoodUpdate(at=now, deltas=applied, presence_delta=presence - state.presence, reason=reply.reason)
    return state.model_copy(update={**values, "presence": _clip(value=presence), "updated_at": now, "thoughts": thoughts, "history": [*state.history, update][-config.history_limit :]})
