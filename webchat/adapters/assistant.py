"""
The assistant as a headless Claude Code session running /chatbot, driven through the Claude Agent SDK.

An SDK client must be connected, used and disconnected from one task, so a single worker task owns it for its whole
life and requests reach that task through a queue.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage

from webchat.adapters.files import read_state, write_state
from webchat.domain.translate import ReplyTranslator
from webchat.models.chat import ChatEvent, TurnDone, TurnError
from webchat.models.paths import WebchatPaths
from webchat.models.state import WebchatState

OPENING_PROMPT = "/chatbot"
RESUME_FAILED = "Couldn't pick up the last conversation. Start a new one."
NO_CONVERSATION = "There's no conversation yet. Start one."

log = logging.getLogger(__name__)


class SdkClient(Protocol):
    async def connect(self) -> None: ...

    async def query(self, prompt: str) -> None: ...

    def receive_response(self) -> AsyncIterator[object]: ...

    async def disconnect(self) -> None: ...


class ClientFactory(Protocol):
    def __call__(self, *, options: ClaudeAgentOptions) -> SdkClient: ...


def assistant_options(*, project_root: Path, resume: str | None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        cwd=project_root,
        setting_sources=["project"],  # the chatbot hooks, allow-list, skill and librarian; not the user's own coding settings
        permission_mode="dontAsk",
        include_partial_messages=True,
        resume=resume,
        stderr=lambda line: log.info("claude: %s", line),
    )


@dataclass
class _Request:
    prompt: str
    new_conversation: bool
    events: asyncio.Queue[ChatEvent | None] = field(default_factory=asyncio.Queue)  # None ends the turn


class AssistantDriver:
    def __init__(
        self,
        *,
        paths: WebchatPaths,
        project_root: Path,
        assistant_name: str,
        client_factory: ClientFactory = ClaudeSDKClient,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._paths = paths
        self._project_root = project_root
        self._lost_connection = f"Lost the connection to {assistant_name}. Try again."
        self._client_factory = client_factory
        self._clock = clock
        self._inbox: asyncio.Queue[_Request | None] = asyncio.Queue()  # None stops the worker
        self._worker: asyncio.Task[None] | None = None
        self._client: SdkClient | None = None
        self._fresh_resume = False  # the live client was resumed and has not completed a turn yet

    def start_conversation(self) -> AsyncIterator[ChatEvent]:
        return self._submit(request=_Request(prompt=OPENING_PROMPT, new_conversation=True))

    def send(self, *, text: str) -> AsyncIterator[ChatEvent]:
        return self._submit(request=_Request(prompt=text, new_conversation=False))

    async def close(self) -> None:
        if self._worker is not None and not self._worker.done():
            await self._inbox.put(None)
            await self._worker

    async def _submit(self, *, request: _Request) -> AsyncIterator[ChatEvent]:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._work())
        await self._inbox.put(request)
        while (event := await request.events.get()) is not None:
            yield event

    async def _work(self) -> None:
        while (request := await self._inbox.get()) is not None:
            await self._serve(request=request)
        await self._drop_client()

    async def _serve(self, *, request: _Request) -> None:
        emit = request.events.put_nowait
        try:
            if request.new_conversation:
                await self._drop_client()
                await self._connect(resume=None)
            elif self._client is None:
                state = read_state(paths=self._paths)
                if state is None:
                    emit(TurnError(message=NO_CONVERSATION, offer_new_conversation=True))
                    return
                await self._connect(resume=state.session_id)
            await self._stream(request=request)
        except Exception:
            log.exception("assistant turn failed")
            await self._drop_client()
            emit(TurnError(message=self._lost_connection))
        finally:
            emit(None)

    async def _stream(self, *, request: _Request) -> None:
        assert self._client is not None
        translator = ReplyTranslator()
        resume_failed = False
        await self._client.query(prompt=request.prompt)
        async for message in self._client.receive_response():
            if isinstance(message, ResultMessage):
                self._record_result(result=message, new_conversation=request.new_conversation)
            for event in translator.translate(message=message):
                if isinstance(event, TurnError) and self._fresh_resume:
                    resume_failed = True
                    event = TurnError(message=f"{RESUME_FAILED} ({event.message})", offer_new_conversation=True)
                elif isinstance(event, TurnDone):
                    self._fresh_resume = False
                request.events.put_nowait(event)
        if resume_failed:
            await self._drop_client()

    def _record_result(self, *, result: ResultMessage, new_conversation: bool) -> None:
        if result.permission_denials:
            log.warning("denied tool calls: %s", result.permission_denials)
        if new_conversation:
            write_state(paths=self._paths, state=WebchatState(session_id=result.session_id, started_at=self._clock()))
            return
        state = read_state(paths=self._paths)
        if state is not None and state.session_id != result.session_id:
            log.warning("session %s continued as %s", state.session_id, result.session_id)
            write_state(paths=self._paths, state=state.model_copy(update={"session_id": result.session_id}))

    async def _connect(self, *, resume: str | None) -> None:
        client = self._client_factory(options=assistant_options(project_root=self._project_root, resume=resume))
        await client.connect()
        self._client = client
        self._fresh_resume = resume is not None

    async def _drop_client(self) -> None:
        client, self._client = self._client, None
        if client is None:
            return
        try:
            await client.disconnect()
        except Exception:
            log.exception("disconnecting the assistant client failed")
