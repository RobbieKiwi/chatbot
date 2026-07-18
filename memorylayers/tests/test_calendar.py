from datetime import date

from memorylayers.models.dates import Bucket
from memorylayers.models.vocab import PeriodKind
from memorylayers.tools.calendar import bucket_calendar, finest_bucket, parse_bucket_name, week_bucket, week_start


def test_bucket_calendar_on_a_saturday_in_q4() -> None:
    names = [bucket.name for bucket in bucket_calendar(today=date(2026, 10, 3), earliest_year=2024)]
    assert names == [
        "2026-W40",
        "2026-W39",
        "2026-10",
        "2026 Q1",
        "2026 Q2",
        "2026 Q3",
        "2026 Q4",
        "2025 Q1",
        "2025 Q2",
        "2025 Q3",
        "2025 Q4",
        "2024",
        "2025",
        "2026",
    ]


def test_week_bucket_spans_monday_to_sunday() -> None:
    bucket = week_bucket(start=week_start(day=date(2026, 10, 3)))
    assert (bucket.start, bucket.end, bucket.kind) == (date(2026, 9, 28), date(2026, 10, 4), PeriodKind.WEEK)


def _finest_name(*, start: date, end: date, buckets: list[Bucket]) -> str | None:
    bucket = finest_bucket(start=start, end=end, buckets=buckets)
    return None if bucket is None else bucket.name


def test_finest_bucket_takes_the_smallest_wholly_containing_bucket() -> None:
    buckets = bucket_calendar(today=date(2026, 10, 3), earliest_year=2020)
    assert _finest_name(start=date(2026, 10, 2), end=date(2026, 10, 2), buckets=buckets) == "2026-W40"
    assert _finest_name(start=date(2026, 10, 1), end=date(2026, 10, 31), buckets=buckets) == "2026-10"
    assert _finest_name(start=date(2026, 7, 14), end=date(2026, 7, 14), buckets=buckets) == "2026 Q3"
    assert _finest_name(start=date(2026, 1, 1), end=date(2026, 12, 31), buckets=buckets) == "2026"
    assert _finest_name(start=date(2021, 5, 1), end=date(2021, 5, 31), buckets=buckets) == "2021"
    assert finest_bucket(start=date(2014, 1, 1), end=date(2016, 12, 31), buckets=buckets) is None


def test_parse_bucket_name() -> None:
    quarter, week, month, year = (parse_bucket_name(name=name) for name in ("2026 Q3", "2026-W40", "2026-02", "2014"))
    assert quarter is not None
    assert week is not None
    assert month is not None
    assert year is not None
    assert quarter.start == date(2026, 7, 1)
    assert week.end == date(2026, 10, 4)
    assert month.end == date(2026, 2, 28)
    assert year.kind is PeriodKind.YEAR
    assert parse_bucket_name(name="Portugal") is None
