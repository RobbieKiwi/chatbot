"""The persona folders on disk: `local/` when it exists, else `default/`."""

import json
import os
import shutil
import time
from pathlib import Path

from pydantic import ValidationError

from persona.models import PersonaError, PersonaNames

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
NAMES_FILE = "persona.json"
CHARACTER_FILE = "PERSONA.md"


def persona_root() -> Path:
    """The folder holding `default/` and `local/`; PERSONA_ROOT moves it for tests."""
    return Path(os.environ.get("PERSONA_ROOT", PACKAGE_ROOT))


def default_dir() -> Path:
    return persona_root() / "default"


def local_dir() -> Path:
    return persona_root() / "local"


def persona_dir() -> Path:
    return local_dir() if local_dir().exists() else default_dir()


def _read_names(*, path: Path) -> PersonaNames:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise PersonaError(f"{path} is missing; copy it from {default_dir() / NAMES_FILE}") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise PersonaError(f"{path} is not valid JSON: {error}") from None
    try:
        return PersonaNames.model_validate(data)
    except ValidationError:
        raise PersonaError(f'{path} must be a JSON object with a string "assistant_name"') from None


def load_names() -> PersonaNames:
    return _read_names(path=persona_dir() / NAMES_FILE)


def _write_names(*, path: Path, names: PersonaNames) -> None:
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    temporary.write_text(json.dumps(names.model_dump(exclude_none=True), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def save_user_name(*, user_name: str) -> PersonaNames:
    """Write the user's name into `local/persona.json`, first copying `default/` into `local/` for whatever it lacks."""
    user_name = user_name.strip()
    if not user_name:
        raise PersonaError("the user name is empty")
    local = local_dir()
    if not local.exists():
        shutil.copytree(default_dir(), local)
    path = local / NAMES_FILE
    if not path.exists():
        shutil.copy2(default_dir() / NAMES_FILE, path)
    names = _read_names(path=path).model_copy(update={"user_name": user_name})
    _write_names(path=path, names=names)
    return names
