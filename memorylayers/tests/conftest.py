import json
import shutil
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from memorylayers.adapters.paths import parent_paths
from memorylayers.adapters.store import MemoryStore
from memorylayers.models.paths import ParentPaths

NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    with MemoryStore(db_path=tmp_path / "memory.db") as memory:
        yield memory


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ParentPaths:
    monkeypatch.setenv("MEMORYLAYERS_DATA_ROOT", str(tmp_path / "data"))
    return parent_paths(parent="pk")


@pytest.fixture
def run_cli(paths: ParentPaths, capsys: pytest.CaptureFixture[str]) -> Callable[[list[str]], tuple[int, str, str]]:
    from memorylayers.entry.cli import main

    def run(argv: list[str]) -> tuple[int, str, str]:
        code = main(argv=[*argv, "--parent", "pk"])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return run


@pytest.fixture
def local_persona(shipped_persona: Path) -> Path:
    """A local persona naming the assistant Nova and the user Alex, in place of the shipped default."""
    local = shipped_persona / "local"
    shutil.copytree(shipped_persona / "default", local)
    (local / "persona.json").write_text(json.dumps({"assistant_name": "Nova", "user_name": "Alex"}), encoding="utf-8")
    return local


@pytest.fixture
def broken_persona(shipped_persona: Path) -> Path:
    """A local persona whose persona.json is not JSON; returns that file."""
    local = shipped_persona / "local"
    local.mkdir()
    names = local / "persona.json"
    names.write_text("{ not json", encoding="utf-8")
    return names
