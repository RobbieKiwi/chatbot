"""The mood a conversation opens with: one dominant feeling, the rest quiet."""

from datetime import datetime
from random import Random

from mood.models.mood import Axis, MoodState

DOMINANT_FEELING = (6.0, 9.0)
QUIET_FEELING = (0.0, 4.0)
PRESENCE = (1.0, 10.0)


def roll_mood(*, rng: Random, now: datetime) -> MoodState:
    dominant = rng.choice(list(Axis))
    values: dict[str, object] = {axis.value: rng.uniform(*(DOMINANT_FEELING if axis is dominant else QUIET_FEELING)) for axis in Axis}
    presence = rng.uniform(*PRESENCE)
    return MoodState.model_validate(values | {"presence": presence, "presence_base": presence, "rolled_at": now, "updated_at": now})
