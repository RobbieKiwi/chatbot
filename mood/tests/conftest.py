import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mood.models.mood import Axis, MoodState

NOW = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)


def mood_state(**values: float) -> MoodState:
    """A mood at 0 on every axis and presence 5, rolled and updated at NOW, with the given values."""
    base: dict[str, object] = {axis.value: 0.0 for axis in Axis} | {"presence": 5.0, "presence_base": 5.0, "rolled_at": NOW, "updated_at": NOW}
    return MoodState.model_validate(base | values)


def write_transcript(*, path: Path, turns: list[tuple[str, str]]) -> Path:
    lines = [json.dumps({"type": role, "timestamp": "2026-10-04T19:00:00Z", "message": {"role": role, "content": [{"type": "text", "text": text}]}}) for role, text in turns]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "mood"
    monkeypatch.setenv("MOOD_DATA_ROOT", str(root))
    return root


def write_persona(*, root: Path, assistant_name: str, user_name: str, persona_md: str) -> Path:
    """A local persona under the persona root, which then takes the place of the default."""
    local = root / "local"
    local.mkdir(parents=True)
    (local / "persona.json").write_text(json.dumps({"assistant_name": assistant_name, "user_name": user_name}), encoding="utf-8")
    (local / "PERSONA.md").write_text(persona_md, encoding="utf-8")
    return local
