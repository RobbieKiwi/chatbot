from mood.domain.render import render_mood, render_mood_cue, render_mood_report, strongest_axes
from mood.models.mood import Axis, MoodUpdate
from mood.tests.conftest import NOW, mood_state


def test_feelings_largest_first() -> None:
    state = mood_state(melancholy=6.6, playfulness=4.2, irritation=1.1, restlessness=0.9, cheerfulness=0.3, presence=2.8)
    assert render_mood(state=state) == '<mood presence="3/10">melancholy 7 · playfulness 4 · irritation 1 · restlessness 1 · cheerfulness 0</mood>'


def test_the_cue_names_strong_feelings() -> None:
    state = mood_state(cheerfulness=9.6, playfulness=7.2, restlessness=6.1)
    assert render_mood_cue(state=state).startswith("Strongest now: cheerfulness 10, playfulness 7. ")


def test_without_a_strong_feeling_the_cue_names_the_largest() -> None:
    assert strongest_axes(state=mood_state(melancholy=4.6, cheerfulness=3.0)) == [Axis.MELANCHOLY]


def test_the_report_lists_the_latest_nudges_with_their_reasons() -> None:
    nudge = MoodUpdate(at=NOW, deltas={Axis.IRRITATION: 0.5, Axis.CHEERFULNESS: 0.01}, presence_delta=-0.2, reason="he dodged the question")
    report = render_mood_report(session_id="s1", state=mood_state(irritation=8).model_copy(update={"history": [nudge, nudge]}), history_count=1)
    assert report.splitlines()[-1] == "  20:00  he dodged the question  (irritation +0.5; presence -0.2)"
    assert report.count("he dodged") == 1
