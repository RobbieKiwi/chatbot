"""webchat's files: config, the current conversation, and each conversation's display log."""

import os
from pathlib import Path

from pydantic import BaseModel

from webchat.models.chat import LoggedMessage
from webchat.models.config import WebchatConfig
from webchat.models.paths import WebchatPaths
from webchat.models.state import WebchatState

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent


def webchat_paths() -> WebchatPaths:
    root = Path(os.environ.get("WEBCHAT_DATA_ROOT", PACKAGE_ROOT / "data"))
    return WebchatPaths(root=root, config=root / "config.json", state=root / "state.json", conversations=root / "conversations", logs=root / "logs")


def _write_model(*, path: Path, value: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(value.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporary, path)


def read_config(*, paths: WebchatPaths) -> WebchatConfig:
    if not paths.config.exists():
        return WebchatConfig()
    return WebchatConfig.model_validate_json(paths.config.read_text(encoding="utf-8"))


def write_config(*, paths: WebchatPaths, config: WebchatConfig) -> None:
    _write_model(path=paths.config, value=config)


def read_state(*, paths: WebchatPaths) -> WebchatState | None:
    if not paths.state.exists():
        return None
    return WebchatState.model_validate_json(paths.state.read_text(encoding="utf-8"))


def write_state(*, paths: WebchatPaths, state: WebchatState) -> None:
    _write_model(path=paths.state, value=state)


def _log_path(*, paths: WebchatPaths, session_id: str) -> Path:
    return paths.conversations / f"{session_id}.jsonl"


def append_messages(*, paths: WebchatPaths, session_id: str, messages: list[LoggedMessage]) -> None:
    path = _log_path(paths=paths, session_id=session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log:
        log.writelines(f"{message.model_dump_json()}\n" for message in messages)


def read_messages(*, paths: WebchatPaths, session_id: str) -> list[LoggedMessage]:
    path = _log_path(paths=paths, session_id=session_id)
    if not path.exists():
        return []
    return [LoggedMessage.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
