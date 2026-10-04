from pathlib import Path

import pytest
from pydantic import ValidationError

from feedback.adapters.paths import feedback_path
from feedback.adapters.store import editing_feedback, load_feedback
from feedback.domain.filing import file_feedback
from feedback.models.commands import NewItem
from feedback.models.feedback import FeedbackFile
from feedback.tests.conftest import NOW


def test_a_missing_file_is_empty(data_root: Path) -> None:
    assert load_feedback(path=feedback_path(parent="pk")) == FeedbackFile()


def test_edits_round_trip(data_root: Path) -> None:
    path = feedback_path(parent="pk")
    assert path == data_root / "pk.json"
    with editing_feedback(path=path) as feedback:
        file_feedback(feedback=feedback, command=NewItem(text="less puns"), context="", now=NOW)
    assert load_feedback(path=path).items[0].text == "less puns"


def test_an_invalid_file_fails_loudly(data_root: Path) -> None:
    path = feedback_path(parent="pk")
    path.parent.mkdir(parents=True)
    path.write_text('{"items": [{"id": "x"}]}', encoding="utf-8")
    with pytest.raises(ValidationError):
        load_feedback(path=path)
