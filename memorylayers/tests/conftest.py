from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from memorylayers.adapters.store import MemoryStore

NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    with MemoryStore(db_path=tmp_path / "memory.db") as memory:
        yield memory
