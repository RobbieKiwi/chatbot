"""The feedback file: validated on every load, edited under a lock."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from feedback.adapters.files import file_lock, write_model
from feedback.models.feedback import FeedbackFile


def load_feedback(*, path: Path) -> FeedbackFile:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return FeedbackFile()
    return FeedbackFile.model_validate_json(text)


@contextmanager
def editing_feedback(*, path: Path) -> Iterator[FeedbackFile]:
    with file_lock(path=path):
        feedback = load_feedback(path=path)
        yield feedback
        write_model(path=path, value=feedback)
