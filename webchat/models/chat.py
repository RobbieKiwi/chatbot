"""What the page shows: logged messages, and the events a streamed turn is made of."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class LoggedMessage(BaseModel):
    """One message in the page's display copy of a conversation. The Claude Code transcript stays the record memory uses."""

    role: Role
    text: str
    at: datetime


class TextDelta(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class Working(BaseModel):
    """The assistant is running a tool. Which tool, and what it returned, never reach the page."""

    kind: Literal["working"] = "working"


class TurnDone(BaseModel):
    kind: Literal["done"] = "done"


class TurnError(BaseModel):
    kind: Literal["error"] = "error"
    message: str
    offer_new_conversation: bool = False


ChatEvent = Annotated[TextDelta | Working | TurnDone | TurnError, Field(discriminator="kind")]
CHAT_EVENT: TypeAdapter[ChatEvent] = TypeAdapter(ChatEvent)
