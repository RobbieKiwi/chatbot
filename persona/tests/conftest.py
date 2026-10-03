import json
from pathlib import Path

import pytest

SCALES = """| Scale | 0 | 5 | 10 |
|---|---|---|---|
| cheerfulness | Flat | Pleasant | Delighted |
| irritation | Patient | Short fuse | Everything grates |"""

PERSONA_MD = f"# Test persona\n\nSome character.\n\n## Mood\n\n{SCALES}\n\nAfter the table.\n"


def write_persona(*, folder: Path, names: dict[str, str] | None = None, persona_md: str = PERSONA_MD) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "persona.json").write_text(json.dumps(names or {"assistant_name": "Nova"}), encoding="utf-8")
    (folder / "PERSONA.md").write_text(persona_md, encoding="utf-8")
    return folder


@pytest.fixture
def persona_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A persona root holding only default/, as a fresh clone has it."""
    root = tmp_path / "persona"
    write_persona(folder=root / "default")
    monkeypatch.setenv("PERSONA_ROOT", str(root))
    return root
