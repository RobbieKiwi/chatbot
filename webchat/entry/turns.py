"""
Runs one assistant turn at a time, each in its own task, so a turn finishes and is logged even when the page that
asked for it has gone away.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

from webchat.adapters.files import append_messages, read_state
from webchat.models.chat import ChatEvent, LoggedMessage, Role, TextDelta, TurnDone, TurnError
from webchat.models.driver import ConversationDriver
from webchat.models.paths import WebchatPaths

TURN_FAILED = "Something went wrong. Try again."

log = logging.getLogger(__name__)


class TurnInProgress(Exception):
    pass


class TurnRunner:
    def __init__(self, *, driver: ConversationDriver, paths: WebchatPaths, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._driver = driver
        self._paths = paths
        self._clock = clock
        self._task: asyncio.Task[None] | None = None

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def begin_conversation(self) -> asyncio.Queue[ChatEvent | None]:
        return self._begin(open_events=self._driver.start_conversation, user_text=None)

    def begin_turn(self, *, text: str) -> asyncio.Queue[ChatEvent | None]:
        return self._begin(open_events=lambda: self._driver.send(text=text), user_text=text)

    async def finished(self) -> None:
        if self._task is not None:
            await self._task

    async def close(self) -> None:
        await self.finished()
        await self._driver.close()

    def _begin(self, *, open_events: Callable[[], AsyncIterator[ChatEvent]], user_text: str | None) -> asyncio.Queue[ChatEvent | None]:
        if self.busy:
            raise TurnInProgress
        out: asyncio.Queue[ChatEvent | None] = asyncio.Queue()  # None ends the turn
        self._task = asyncio.create_task(self._run(events=open_events(), user_text=user_text, out=out))
        return out

    async def _run(self, *, events: AsyncIterator[ChatEvent], user_text: str | None, out: asyncio.Queue[ChatEvent | None]) -> None:
        asked_at = self._clock()
        reply: list[str] = []
        try:
            async for event in events:
                if isinstance(event, TextDelta):
                    reply.append(event.text)
                elif isinstance(event, TurnDone):
                    self._log(user_text=user_text, asked_at=asked_at, reply="".join(reply))
                out.put_nowait(event)
        except Exception:
            log.exception("turn failed")
            out.put_nowait(TurnError(message=TURN_FAILED))
        finally:
            out.put_nowait(None)

    def _log(self, *, user_text: str | None, asked_at: datetime, reply: str) -> None:
        state = read_state(paths=self._paths)
        if state is None:
            return
        asked = [LoggedMessage(role=Role.USER, text=user_text, at=asked_at)] if user_text is not None else []
        append_messages(paths=self._paths, session_id=state.session_id, messages=[*asked, LoggedMessage(role=Role.ASSISTANT, text=reply, at=self._clock())])
