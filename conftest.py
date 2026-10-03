import shutil
from pathlib import Path

import pytest

SHIPPED_PERSONA = Path(__file__).parent / "persona" / "default"


@pytest.fixture(autouse=True)
def shipped_persona(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every test reads a copy of the shipped persona, never a developer's persona/local/."""
    root = tmp_path_factory.mktemp("persona")
    shutil.copytree(SHIPPED_PERSONA, root / "default")
    monkeypatch.setenv("PERSONA_ROOT", str(root))
    return root
