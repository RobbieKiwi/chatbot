import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from webchat.adapters.files import read_config, write_config
from webchat.domain.auth import new_passphrase_record
from webchat.entry.app import COOKIE_NAME, create_app
from webchat.entry.turns import TurnInProgress, TurnRunner
from webchat.models.chat import TextDelta, TurnDone, TurnError
from webchat.models.config import WebchatConfig
from webchat.models.paths import WebchatPaths
from webchat.tests.fakes import FakeDriver

PASSPHRASE = "correct horse"
ASSISTANT = "Iris <&> O'Neil"
ESCAPED = "Iris &lt;&amp;&gt; O&#x27;Neil"


@pytest.fixture
def driver(paths: WebchatPaths) -> FakeDriver:
    write_config(paths=paths, config=WebchatConfig(passphrase=new_passphrase_record(passphrase=PASSPHRASE)))
    return FakeDriver(paths=paths, opening=[TextDelta(text="Hello Alex."), TurnDone()], replies=[])


@pytest.fixture
def client(paths: WebchatPaths, driver: FakeDriver) -> Iterator[TestClient]:
    app = create_app(paths=paths, turns=TurnRunner(driver=driver, paths=paths), assistant_name=ASSISTANT, failed_login_delay_s=0)
    with TestClient(app) as test_client:
        yield test_client


def log_in(client: TestClient) -> None:
    assert client.post("/login", json={"passphrase": PASSPHRASE}).status_code == 204


def events_of(text: str) -> list[dict]:
    return [json.loads(chunk.removeprefix("data: ")) for chunk in text.split("\n\n") if chunk.startswith("data: ")]


def test_root_serves_the_login_page_until_logged_in(client: TestClient) -> None:
    assert 'id="login"' in client.get("/").text
    log_in(client)
    assert 'id="messages"' in client.get("/").text


def test_wrong_passphrase_is_401_and_sets_no_cookie(client: TestClient) -> None:
    response = client.post("/login", json={"passphrase": "nope"})
    assert response.status_code == 401
    assert COOKIE_NAME not in response.cookies


def test_login_cookie_is_httponly_and_strict(client: TestClient) -> None:
    header = client.post("/login", json={"passphrase": PASSPHRASE}).headers["set-cookie"].lower()
    assert "httponly" in header
    assert "samesite=strict" in header
    assert "max-age=31536000" in header


@pytest.mark.parametrize(("method", "url"), [("GET", "/api/conversation"), ("POST", "/api/conversation"), ("POST", "/api/turn")])
def test_api_needs_the_cookie(client: TestClient, method: str, url: str) -> None:
    assert client.request(method, url, json={"text": "Hi"}).status_code == 401


def test_tampered_cookie_is_refused(client: TestClient) -> None:
    client.cookies.set(COOKIE_NAME, "1.deadbeef")
    assert client.get("/api/conversation").status_code == 401


def test_cookie_stops_working_after_passphrase_change(client: TestClient, paths: WebchatPaths) -> None:
    log_in(client)
    write_config(paths=paths, config=read_config(paths=paths).model_copy(update={"passphrase": new_passphrase_record(passphrase=PASSPHRASE)}))
    assert client.get("/api/conversation").status_code == 401


def test_no_conversation_yet_is_an_empty_history(client: TestClient) -> None:
    log_in(client)
    assert client.get("/api/conversation").json() == []


def test_new_conversation_streams_the_opening_and_logs_it(client: TestClient) -> None:
    log_in(client)
    response = client.post("/api/conversation")
    assert response.headers["content-type"].startswith("text/event-stream")
    assert events_of(response.text) == [{"kind": "text", "text": "Hello Alex."}, {"kind": "done"}]
    assert [(m["role"], m["text"]) for m in client.get("/api/conversation").json()] == [("assistant", "Hello Alex.")]


def test_turn_streams_the_reply_and_logs_both_sides(client: TestClient, driver: FakeDriver) -> None:
    log_in(client)
    client.post("/api/conversation")
    driver.replies.append([TextDelta(text="Sure."), TurnDone()])
    assert events_of(client.post("/api/turn", json={"text": "Hi"}).text) == [{"kind": "text", "text": "Sure."}, {"kind": "done"}]
    assert [(m["role"], m["text"]) for m in client.get("/api/conversation").json()][1:] == [("user", "Hi"), ("assistant", "Sure.")]


def test_failed_turn_streams_the_error_and_logs_nothing(client: TestClient, driver: FakeDriver) -> None:
    log_in(client)
    client.post("/api/conversation")
    driver.replies.append([TurnError(message="boom")])
    assert events_of(client.post("/api/turn", json={"text": "Hi"}).text) == [{"kind": "error", "message": "boom", "offer_new_conversation": False}]
    assert len(client.get("/api/conversation").json()) == 1


def test_empty_message_is_rejected(client: TestClient) -> None:
    log_in(client)
    assert client.post("/api/turn", json={"text": ""}).status_code == 422


class BusyTurns(TurnRunner):
    def begin_turn(self, *, text: str):
        raise TurnInProgress


def test_turn_while_busy_is_409(paths: WebchatPaths, driver: FakeDriver) -> None:
    app = create_app(paths=paths, turns=BusyTurns(driver=driver, paths=paths), assistant_name=ASSISTANT, failed_login_delay_s=0)
    with TestClient(app) as client:
        log_in(client)
        response = client.post("/api/turn", json={"text": "Hi"})
        assert response.status_code == 409 and response.json()["detail"] == f"{ASSISTANT} is still replying"


def test_the_pages_carry_the_assistant_name(client: TestClient) -> None:
    for page in (client.get("/").text, (log_in(client), client.get("/").text)[1]):
        assert f"<title>{ESCAPED}</title>" in page and f"<h1>{ESCAPED}</h1>" in page
        assert "__ASSISTANT__" not in page


def test_shutdown_closes_the_driver(paths: WebchatPaths, driver: FakeDriver) -> None:
    with TestClient(create_app(paths=paths, turns=TurnRunner(driver=driver, paths=paths), assistant_name=ASSISTANT)):
        pass
    assert driver.closed
