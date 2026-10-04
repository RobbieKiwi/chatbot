"""The chat server: the passphrase gate, the page, and the assistant's turns streamed as Server-Sent Events."""

import asyncio
import html
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from webchat.adapters.files import read_config, read_messages, read_state
from webchat.domain.auth import COOKIE_LIFETIME, cookie_valid, passphrase_matches, sign_cookie
from webchat.entry.turns import TurnInProgress, TurnRunner
from webchat.models.chat import CHAT_EVENT, ChatEvent, LoggedMessage
from webchat.models.paths import WebchatPaths

COOKIE_NAME = "chat_login"
STATIC = Path(__file__).parent / "static"
NAME_SLOT = "__ASSISTANT__"  # where the pages take the assistant's name


class LoginRequest(BaseModel):
    passphrase: str


class TurnRequest(BaseModel):
    text: str = Field(min_length=1)


def _now() -> datetime:
    return datetime.now(UTC)


def create_app(*, paths: WebchatPaths, turns: TurnRunner, assistant_name: str, failed_login_delay_s: float = 1.0) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await turns.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    def logged_in(request: Request) -> bool:
        record = read_config(paths=paths).passphrase
        return record is not None and cookie_valid(record=record, cookie=request.cookies.get(COOKIE_NAME), now=_now())

    def require_login(request: Request) -> None:
        if not logged_in(request=request):
            raise HTTPException(status_code=401)

    def stream(*, begin: Callable[[], asyncio.Queue[ChatEvent | None]]) -> StreamingResponse:
        try:
            events = begin()
        except TurnInProgress:
            raise HTTPException(status_code=409, detail=f"{assistant_name} is still replying") from None

        async def body() -> AsyncIterator[str]:
            while (event := await events.get()) is not None:
                yield f"data: {CHAT_EVENT.dump_json(event).decode('utf-8')}\n\n"

        return StreamingResponse(content=body(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})

    @app.get("/")
    async def page(request: Request) -> HTMLResponse:
        page = (STATIC / ("index.html" if logged_in(request=request) else "login.html")).read_text(encoding="utf-8")
        return HTMLResponse(content=page.replace(NAME_SLOT, html.escape(assistant_name)))

    @app.post("/login", status_code=204)
    async def login(body: LoginRequest, response: Response) -> None:
        record = read_config(paths=paths).passphrase
        if record is None or not passphrase_matches(record=record, passphrase=body.passphrase):
            await asyncio.sleep(failed_login_delay_s)
            raise HTTPException(status_code=401)
        response.set_cookie(
            key=COOKIE_NAME,
            value=sign_cookie(record=record, now=_now()),
            max_age=int(COOKIE_LIFETIME.total_seconds()),
            httponly=True,
            samesite="strict",
        )

    @app.get("/api/conversation", dependencies=[Depends(require_login)])
    async def conversation() -> list[LoggedMessage]:
        state = read_state(paths=paths)
        return [] if state is None else read_messages(paths=paths, session_id=state.session_id)

    # Turns begin inside async handlers: TurnRunner starts a task on the running event loop.
    @app.post("/api/conversation", dependencies=[Depends(require_login)])
    async def new_conversation() -> StreamingResponse:
        return stream(begin=turns.begin_conversation)

    @app.post("/api/turn", dependencies=[Depends(require_login)])
    async def turn(body: TurnRequest) -> StreamingResponse:
        return stream(begin=lambda: turns.begin_turn(text=body.text))

    return app
