from mood.domain.render import render_mood
from mood.tests.conftest import mood_state


def test_feelings_largest_first() -> None:
    state = mood_state(melancholy=6.6, playfulness=4.2, irritation=1.1, restlessness=0.9, cheerfulness=0.3, presence=2.8)
    assert render_mood(state=state) == '<mood presence="3/10">melancholy 7 · playfulness 4 · irritation 1 · restlessness 1 · cheerfulness 0</mood>'
