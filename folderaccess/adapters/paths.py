"""Where the folder list and the local project settings it syncs into live."""

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent


def data_root() -> Path:
    return Path(os.environ.get("FOLDERACCESS_DATA_ROOT", PACKAGE_ROOT / "data"))


def list_path() -> Path:
    return data_root() / "folders.txt"


def settings_path() -> Path:
    """The user's own, gitignored settings; the committed settings.json is never written."""
    return PROJECT_ROOT / ".claude" / "settings.local.json"
