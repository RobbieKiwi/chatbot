import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest

from webchat.adapters.files import read_messages
from webchat.entry.turns import TURN_FAILED, TurnInProgress, TurnRunner
from webchat.models.chat import ChatEvent, LoggedMessage, Role, TextDelta, TurnDone, TurnError, Working
from webchat.models.paths import WebchatPaths
from webchat.tests.fakes import FakeDriver

NOW = datetime(2026, 10, 4, 13, 0, tzinfo=UTC)


async def drain(events: asyncio.Queue[ChatEvent | None]) -> list[ChatEvent]:
    collected = []
    while (event := await events.get()) is not None:
        collected.append(event)
    return collected


def runner_for(*, driver: FakeDriver, paths: WebchatPaths) -> TurnRunner:
    return TurnRunner(driver=driver, paths=paths, clock=lambda: NOW)


@pytest.mark.anyio
async def test_opening_is_streamed_and_logged_as_assistant_only(paths: WebchatPaths) -> None:
    driver = FakeDriver(paths=paths, opening=[TextDelta(text="Hello "), TextDelta(text="Alex."), TurnDone()], replies=[])
    runner = runner_for(driver=driver, paths=paths)
    assert await drain(runner.begin_conversation()) == [TextDelta(text="Hello "), TextDelta(text="Alex."), TurnDone()]
    assert read_messages(paths=paths, session_id="s1") == [LoggedMessage(role=Role.ASSISTANT, text="Hello Alex.", at=NOW)]


@pytest.mark.anyio
async def test_turn_logs_the_message_and_the_reply(paths: WebchatPaths) -> None:
    driver = FakeDriver(paths=paths, opening=[TurnDone()], replies=[[Working(), TextDelta(text="Sure."), TurnDone()]])
    runner = runner_for(driver=driver, paths=paths)
    await drain(runner.begin_conversation())
    await drain(runner.begin_turn(text="Hi"))
    assert read_messages(paths=paths, session_id="s1")[1:] == [
        LoggedMessage(role=Role.USER, text="Hi", at=NOW),
        LoggedMessage(role=Role.ASSISTANT, text="Sure.", at=NOW),
    ]


@pytest.mark.anyio
async def test_failed_turn_logs_nothing(paths: WebchatPaths) -> None:
    driver = FakeDriver(paths=paths, opening=[TurnDone()], replies=[[TextDelta(text="Hm"), TurnError(message="boom")]])
    runner = runner_for(driver=driver, paths=paths)
    await drain(runner.begin_conversation())
    await drain(runner.begin_turn(text="Hi"))
    assert len(read_messages(paths=paths, session_id="s1")) == 1


@pytest.mark.anyio
async def test_turn_finishes_and_logs_when_nobody_reads_it(paths: WebchatPaths) -> None:
    driver = FakeDriver(paths=paths, opening=[TurnDone()], replies=[[TextDelta(text="Still here."), TurnDone()]])
    runner = runner_for(driver=driver, paths=paths)
    await drain(runner.begin_conversation())
    runner.begin_turn(text="Hi")  # the page went away: nobody drains this queue
    await runner.finished()
    assert read_messages(paths=paths, session_id="s1")[-1].text == "Still here."


@pytest.mark.anyio
async def test_second_turn_while_busy_is_refused(paths: WebchatPaths) -> None:
    gate = asyncio.Event()
    driver = FakeDriver(paths=paths, opening=[TurnDone()], replies=[[TurnDone()]], gate=gate)
    runner = runner_for(driver=driver, paths=paths)
    await drain(runner.begin_conversation())
    first = runner.begin_turn(text="one")
    await asyncio.sleep(0)
    assert runner.busy
    with pytest.raises(TurnInProgress):
        runner.begin_turn(text="two")
    gate.set()
    assert await drain(first) == [TurnDone()]
    assert driver.sent == ["one"]
    assert not runner.busy


class BrokenDriver(FakeDriver):
    async def send(self, *, text: str) -> AsyncIterator[ChatEvent]:
        raise RuntimeError("driver bug")
        yield TurnDone()


@pytest.mark.anyio
async def test_driver_exception_ends_the_turn_with_an_error(paths: WebchatPaths) -> None:
    runner = runner_for(driver=BrokenDriver(paths=paths, opening=[], replies=[]), paths=paths)
    assert await drain(runner.begin_turn(text="Hi")) == [TurnError(message=TURN_FAILED)]
    assert not runner.busy


@pytest.mark.anyio
async def test_close_closes_the_driver(paths: WebchatPaths) -> None:
    driver = FakeDriver(paths=paths, opening=[], replies=[])
    await runner_for(driver=driver, paths=paths).close()
    assert driver.closed
