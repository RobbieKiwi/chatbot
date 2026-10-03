import json
from pathlib import Path

import pytest

from persona.entry.cli import main


def test_show_reports_an_unset_user_and_the_default_persona(persona_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv=["show"]) == 0
    out = capsys.readouterr().out
    assert "assistant: Nova" in out
    assert "user: not set" in out
    assert f"persona: {persona_root / 'default' / 'PERSONA.md'}" in out


def test_set_user_saves_the_name_and_show_reports_the_local_persona(persona_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv=["set-user", "--name", "Zoë O'Brien"]) == 0
    assert "Zoë O'Brien" in capsys.readouterr().out
    assert json.loads((persona_root / "local" / "persona.json").read_text(encoding="utf-8"))["user_name"] == "Zoë O'Brien"
    assert main(argv=["show"]) == 0
    out = capsys.readouterr().out
    assert "user: Zoë O'Brien" in out
    assert f"persona: {persona_root / 'local' / 'PERSONA.md'}" in out


def test_a_broken_persona_is_a_one_line_error(persona_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (persona_root / "local").mkdir()
    (persona_root / "local" / "persona.json").write_text("{ nope", encoding="utf-8")
    assert main(argv=["show"]) == 2
    err = capsys.readouterr().err
    assert str(persona_root / "local" / "persona.json") in err and len(err.strip().splitlines()) == 1
