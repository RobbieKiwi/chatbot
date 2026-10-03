from datetime import UTC, datetime

from memorylayers.domain.window import select_window, unprocessed_chars
from memorylayers.models.transcript import ConversationTurns, Turn
from memorylayers.models.vocab import Role

AT = datetime(2026, 10, 3, tzinfo=UTC)


def _turn(*, session: str, line: int, chars: int) -> Turn:
    return Turn(role=Role.USER, text="x" * chars, at=AT, session_id=session, line=line)


def test_the_window_stops_once_it_reaches_the_threshold() -> None:
    turns = ConversationTurns(
        processed=[_turn(session="a", line=1, chars=50), _turn(session="a", line=3, chars=20)],
        unprocessed=[_turn(session="a", line=5, chars=60), _turn(session="a", line=7, chars=60), _turn(session="b", line=2, chars=10)],
        ends={"a": 9, "b": 4},
    )
    window = select_window(turns=turns, threshold_chars=100, overlap_fraction=0.3)
    assert [turn.line for turn in window.new] == [5, 7]
    assert window.end == {"a": 9, "b": 2}
    assert [turn.line for turn in window.context] == [1, 3]


def test_context_is_bounded_by_the_overlap() -> None:
    turns = ConversationTurns(
        processed=[_turn(session="a", line=1, chars=50), _turn(session="a", line=3, chars=40)],
        unprocessed=[_turn(session="a", line=5, chars=10)],
        ends={"a": 6},
    )
    window = select_window(turns=turns, threshold_chars=100, overlap_fraction=0.3)
    assert [turn.line for turn in window.context] == [3]
    assert window.end == {"a": 6}


def test_unprocessed_chars() -> None:
    assert unprocessed_chars(turns=[_turn(session="a", line=1, chars=7), _turn(session="a", line=2, chars=5)]) == 12
