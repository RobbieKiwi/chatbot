"""A stand-in for the assistant that replays scripted chat events."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from webchat.adapters.files import write_state
from webchat.models.chat import ChatEvent
from webchat.models.paths import WebchatPaths
from webchat.models.state import WebchatState

STARTED = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


class FakeDriver:
    def __init__(self, *, paths: WebchatPaths, opening: list[ChatEvent], replies: list[list[ChatEvent]], gate: asyncio.Event | None = None) -> None:
        self.paths = paths
        self.opening = opening
        self.replies = replies
        self.gate = gate  # when set, each reply waits for it before its first event
        self.sent: list[str] = []
        self.starts = 0
        self.closed = False

    async def start_conversation(self) -> AsyncIterator[ChatEvent]:
        self.starts += 1
        write_state(paths=self.paths, state=WebchatState(session_id=f"s{self.starts}", started_at=STARTED))
        for event in self.opening:
            yield event

    async def send(self, *, text: str) -> AsyncIterator[ChatEvent]:
        self.sent.append(text)
        if self.gate is not None:
            await self.gate.wait()
        for event in self.replies.pop(0):
            yield event

    async def close(self) -> None:
        self.closed = True
