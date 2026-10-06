"""How fast the mood may move, and how the observer runs: defaults here, overridden by the parent's config.json."""

from pydantic import BaseModel, ConfigDict


class MoodConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    axis_swing_minutes: float = 60  # conversation needed for a full 0–10 swing of a feeling
    presence_swing_minutes: float = 10
    presence_drift_per_minute: float = 0.1  # towards presence_base, when nothing pushes presence
    max_elapsed_minutes: float = 15  # a longer pause counts as this much conversation
    history_limit: int = 20
    thoughts_limit: int = 3
    observer_turns: int = 6
    observer_model: str = "haiku"
    observer_timeout_s: float = 120
    claude_executable: str = "claude"
