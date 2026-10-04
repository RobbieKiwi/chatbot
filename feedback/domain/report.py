"""Feedback and changes as the review reads them."""

from feedback.domain.status import changes_for, item_status
from feedback.models.feedback import Change, FeedbackFile, Item, Status


def _indent(*, text: str) -> str:
    return "\n".join(f"    {line}" for line in text.splitlines())


def format_item(*, item: Item, changes: list[Change], with_context: bool) -> str:
    lines = [f"#{item.id} [{item_status(item=item, changes=changes)}] {item.created_at:%Y-%m-%d} {item.text}"]
    if with_context and item.context:
        lines += ["  context:", _indent(text=item.context)]
    for note in item.notes:
        lines.append(f"  note {note.at:%Y-%m-%d}: {note.text}")
        if with_context and note.context:
            lines += ["  context:", _indent(text=note.context)]
    lines += [f"  change #{change.id} ({change.addresses[item.id]}) {change.made_at:%Y-%m-%d}: {change.summary}" for change in changes_for(item_id=item.id, changes=changes)]
    return "\n".join(lines)


def format_open(*, feedback: FeedbackFile) -> str:
    unresolved = [item for item in feedback.items if item_status(item=item, changes=feedback.changes) is not Status.RESOLVED]
    if not unresolved:
        return "No open feedback."
    return "\n\n".join(format_item(item=item, changes=feedback.changes, with_context=False) for item in unresolved)


def format_history(*, changes: list[Change]) -> str:
    if not changes:
        return "No changes recorded."
    lines = []
    for change in sorted(changes, key=lambda change: change.made_at, reverse=True):
        verdicts = ", ".join(f"{verdict} #{item_id}" for item_id, verdict in sorted(change.addresses.items()))
        lines.append(f"#{change.id} {change.made_at:%Y-%m-%d} {change.summary} — {', '.join(change.files) or 'no files'} — {verdicts}")
    return "\n".join(lines)
