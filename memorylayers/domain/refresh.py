"""Which summaries a refresh must rewrite."""

from datetime import date

from memorylayers.models.dates import Bucket
from memorylayers.models.views import FactSpan, RefreshPlan
from memorylayers.models.vocab import PeriodKind
from memorylayers.tools.calendar import finest_bucket, week_start

TAG_SUMMARY_MIN_FACTS = 3


def _by_start(bucket: Bucket) -> tuple[date, str]:
    return bucket.start, bucket.name


def plan_refresh(
    *, touched: list[FactSpan], tag_fact_counts: dict[str, int], stored_periods: list[Bucket], calendar: list[Bucket], last_week_start: date | None, today: date, current_revision: int
) -> RefreshPlan:
    eras = [period for period in stored_periods if period.kind is PeriodKind.ERA]
    due: dict[str, Bucket] = {}
    for fact in touched:
        if fact.start is None or fact.end is None:
            continue
        bucket = finest_bucket(start=fact.start, end=fact.end, buckets=calendar)
        if bucket is not None:
            due[bucket.name] = bucket
        for era in eras:
            if era.start <= fact.end and fact.start <= era.end:
                due[era.name] = era
    this_week = week_start(day=today)
    expired: list[str] = []
    if last_week_start != this_week:
        live = {bucket.name for bucket in calendar}
        for period in stored_periods:
            if period.kind is PeriodKind.ERA or period.name in live:
                continue
            expired.append(period.name)
            container = finest_bucket(start=period.start, end=period.end, buckets=calendar)
            if container is not None:
                due[container.name] = container
    tag_names = sorted({tag for fact in touched for tag in fact.tags if tag_fact_counts.get(tag, 0) >= TAG_SUMMARY_MIN_FACTS})
    return RefreshPlan(
        through_revision=current_revision,
        calendar_week_start=this_week,
        tag_names=tag_names,
        periods=sorted(list(due.values()), key=_by_start),
        expired_periods=sorted(expired),
    )


def format_plan(*, plan: RefreshPlan) -> str:
    periods = ", ".join(f"{bucket.name} ({bucket.kind})" for bucket in plan.periods) or "none"
    return "\n".join(
        [
            f"Refresh plan through revision {plan.through_revision} (calendar week of {plan.calendar_week_start})",
            f"Tags: {', '.join(plan.tag_names) or 'none'}",
            f"Periods: {periods}",
            f"Expired: {', '.join(plan.expired_periods) or 'none'}",
        ]
    )
