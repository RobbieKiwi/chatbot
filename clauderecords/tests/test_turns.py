from pathlib import Path

from clauderecords.models import Role, TextTurn
from clauderecords.turns import last_text_turns, render_turns

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"


def test_only_the_visible_text_turns_survive() -> None:
    assert last_text_turns(transcript_path=FIXTURE, count=10) == [
        TextTurn(role=Role.ASSISTANT, text="Hello, Alex. Tell me something true."),
        TextTurn(role=Role.USER, text="Yesterday I went dancing with Jordan."),
        TextTurn(role=Role.ASSISTANT, text="Tango? Of course you did."),
    ]


def test_count_keeps_the_last_turns() -> None:
    assert [turn.text for turn in last_text_turns(transcript_path=FIXTURE, count=2)] == ["Yesterday I went dancing with Jordan.", "Tango? Of course you did."]


def test_zero_count_and_missing_file_give_nothing(tmp_path: Path) -> None:
    assert last_text_turns(transcript_path=FIXTURE, count=0) == []
    assert last_text_turns(transcript_path=tmp_path / "missing.jsonl", count=5) == []


def test_render_names_the_speakers() -> None:
    turns = [TextTurn(role=Role.USER, text="hi"), TextTurn(role=Role.ASSISTANT, text="hello")]
    assert render_turns(turns=turns, user_name="Alex", assistant_name="Nova") == "Alex: hi\n\nNova: hello"
