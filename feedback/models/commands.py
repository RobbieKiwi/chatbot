"""What a `fb:` message asks for."""

from pydantic import BaseModel


class NewItem(BaseModel):
    text: str


class AddNote(BaseModel):
    item_id: int
    text: str


class EmptyFeedback(BaseModel):
    """`fb:` with nothing to say."""


FeedbackCommand = NewItem | AddNote | EmptyFeedback
