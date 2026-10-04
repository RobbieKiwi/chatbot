import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def write_transcript(*, path: Path, turns: list[tuple[str, str]]) -> Path:
    lines = [json.dumps({"type": role, "timestamp": "2026-10-04T10:00:00Z", "message": {"role": role, "content": [{"type": "text", "text": text}]}}) for role, text in turns]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "feedback"
    monkeypatch.setenv("FEEDBACK_DATA_ROOT", str(root))
    return root
