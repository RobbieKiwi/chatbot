"""The project's local Claude Code settings file."""

import json

from folderaccess.adapters import paths
from folderaccess.adapters.files import write_text_atomically


def read_settings() -> dict[str, object]:
    """A missing file is empty settings. Raise ValueError when the file is unreadable, unparsable or not a JSON object."""
    path = paths.settings_path()
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(settings, dict):
        raise ValueError(f"cannot read {path}: not a JSON object")
    return settings


def write_settings(*, settings: dict[str, object]) -> None:
    write_text_atomically(path=paths.settings_path(), text=json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
