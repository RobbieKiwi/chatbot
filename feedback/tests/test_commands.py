import pytest

from feedback.domain.commands import parse_feedback
from feedback.models.commands import AddNote, EmptyFeedback, NewItem


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("fb: too many questions in a row", NewItem(text="too many questions in a row")),
        ("  FB:  louder please ", NewItem(text="louder please")),
        ("fb:fewer jokes", NewItem(text="fewer jokes")),
        ("fb: #3 still doing it", AddNote(item_id=3, text="still doing it")),
        ("fb:#3 still doing it", AddNote(item_id=3, text="still doing it")),
        ("fb: #abc is not an id", NewItem(text="#abc is not an id")),
        ("fb:", EmptyFeedback()),
        ("fb:   ", EmptyFeedback()),
        ("fb: #3", EmptyFeedback()),
        ("fb: line one\nline two", NewItem(text="line one\nline two")),
    ],
)
def test_feedback_prefixes(prompt: str, expected: object) -> None:
    assert parse_feedback(prompt=prompt) == expected


@pytest.mark.parametrize("prompt", ["hello", "fb no colon", "fbx: is a word", "!fb bash mode", "say fb: later", ""])
def test_ordinary_messages_are_not_feedback(prompt: str) -> None:
    assert parse_feedback(prompt=prompt) is None
