"""The interface to the assistant that the server runs turns through."""

from collections.abc import AsyncIterator
from typing import Protocol

from webchat.models.chat import ChatEvent


class ConversationDriver(Protocol):
    def start_conversation(self) -> AsyncIterator[ChatEvent]: ...

    def send(self, *, text: str) -> AsyncIterator[ChatEvent]: ...

    async def close(self) -> None: ...
