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
