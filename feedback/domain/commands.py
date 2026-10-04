"""Reading a message as a `fb:` command."""

import re

from feedback.models.commands import AddNote, EmptyFeedback, FeedbackCommand, NewItem

_FEEDBACK = re.compile(r"fb:(?:\s*#(\d+)(?=\s|$))?(.*)", re.DOTALL | re.IGNORECASE)


def parse_feedback(*, prompt: str) -> FeedbackCommand | None:
    match = _FEEDBACK.fullmatch(prompt.strip())
    if match is None:
        return None
    item_id, text = match.group(1), match.group(2).strip()
    if not text:
        return EmptyFeedback()
    return NewItem(text=text) if item_id is None else AddNote(item_id=int(item_id), text=text)
