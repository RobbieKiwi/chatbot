"""Per-parent settings: defaults here, overridden by the parent's config.json."""

from pydantic import BaseModel, ConfigDict


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scribe_threshold_chars: int = 8000
    overlap_fraction: float = 0.3  # share of the threshold re-shown from the previous window
    idle_hours: float = 12
    pending_settle_runs: int = 2
    refresh_after_facts: int = 10
    duplicate_overlap: float = 0.5  # Jaccard overlap of content tokens
    stale_lock_minutes: int = 30
    max_consecutive_failures: int = 3
    recent_turns: int = 6
    scribe_model: str = "sonnet"
    summariser_model: str = "sonnet"
    local_timezone: str = "UTC"  # IANA zone name
    claude_executable: str = "claude"
    gap_cooldown_days: int = 14  # a gap shown to the assistant rests this long
    curiosity_skip_turns: int = 3  # no curiosity during a conversation's first messages
    curiosity_every_turns: int = 8  # after that, curiosity fires with probability 1 / this
