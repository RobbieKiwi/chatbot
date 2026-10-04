from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from claude_agent_sdk import ClaudeAgentOptions

from webchat.adapters.assistant import NO_CONVERSATION, OPENING_PROMPT, RESUME_FAILED, AssistantDriver
from webchat.adapters.files import read_state, write_state
from webchat.models.chat import ChatEvent, TextDelta, TurnDone, TurnError
from webchat.models.paths import WebchatPaths
from webchat.models.state import WebchatState
from webchat.tests.sdk_messages import result, text_delta

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
PROJECT = Path("C:/project")


class FakeClient:
    """Replays one scripted reply per query; an exception in a reply is raised mid-stream."""

    def __init__(self, *, options: ClaudeAgentOptions, replies: list[list[object]]) -> None:
        self.options = options
        self.replies = replies
        self.prompts: list[str] = []
        self.disconnected = False

    async def connect(self) -> None:
        pass

    async def query(self, prompt: str) -> None:
        self.prompts.append(prompt)

    async def receive_response(self) -> AsyncIterator[object]:
        for message in self.replies.pop(0):
            if isinstance(message, Exception):
                raise message
            yield message

    async def disconnect(self) -> None:
        self.disconnected = True


class Clients:
    """A client factory that hands out FakeClients sharing one script, and remembers them."""

    def __init__(self, *, replies: list[list[object]]) -> None:
        self.replies = replies
        self.made: list[FakeClient] = []

    def __call__(self, *, options: ClaudeAgentOptions) -> FakeClient:
        client = FakeClient(options=options, replies=self.replies)
        self.made.append(client)
        return client


def driver_with(*, paths: WebchatPaths, clients: Clients) -> AssistantDriver:
    return AssistantDriver(paths=paths, project_root=PROJECT, assistant_name="Nova", client_factory=clients, clock=lambda: NOW)


async def collect(events: AsyncIterator[ChatEvent]) -> list[ChatEvent]:
    return [event async for event in events]


@pytest.mark.anyio
async def test_start_opens_chatbot_and_saves_the_session(paths: WebchatPaths) -> None:
    clients = Clients(replies=[[text_delta(text="Hello Alex."), result(session_id="s1")]])
    driver = driver_with(paths=paths, clients=clients)
    assert await collect(driver.start_conversation()) == [TextDelta(text="Hello Alex."), TurnDone()]
    await driver.close()
    (client,) = clients.made
    assert client.prompts == [OPENING_PROMPT]
    assert client.options.resume is None
    assert client.options.setting_sources == ["project"]
    assert client.options.permission_mode == "dontAsk"
    assert client.options.include_partial_messages is True
    assert client.options.cwd == PROJECT
    assert read_state(paths=paths) == WebchatState(session_id="s1", started_at=NOW)


@pytest.mark.anyio
async def test_send_reuses_the_live_client(paths: WebchatPaths) -> None:
    clients = Clients(replies=[[result()], [text_delta(text="Sure."), result()]])
    driver = driver_with(paths=paths, clients=clients)
    await collect(driver.start_conversation())
    assert await collect(driver.send(text="Hi")) == [TextDelta(text="Sure."), TurnDone()]
    await driver.close()
    assert len(clients.made) == 1
    assert clients.made[0].prompts == [OPENING_PROMPT, "Hi"]


@pytest.mark.anyio
async def test_send_without_a_conversation_offers_a_new_one(paths: WebchatPaths) -> None:
    clients = Clients(replies=[])
    driver = driver_with(paths=paths, clients=clients)
    assert await collect(driver.send(text="Hi")) == [TurnError(message=NO_CONVERSATION, offer_new_conversation=True)]
    await driver.close()
    assert clients.made == []


@pytest.mark.anyio
async def test_send_after_restart_resumes_saved_session(paths: WebchatPaths) -> None:
    write_state(paths=paths, state=WebchatState(session_id="s0", started_at=NOW))
    clients = Clients(replies=[[text_delta(text="Where were we?", session_id="s0"), result(session_id="s0")]])
    driver = driver_with(paths=paths, clients=clients)
    assert await collect(driver.send(text="Back")) == [TextDelta(text="Where were we?"), TurnDone()]
    await driver.close()
    assert clients.made[0].options.resume == "s0"


@pytest.mark.anyio
async def test_changed_session_id_after_resume_updates_state(paths: WebchatPaths) -> None:
    write_state(paths=paths, state=WebchatState(session_id="s0", started_at=NOW))
    driver = driver_with(paths=paths, clients=Clients(replies=[[result(session_id="s9")]]))
    await collect(driver.send(text="Back"))
    await driver.close()
    assert read_state(paths=paths) == WebchatState(session_id="s9", started_at=NOW)


@pytest.mark.anyio
async def test_failed_first_turn_after_resume_offers_a_new_conversation(paths: WebchatPaths) -> None:
    write_state(paths=paths, state=WebchatState(session_id="gone", started_at=NOW))
    clients = Clients(replies=[[result(session_id="gone", error="No conversation found")], [result(session_id="gone")]])
    driver = driver_with(paths=paths, clients=clients)
    assert await collect(driver.send(text="Back")) == [TurnError(message=f"{RESUME_FAILED} (No conversation found)", offer_new_conversation=True)]
    assert clients.made[0].disconnected
    await collect(driver.send(text="Again"))
    await driver.close()
    assert len(clients.made) == 2


@pytest.mark.anyio
async def test_crash_mid_turn_reports_and_reconnects_next_time(paths: WebchatPaths) -> None:
    clients = Clients(replies=[[result()], [text_delta(text="Hm"), RuntimeError("process died")], [result()]])
    driver = driver_with(paths=paths, clients=clients)
    await collect(driver.start_conversation())
    assert await collect(driver.send(text="Hi")) == [TextDelta(text="Hm"), TurnError(message="Lost the connection to Nova. Try again.")]
    assert clients.made[0].disconnected
    await collect(driver.send(text="Hi again"))
    await driver.close()
    assert clients.made[1].options.resume == "s1"


@pytest.mark.anyio
async def test_error_result_mid_conversation_keeps_the_client(paths: WebchatPaths) -> None:
    clients = Clients(replies=[[result()], [result(error="Usage limit reached")]])
    driver = driver_with(paths=paths, clients=clients)
    await collect(driver.start_conversation())
    assert await collect(driver.send(text="Hi")) == [TurnError(message="Usage limit reached")]
    await driver.close()
    assert len(clients.made) == 1


@pytest.mark.anyio
async def test_starting_again_replaces_the_client(paths: WebchatPaths) -> None:
    clients = Clients(replies=[[result(session_id="s1")], [result(session_id="s2")]])
    driver = driver_with(paths=paths, clients=clients)
    await collect(driver.start_conversation())
    await collect(driver.start_conversation())
    await driver.close()
    assert clients.made[0].disconnected
    assert clients.made[1].options.resume is None
    assert read_state(paths=paths) == WebchatState(session_id="s2", started_at=NOW)


@pytest.mark.anyio
async def test_close_disconnects_the_live_client(paths: WebchatPaths) -> None:
    clients = Clients(replies=[[result()]])
    driver = driver_with(paths=paths, clients=clients)
    await collect(driver.start_conversation())
    await driver.close()
    assert clients.made[0].disconnected
