import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from folderaccess.adapters import paths

SETTINGS = {
    "permissions": {
        "allow": ["Bash(git status)", "Read(./notes/**)", "Glob(./notes/**)"],
        "deny": [],
    },
    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "stop"}]}]},
}


def _bytes(*, path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


@dataclass
class Layout:
    home: Path
    project_root: Path
    list_path: Path
    settings_path: Path  # the local settings, which the list syncs into
    shared_settings_path: Path  # the committed settings, never touched

    def snapshot(self) -> tuple[bytes | None, bytes | None, bytes | None]:
        return _bytes(path=self.list_path), _bytes(path=self.settings_path), _bytes(path=self.shared_settings_path)


@pytest.fixture
def layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Layout:
    home = tmp_path / "home"
    project_root = home / "project"
    for folder in (project_root / "src", project_root / ".claude", home / "documents", home / "drafts"):
        folder.mkdir(parents=True)
    shared_settings_path = project_root / ".claude" / "settings.json"
    shared_settings_path.write_text(json.dumps({"hooks": {"Stop": []}}, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setenv("FOLDERACCESS_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(paths, "PROJECT_ROOT", project_root)
    return Layout(
        home=home,
        project_root=project_root,
        list_path=tmp_path / "data" / "folders.txt",
        settings_path=project_root / ".claude" / "settings.local.json",
        shared_settings_path=shared_settings_path,
    )
