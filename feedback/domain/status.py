"""An item's status, derived from the changes that addressed it and the notes added since."""

from feedback.models.feedback import Change, Item, Status


def changes_for(*, item_id: int, changes: list[Change]) -> list[Change]:
    return sorted((change for change in changes if item_id in change.addresses), key=lambda change: change.made_at)


def item_status(*, item: Item, changes: list[Change]) -> Status:
    addressed = changes_for(item_id=item.id, changes=changes)
    if not addressed:
        return Status.OPEN
    latest = addressed[-1]
    if any(note.at > latest.made_at for note in item.notes):
        return Status.OPEN
    return Status(latest.addresses[item.id].value)
