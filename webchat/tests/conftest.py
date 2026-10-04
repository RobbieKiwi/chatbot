from pathlib import Path

import pytest

from webchat.adapters.files import webchat_paths
from webchat.models.paths import WebchatPaths


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WebchatPaths:
    monkeypatch.setenv("WEBCHAT_DATA_ROOT", str(tmp_path / "data"))
    return webchat_paths()
