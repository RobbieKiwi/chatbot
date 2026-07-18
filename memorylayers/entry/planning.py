"""What a summary refresh needs, gathered from the store."""

from datetime import date

from memorylayers.adapters.store import MemoryStore
from memorylayers.domain.refresh import plan_refresh
from memorylayers.models.dates import ONGOING_END, Bucket
from memorylayers.models.views import BriefSection, RefreshPlan
from memorylayers.models.vocab import PeriodKind
from memorylayers.tools.calendar import bucket_calendar, finest_bucket, parse_bucket_name


def _calendar(*, store: MemoryStore, today: date) -> list[Bucket]:
    return bucket_calendar(today=today, earliest_year=store.earliest_year() or today.year)


def _stored_buckets(*, store: MemoryStore) -> list[Bucket]:
    return [Bucket(name=period.name, kind=period.kind, start=period.start, end=period.end) for period in store.periods()]


def plan_for(*, store: MemoryStore, today: date) -> RefreshPlan:
    state = store.refresh_state()
    return plan_refresh(
        touched=store.touched_facts(above_revision=state.through_revision),
        tag_fact_counts={tag.name: tag.fact_count for tag in store.tag_lines()},
        stored_periods=_stored_buckets(store=store),
        calendar=_calendar(store=store, today=today),
        last_week_start=state.calendar_week_start,
        today=today,
        current_revision=store.max_revision(),
    )


def period_bucket(*, store: MemoryStore, name: str) -> Bucket | None:
    """A calendar bucket by its name, or a stored era."""
    bucket = parse_bucket_name(name=name)
    if bucket is not None:
        return bucket
    era = store.period(name=name)
    return Bucket(name=era.name, kind=era.kind, start=era.start, end=era.end) if era and era.kind is PeriodKind.ERA else None


def tag_sections(*, store: MemoryStore, plan: RefreshPlan) -> list[BriefSection]:
    lines = {tag.name: tag for tag in store.tag_lines()}
    sections = []
    for name in plan.tag_names:
        existing = store.tag_summary(name=name)
        tag = lines[name]
        sections.append(BriefSection(title=f"tag {name} ({tag.kind}): {tag.description}", facts=store.facts_for_tag(name=name), existing_summary=existing.summary if existing else ""))
    return sections


def period_sections(*, store: MemoryStore, plan: RefreshPlan, today: date) -> list[BriefSection]:
    calendar = _calendar(store=store, today=today)
    spans = store.fact_spans()
    lines = {line.id: line for line in store.current_facts()}
    stored = store.periods()
    sections = []
    for bucket in plan.periods:
        if bucket.kind is PeriodKind.ERA:
            members = [span.id for span in spans if span.start and span.end and span.start <= bucket.end and bucket.start <= span.end]
        else:
            members = [span.id for span in spans if span.start and span.end and (container := finest_bucket(start=span.start, end=span.end, buckets=calendar)) and container.name == bucket.name]
        children = {
            period.name: period.summary
            for period in stored
            if period.name != bucket.name and period.kind is not PeriodKind.ERA and bucket.start <= period.start and period.end <= bucket.end and period.summary
        }
        existing = next((period.summary for period in stored if period.name == bucket.name), "")
        end = "ongoing" if bucket.end == ONGOING_END else bucket.end.isoformat()
        sections.append(
            BriefSection(title=f"period {bucket.name} ({bucket.kind}, {bucket.start}..{end})", facts=[lines[i] for i in members if i in lines], existing_summary=existing, child_summaries=children)
        )
    return sections
