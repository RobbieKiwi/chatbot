from datetime import datetime, timedelta

import pytest

from mood.domain.clamp import apply_reply
from mood.models.config import MoodConfig
from mood.models.mood import Axis, ObserverReply
from mood.tests.conftest import NOW, mood_state

CONFIG = MoodConfig()


def _after(*, minutes: float) -> datetime:
    return NOW + timedelta(minutes=minutes)


def test_a_nudge_is_capped_by_elapsed_time() -> None:
    state = apply_reply(state=mood_state(playfulness=4), reply=ObserverReply(deltas={Axis.PLAYFULNESS: 3}, reason="a good joke"), config=CONFIG, now=_after(minutes=3))
    assert state.playfulness == pytest.approx(4.5)
    assert state.updated_at == _after(minutes=3)
    assert state.history[-1].deltas == {Axis.PLAYFULNESS: pytest.approx(0.5)} and state.history[-1].reason == "a good joke"


def test_idle_time_counts_as_fifteen_minutes() -> None:
    state = apply_reply(state=mood_state(irritation=2), reply=ObserverReply(deltas={Axis.IRRITATION: 3}), config=CONFIG, now=_after(minutes=120))
    assert state.irritation == pytest.approx(4.5)


def test_a_full_swing_takes_an_hour_of_turns() -> None:
    state = mood_state(melancholy=0)
    for minute in range(1, 61):
        state = apply_reply(state=state, reply=ObserverReply(deltas={Axis.MELANCHOLY: 3}), config=CONFIG, now=_after(minutes=minute))
        if minute == 59:
            assert state.melancholy < 10
    assert state.melancholy == pytest.approx(10)
    assert len(state.history) == CONFIG.history_limit


def test_values_stay_on_the_scale() -> None:
    state = apply_reply(state=mood_state(irritation=0.2, cheerfulness=9.9), reply=ObserverReply(deltas={Axis.IRRITATION: -3, Axis.CHEERFULNESS: 3}), config=CONFIG, now=_after(minutes=15))
    assert (state.irritation, state.cheerfulness) == (0, 10)


def test_presence_moves_faster_than_feelings() -> None:
    state = apply_reply(state=mood_state(presence=2, presence_base=2), reply=ObserverReply(presence_delta=3, probing=True), config=CONFIG, now=_after(minutes=3))
    assert state.presence == pytest.approx(5)


@pytest.mark.parametrize(
    ("delta", "probing", "expected"),
    [
        (0, False, 7.5),  # nothing pushes presence: it drifts home by 0.1 a minute
        (0, True, 8.0),  # the user is asking how the assistant feels: no drift
        (-1, False, 7.0),  # pushed towards base: no extra drift
        (1, False, 8.5),  # pushed away from base: the push, then the drift
    ],
)
def test_presence_drifts_to_its_base(delta: float, probing: bool, expected: float) -> None:
    state = apply_reply(state=mood_state(presence=8, presence_base=3), reply=ObserverReply(presence_delta=delta, probing=probing), config=CONFIG, now=_after(minutes=5))
    assert state.presence == pytest.approx(expected)


def test_drift_stops_at_the_base() -> None:
    state = apply_reply(state=mood_state(presence=3.2, presence_base=3), reply=ObserverReply(), config=CONFIG, now=_after(minutes=15))
    assert state.presence == pytest.approx(3)


def test_a_clock_running_backwards_moves_nothing() -> None:
    before = mood_state(playfulness=4, presence=8, presence_base=3)
    after = apply_reply(state=before, reply=ObserverReply(deltas={Axis.PLAYFULNESS: 3}, presence_delta=3), config=CONFIG, now=NOW - timedelta(minutes=5))
    assert (after.playfulness, after.presence) == (4, 8)


def test_thoughts_are_rewritten_trimmed_and_capped() -> None:
    before = mood_state().model_copy(update={"thoughts": ["old"]})
    reply = ObserverReply(thoughts=[" one ", "", "two", "three", "four"])
    assert apply_reply(state=before, reply=reply, config=CONFIG, now=_after(minutes=1)).thoughts == ["one", "two", "three"]


def test_a_reply_without_thoughts_keeps_hers() -> None:
    before = mood_state().model_copy(update={"thoughts": ["old"]})
    assert apply_reply(state=before, reply=ObserverReply(), config=CONFIG, now=_after(minutes=1)).thoughts == ["old"]
