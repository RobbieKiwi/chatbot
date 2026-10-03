from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from memorylayers.models.vocab import Role
from memorylayers.tools.transcript import parse_turn, parse_turns

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"
BERLIN = ZoneInfo("Europe/Berlin")


def _turns() -> list:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    return parse_turns(lines=lines, first_line=0, session_id="s1", tz=BERLIN)


def test_only_visible_text_survives() -> None:
    turns = _turns()
    assert [(turn.role, turn.text) for turn in turns] == [
        (Role.ASSISTANT, "Hello, Alex. Tell me something true."),
        (Role.USER, "Yesterday I went dancing with Jordan."),
        (Role.ASSISTANT, "Tango? Of course you did."),
    ]


def test_turns_keep_their_line_numbers() -> None:
    assert [turn.line for turn in _turns()] == [6, 8, 12]


def test_a_turn_just_after_local_midnight_has_its_local_date() -> None:
    # 23:31 UTC on 1 October is 01:31 on 2 October in Berlin.
    user_turn = _turns()[1]
    assert user_turn.at.date() == date(2026, 10, 2)
    assert user_turn.at.utcoffset() is not None


def test_garbage_lines_are_skipped() -> None:
    assert parse_turn(line='{"type": "user", "mess', line_number=0, session_id="s1", tz=BERLIN) is None
