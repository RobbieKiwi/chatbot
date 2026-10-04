from datetime import timedelta
from pathlib import Path

import pytest

from feedback.adapters.paths import feedback_path
from feedback.adapters.store import editing_feedback, load_feedback
from feedback.domain.filing import file_feedback
from feedback.entry import cli
from feedback.entry.cli import main
from feedback.models.commands import AddNote, NewItem
from feedback.tests.conftest import NOW


@pytest.fixture
def filed(data_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cli, "now_utc", lambda: NOW + timedelta(hours=1))
    path = feedback_path(parent="pk")
    with editing_feedback(path=path) as feedback:
        file_feedback(feedback=feedback, command=NewItem(text="fewer questions"), context="Nova: why? why? why?", now=NOW)
        file_feedback(feedback=feedback, command=NewItem(text="more puns"), context="", now=NOW)
        file_feedback(feedback=feedback, command=AddNote(item_id=1, text="still"), context="Nova: why?!", now=NOW + timedelta(minutes=5))
    return path


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv=[*argv, "--parent", "pk"])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_open_lists_items_with_notes(filed: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["open"], capsys)
    assert code == 0
    assert "#1 [open] 2026-10-04 fewer questions" in out
    assert "  note 2026-10-04: still" in out
    assert "#2 [open] 2026-10-04 more puns" in out
    assert "why? why?" not in out


def test_record_change_then_open_and_history(filed: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["record-change", "--summary", "Cap questions per reply", "--files", "PERSONA.md,TOPICS.md", "--partly", "1", "--resolved", "2"], capsys)
    assert (code, out.strip()) == (0, "change #1 recorded")
    _, out, _ = _run(["open"], capsys)
    assert "#1 [partly]" in out
    assert "  change #1 (partly) 2026-" in out
    assert "more puns" not in out
    _, out, _ = _run(["history"], capsys)
    assert "#1 2026-" in out and "Cap questions per reply" in out and "PERSONA.md, TOPICS.md" in out and "partly #1" in out and "resolved #2" in out
    assert load_feedback(path=filed).changes[0].files == ["PERSONA.md", "TOPICS.md"]


def test_show_includes_context(filed: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["show", "1"], capsys)
    assert code == 0
    assert "Nova: why? why? why?" in out and "Nova: why?!" in out


def test_errors_exit_2(filed: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["show", "9"], capsys)
    assert (code, err.strip()) == (2, "no feedback item #9")
    code, _, err = _run(["record-change", "--summary", "x", "--resolved", "9"], capsys)
    assert (code, err.strip()) == (2, "unknown items: 9")


def test_an_invalid_file_fails_loudly(data_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = feedback_path(parent="pk")
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")
    code, _, err = _run(["open"], capsys)
    assert code == 2
    assert "invalid feedback file" in err


def test_nothing_open(data_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(["open"], capsys)[1].strip() == "No open feedback."
