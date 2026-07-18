"""The recency-bucket calendar: coarser buckets further from today."""

import calendar
import re
from datetime import date, timedelta

from memorylayers.models.dates import Bucket
from memorylayers.models.vocab import PeriodKind


def week_start(*, day: date) -> date:
    return day - timedelta(days=day.weekday())


def quarter_of(*, month: int) -> int:
    return (month - 1) // 3 + 1


def week_bucket(*, start: date) -> Bucket:
    iso = start.isocalendar()
    return Bucket(name=f"{iso.year}-W{iso.week:02d}", kind=PeriodKind.WEEK, start=start, end=start + timedelta(days=6))


def month_bucket(*, year: int, month: int) -> Bucket:
    last = calendar.monthrange(year, month)[1]
    return Bucket(name=f"{year}-{month:02d}", kind=PeriodKind.MONTH, start=date(year, month, 1), end=date(year, month, last))


def quarter_bucket(*, year: int, quarter: int) -> Bucket:
    last_month = quarter * 3
    last = calendar.monthrange(year, last_month)[1]
    return Bucket(name=f"{year} Q{quarter}", kind=PeriodKind.QUARTER, start=date(year, last_month - 2, 1), end=date(year, last_month, last))


def year_bucket(*, year: int) -> Bucket:
    return Bucket(name=str(year), kind=PeriodKind.YEAR, start=date(year, 1, 1), end=date(year, 12, 31))


def bucket_calendar(*, today: date, earliest_year: int) -> list[Bucket]:
    this_week = week_start(day=today)
    quarter = quarter_of(month=today.month)
    return [
        week_bucket(start=this_week),
        week_bucket(start=this_week - timedelta(days=7)),
        *(month_bucket(year=today.year, month=month) for month in range(quarter * 3 - 2, today.month + 1)),
        *(quarter_bucket(year=today.year, quarter=q) for q in range(1, 5)),
        *(quarter_bucket(year=today.year - 1, quarter=q) for q in range(1, 5)),
        *(year_bucket(year=year) for year in range(min(earliest_year, today.year), today.year + 1)),
    ]


def _span(bucket: Bucket) -> timedelta:
    return bucket.end - bucket.start


def finest_bucket(*, start: date, end: date, buckets: list[Bucket]) -> Bucket | None:
    containing = [bucket for bucket in buckets if bucket.start <= start and end <= bucket.end]
    return min(containing, key=_span) if containing else None


def parse_bucket_name(*, name: str) -> Bucket | None:
    """The calendar bucket a name denotes, or None for anything else (an era's name)."""
    if match := re.fullmatch(r"(\d{4})-W(\d{2})", name):
        return week_bucket(start=date.fromisocalendar(int(match[1]), int(match[2]), 1))
    if match := re.fullmatch(r"(\d{4})-(\d{2})", name):
        return month_bucket(year=int(match[1]), month=int(match[2]))
    if match := re.fullmatch(r"(\d{4}) Q([1-4])", name):
        return quarter_bucket(year=int(match[1]), quarter=int(match[2]))
    if match := re.fullmatch(r"(\d{4})", name):
        return year_bucket(year=int(match[1]))
    return None
