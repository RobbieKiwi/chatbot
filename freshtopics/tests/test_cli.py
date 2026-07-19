from pathlib import Path

import pytest

import freshtopics.dao
from freshtopics.__main__ import main


@pytest.fixture(autouse=True)
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(freshtopics.dao, "DATA_ROOT", tmp_path)
    return tmp_path


def test_log_then_context(capsys: pytest.CaptureFixture[str], data_root: Path) -> None:
    assert main(argv=["log", "--parent", "pk", "--phrase", "childhood computer games", "--initiator", "skill", "--score", "9"]) == 0
    assert (data_root / "pk" / "topics.json").exists()
    capsys.readouterr()
    assert main(argv=["context", "--parent", "pk"]) == 0
    out = capsys.readouterr().out
    assert "- childhood computer games (skill, 9)" in out
    assert "Excellent topics: childhood computer games" in out


def test_invalid_topics_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv=["log", "--parent", "pk", "--phrase", "two words", "--initiator", "skill"]) == 2
    assert "3-8 words" in capsys.readouterr().err


def test_log_into_a_fresh_data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fresh = tmp_path / "clone" / "freshtopics" / "data"
    monkeypatch.setattr(freshtopics.dao, "DATA_ROOT", fresh)
    assert main(argv=["log", "--parent", "chatbot", "--phrase", "the last lighthouse keeper", "--initiator", "skill", "--score", "7"]) == 0
    assert (fresh / "chatbot" / "topics.json").exists()
