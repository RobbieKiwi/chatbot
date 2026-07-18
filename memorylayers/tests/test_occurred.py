from datetime import date

import pytest

from memorylayers.models.dates import OccurredRange
from memorylayers.models.vocab import Precision
from memorylayers.tools.occurred import TIMELESS, OccurredFormatError, label_occurred, parse_occurred


@pytest.mark.parametrize(
    ("text", "start", "end", "precision"),
    [
        ("2026-10-01", date(2026, 10, 1), date(2026, 10, 1), Precision.DAY),
        ("2026-07", date(2026, 7, 1), date(2026, 7, 31), Precision.MONTH),
        ("2024-02", date(2024, 2, 1), date(2024, 2, 29), Precision.MONTH),
        ("2014", date(2014, 1, 1), date(2014, 12, 31), Precision.YEAR),
        ("2010s", date(2010, 1, 1), date(2019, 12, 31), Precision.DECADE),
        ("2014..2016", date(2014, 1, 1), date(2016, 12, 31), Precision.YEAR),
        ("2019-03..2021", date(2019, 3, 1), date(2021, 12, 31), Precision.YEAR),
    ],
)
def test_parse_occurred(text: str, start: date, end: date, precision: Precision) -> None:
    assert parse_occurred(text=text) == OccurredRange(start=start, end=end, precision=precision)


def test_unknown_has_no_dates() -> None:
    assert parse_occurred(text="unknown") == OccurredRange(start=None, end=None, precision=Precision.UNKNOWN)


@pytest.mark.parametrize("text", ["yesterday", "2026-13", "2026-02-30", "26", "2016..2014", "summer 2014"])
def test_rejects_anything_else(text: str) -> None:
    with pytest.raises(OccurredFormatError):
        parse_occurred(text=text)


@pytest.mark.parametrize(
    ("text", "label"),
    [("2026-10-01", "2026-10-01"), ("2026-07", "2026-07"), ("2014", "2014"), ("2010s", "2010s"), ("2014..2016", "2014..2016"), ("unknown", "date unknown")],
)
def test_label_round_trips(text: str, label: str) -> None:
    assert label_occurred(occurred=parse_occurred(text=text)) == label


def test_timeless_label() -> None:
    assert label_occurred(occurred=TIMELESS) == "timeless"
