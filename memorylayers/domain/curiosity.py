"""The assistant's curiosity: which gaps in memory it may be nudged towards."""

from datetime import datetime, timedelta
from random import Random

from memorylayers.models.views import GapLine


def available_gaps(*, gaps: list[GapLine], now: datetime, cooldown_days: int) -> list[GapLine]:
    cutoff = now - timedelta(days=cooldown_days)
    return [gap for gap in gaps if gap.last_shown_at is None or gap.last_shown_at <= cutoff]


def curiosity_fires(*, messages_seen: int, skip_turns: int, every_turns: int, rng: Random) -> bool:
    if messages_seen <= skip_turns or every_turns <= 0:
        return False
    return rng.random() < 1 / every_turns


def pick_gap(*, gaps: list[GapLine], rng: Random) -> GapLine | None:
    return rng.choice(gaps) if gaps else None


def render_curiosity(*, gap: GapLine) -> str:
    return f'<curiosity tag="{gap.tag}">{gap.text}</curiosity>'
