from datetime import date

from memorylayers.tools.date_mentions import period_names_mentioned

TODAY = date(2026, 10, 3)


def test_years() -> None:
    assert period_names_mentioned(text="back in 2014 and 2016", today=TODAY) == [["2014"], ["2016"]]


def test_month_names_resolve_to_the_latest_such_month() -> None:
    assert period_names_mentioned(text="in March", today=TODAY) == [["2026-03", "2026 Q1", "2026"]]
    assert period_names_mentioned(text="in November", today=TODAY) == [["2025-11", "2025 Q4", "2025"]]


def test_relative_phrases() -> None:
    assert period_names_mentioned(text="last summer", today=TODAY) == [["2026 Q3", "2026"]]
    assert period_names_mentioned(text="last year", today=TODAY) == [["2025"]]
    assert period_names_mentioned(text="last week", today=TODAY) == [["2026-W39", "2026-09", "2026 Q3", "2026"]]


def test_may_is_not_a_month() -> None:
    assert period_names_mentioned(text="I may go", today=TODAY) == []
