"""Filing feedback items and the changes that answer them."""

from datetime import datetime

from feedback.models.commands import AddNote, NewItem
from feedback.models.feedback import Change, FeedbackFile, Item, Note, Verdict


class FeedbackError(ValueError):
    """A request the feedback file cannot take: exit 2 with a message to act on."""


def file_feedback(*, feedback: FeedbackFile, command: NewItem | AddNote, context: str, now: datetime) -> int:
    """Add the command to the file in place; the id of the item it landed on."""
    text = command.text
    if isinstance(command, AddNote):
        item = next((item for item in feedback.items if item.id == command.item_id), None)
        if item is not None:
            item.notes.append(Note(at=now, text=command.text, context=context))
            return item.id
        text = f"(about #{command.item_id}, which does not exist) {command.text}"
    new_id = max((item.id for item in feedback.items), default=0) + 1
    feedback.items.append(Item(id=new_id, created_at=now, text=text, context=context))
    return new_id


def record_change(*, feedback: FeedbackFile, summary: str, files: list[str], resolved: list[int], partly: list[int], now: datetime) -> Change:
    if not resolved and not partly:
        raise FeedbackError("a change addresses at least one item: pass --resolved or --partly")
    unknown = sorted(set(resolved + partly) - {item.id for item in feedback.items})
    if unknown:
        raise FeedbackError(f"unknown items: {', '.join(map(str, unknown))}")
    both = sorted(set(resolved) & set(partly))
    if both:
        raise FeedbackError(f"both resolved and partly: {', '.join(map(str, both))}")
    addresses = {item_id: Verdict.RESOLVED for item_id in resolved} | {item_id: Verdict.PARTLY for item_id in partly}
    change = Change(id=max((change.id for change in feedback.changes), default=0) + 1, made_at=now, summary=summary, files=files, addresses=addresses)
    feedback.changes.append(change)
    return change
