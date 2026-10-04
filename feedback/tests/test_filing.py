from datetime import timedelta

import pytest

from feedback.domain.filing import FeedbackError, file_feedback, record_change
from feedback.domain.status import changes_for, item_status
from feedback.models.commands import AddNote, NewItem
from feedback.models.feedback import FeedbackFile, Status, Verdict
from feedback.tests.conftest import NOW


def _with_item() -> FeedbackFile:
    feedback = FeedbackFile()
    file_feedback(feedback=feedback, command=NewItem(text="too sarcastic"), context="Nova: ugh", now=NOW)
    return feedback


def test_new_items_get_the_next_id() -> None:
    feedback = _with_item()
    assert file_feedback(feedback=feedback, command=NewItem(text="too long"), context="", now=NOW) == 2
    assert [item.id for item in feedback.items] == [1, 2]
    assert feedback.items[0].context == "Nova: ugh"


def test_a_note_lands_on_its_item() -> None:
    feedback = _with_item()
    assert file_feedback(feedback=feedback, command=AddNote(item_id=1, text="still"), context="ctx", now=NOW) == 1
    assert [(note.text, note.context) for note in feedback.items[0].notes] == [("still", "ctx")]


def test_a_note_for_an_unknown_item_becomes_a_new_item() -> None:
    feedback = _with_item()
    assert file_feedback(feedback=feedback, command=AddNote(item_id=99, text="what about this"), context="", now=NOW) == 2
    assert feedback.items[1].text == "(about #99, which does not exist) what about this"


def test_status_follows_verdicts_and_reopenings() -> None:
    feedback = _with_item()
    item = feedback.items[0]
    assert item_status(item=item, changes=feedback.changes) is Status.OPEN
    record_change(feedback=feedback, summary="softer", files=["PERSONA.md"], resolved=[], partly=[1], now=NOW + timedelta(hours=1))
    assert item_status(item=item, changes=feedback.changes) is Status.PARTLY
    record_change(feedback=feedback, summary="softer still", files=["PERSONA.md"], resolved=[1], partly=[], now=NOW + timedelta(hours=2))
    assert item_status(item=item, changes=feedback.changes) is Status.RESOLVED
    file_feedback(feedback=feedback, command=AddNote(item_id=1, text="back again"), context="", now=NOW + timedelta(hours=3))
    assert item_status(item=item, changes=feedback.changes) is Status.OPEN
    assert [change.id for change in changes_for(item_id=1, changes=feedback.changes)] == [1, 2]


def test_record_change_validates_its_items() -> None:
    feedback = _with_item()
    with pytest.raises(FeedbackError, match="unknown items: 7"):
        record_change(feedback=feedback, summary="x", files=[], resolved=[7], partly=[], now=NOW)
    with pytest.raises(FeedbackError, match="both resolved and partly: 1"):
        record_change(feedback=feedback, summary="x", files=[], resolved=[1], partly=[1], now=NOW)
    with pytest.raises(FeedbackError, match="at least one item"):
        record_change(feedback=feedback, summary="x", files=[], resolved=[], partly=[], now=NOW)
    change = record_change(feedback=feedback, summary="x", files=["a"], resolved=[1], partly=[], now=NOW)
    assert (change.id, change.addresses) == (1, {1: Verdict.RESOLVED})
