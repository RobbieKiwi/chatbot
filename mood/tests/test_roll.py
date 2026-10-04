import random

from mood.domain.roll import roll_mood
from mood.models.mood import Axis
from mood.tests.conftest import NOW


def test_one_dominant_feeling_per_roll() -> None:
    rng = random.Random(7)
    dominants = set()
    for _ in range(3000):
        state = roll_mood(rng=rng, now=NOW)
        [dominant] = [axis for axis in Axis if state.value(axis=axis) > 4]
        assert 6 <= state.value(axis=dominant) <= 9
        assert all(0 <= state.value(axis=axis) <= 10 for axis in Axis)
        assert 1 <= state.presence <= 10 and state.presence == state.presence_base
        assert state.rolled_at == state.updated_at == NOW and state.history == []
        dominants.add(dominant)
    assert dominants == set(Axis)


def test_the_roll_is_seeded() -> None:
    assert roll_mood(rng=random.Random(1), now=NOW) == roll_mood(rng=random.Random(1), now=NOW)
