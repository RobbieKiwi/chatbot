"""JSON state files: config, the session registry, conversations and worker health."""

import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel

from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import ConversationState, SessionRegistry
from memorylayers.models.paths import ParentPaths
from memorylayers.models.worker import WorkerHealth


def read_model[M: BaseModel](*, path: Path, model: type[M]) -> M | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return model.model_validate_json(text)


def write_model(*, path: Path, value: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    temporary.write_text(value.model_dump_json(indent=2), encoding="utf-8")
    for _ in range(50):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:  # Windows: another process has the file open for a moment
            time.sleep(0.01)
    os.replace(temporary, path)


@contextmanager
def file_lock(*, path: Path, timeout_s: float = 5.0) -> Iterator[None]:
    """A cross-process lock: a sidecar file created exclusively. A holder that died is broken after the timeout."""
    lock = path.with_name(f"{path.name}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except (FileExistsError, PermissionError):  # Windows reports a lock file mid-delete as PermissionError
            if time.monotonic() > deadline:
                lock.unlink(missing_ok=True)
                deadline = time.monotonic() + timeout_s
            time.sleep(0.002)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def load_config(*, paths: ParentPaths) -> MemoryConfig:
    return read_model(path=paths.config, model=MemoryConfig) or MemoryConfig()


def load_registry(*, paths: ParentPaths) -> SessionRegistry:
    return read_model(path=paths.registry, model=SessionRegistry) or SessionRegistry()


def update_registry(*, paths: ParentPaths, change: Callable[[SessionRegistry], None]) -> SessionRegistry:
    with file_lock(path=paths.registry):
        registry = load_registry(paths=paths)
        change(registry)
        write_model(path=paths.registry, value=registry)
    return registry


def _conversation_path(*, paths: ParentPaths, conversation_id: str) -> Path:
    return paths.conversations / f"{conversation_id}.json"


def load_conversation(*, paths: ParentPaths, conversation_id: str) -> ConversationState:
    state = read_model(path=_conversation_path(paths=paths, conversation_id=conversation_id), model=ConversationState)
    if state is None:
        raise KeyError(f"no conversation {conversation_id!r}")
    return state


def save_conversation(*, paths: ParentPaths, state: ConversationState) -> None:
    path = _conversation_path(paths=paths, conversation_id=state.id)
    with file_lock(path=path):
        write_model(path=path, value=state)


def update_conversation(*, paths: ParentPaths, conversation_id: str, change: Callable[[ConversationState], None]) -> ConversationState:
    path = _conversation_path(paths=paths, conversation_id=conversation_id)
    with file_lock(path=path):
        state = load_conversation(paths=paths, conversation_id=conversation_id)
        change(state)
        write_model(path=path, value=state)
    return state


def list_conversations(*, paths: ParentPaths) -> list[ConversationState]:
    if not paths.conversations.exists():
        return []
    states = [read_model(path=path, model=ConversationState) for path in paths.conversations.glob("*.json")]
    return sorted((state for state in states if state is not None), key=lambda state: state.last_activity)


def load_summariser_health(*, paths: ParentPaths) -> WorkerHealth:
    return read_model(path=paths.summariser_health, model=WorkerHealth) or WorkerHealth()


def update_summariser_health(*, paths: ParentPaths, change: Callable[[WorkerHealth], None]) -> WorkerHealth:
    with file_lock(path=paths.summariser_health):
        health = load_summariser_health(paths=paths)
        change(health)
        write_model(path=paths.summariser_health, value=health)
    return health
