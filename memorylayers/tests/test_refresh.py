from datetime import date

from memorylayers.domain.refresh import plan_refresh
from memorylayers.models.dates import Bucket
from memorylayers.models.views import FactSpan, RefreshPlan
from memorylayers.models.vocab import PeriodKind
from memorylayers.tools.calendar import bucket_calendar, week_bucket

TODAY = date(2026, 10, 3)
CALENDAR = bucket_calendar(today=TODAY, earliest_year=2014)
PORTUGAL = Bucket(name="Portugal", kind=PeriodKind.ERA, start=date(2019, 3, 1), end=date(2021, 6, 30))


def _plan(*, touched: list[FactSpan], stored: list[Bucket], last_week: date | None) -> RefreshPlan:
    return plan_refresh(touched=touched, tag_fact_counts={"jordan": 3, "friend": 2}, stored_periods=stored, calendar=CALENDAR, last_week_start=last_week, today=TODAY, current_revision=42)


def test_touched_facts_make_their_finest_bucket_eras_and_tags_due() -> None:
    touched = [
        FactSpan(id=1, start=date(2026, 10, 2), end=date(2026, 10, 2), tags=["jordan", "friend"]),
        FactSpan(id=2, start=date(2020, 5, 1), end=date(2020, 5, 31), tags=["friend"]),
        FactSpan(id=3, start=None, end=None, tags=["jordan"]),
    ]
    plan = _plan(touched=touched, stored=[PORTUGAL], last_week=date(2026, 9, 28))
    assert [bucket.name for bucket in plan.periods] == ["Portugal", "2020", "2026-W40"]
    assert plan.tag_names == ["jordan"]
    assert plan.expired_periods == []
    assert plan.through_revision == 42


def test_a_new_week_expires_old_buckets_into_their_container() -> None:
    expired_week = week_bucket(start=date(2026, 9, 14))
    plan = _plan(touched=[], stored=[expired_week, PORTUGAL], last_week=date(2026, 9, 21))
    assert plan.expired_periods == ["2026-W38"]
    assert [bucket.name for bucket in plan.periods] == ["2026 Q3"]


def test_nothing_due_is_an_empty_plan() -> None:
    assert _plan(touched=[], stored=[PORTUGAL], last_week=date(2026, 9, 28)).is_empty
