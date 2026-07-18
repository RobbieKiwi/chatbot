"""Plain-text renderings of memory for the assistant, the librarian and the workers."""

from collections.abc import Sequence
from zoneinfo import ZoneInfo

from memorylayers.models.dates import ONGOING_END
from memorylayers.models.memory import Period
from memorylayers.models.views import FactLine, SearchHit, TagDates, TagLine
from memorylayers.models.vocab import SearchKind, TagKind

CLI = ".venv/Scripts/python -m memorylayers"
FACTS_SHOWN = 10


def format_fact(*, fact: FactLine) -> str:
    line = f"#{fact.id} [{fact.relevance}] {fact.occurred} · {fact.detail} ({', '.join(fact.tags)})"
    return f"{line} — superseded by #{fact.superseded_by}" if fact.superseded_by else line


def format_fact_list(*, facts: Sequence[FactLine], limit: int, more_command: str) -> str:
    lines = [format_fact(fact=fact) for fact in facts[:limit]] or ["No facts."]
    if len(facts) > limit:
        lines.append(f"{len(facts) - limit} more facts: {more_command}")
    return "\n".join(lines)


def _counts(*, pairs: Sequence[tuple[str, int]]) -> str:
    return ", ".join(f"{name} ({count})" for name, count in pairs) or "none"


def _summary_or_facts(*, name: str, summary: str | None, facts: Sequence[FactLine], parent: str) -> list[str]:
    if summary:
        return ["Summary:", summary, f"{len(facts)} facts beneath: {CLI} facts {name} --parent {parent}"]
    more = f"{CLI} facts {name} --limit {len(facts)} --parent {parent}"
    return ["Facts:", format_fact_list(facts=facts, limit=FACTS_SHOWN, more_command=more)]


def format_entity_recall(
    *, tag: TagLine, summary: str | None, facts: Sequence[FactLine], related: Sequence[tuple[str, int]], categories: Sequence[tuple[str, int]], dates: TagDates, tz: ZoneInfo, parent: str
) -> str:
    first = dates.first_recorded.astimezone(tz).date() if dates.first_recorded else "never"
    last = dates.last_recorded.astimezone(tz).date() if dates.last_recorded else "never"
    latest = dates.latest_occurred or "unknown"
    return "\n".join(
        [
            f"{tag.name} (entity): {tag.description}",
            *_summary_or_facts(name=tag.name, summary=summary, facts=facts, parent=parent),
            f"Related: {_counts(pairs=related)}",
            f"Categories: {_counts(pairs=categories)}",
            f"First mentioned {first} · last mentioned {last} · latest occurred {latest}",
        ]
    )


def format_category_recall(*, tag: TagLine, summary: str | None, facts: Sequence[FactLine], top_entities: Sequence[tuple[str, int]], parent: str) -> str:
    return "\n".join(
        [
            f"{tag.name} (category): {tag.description}",
            *_summary_or_facts(name=tag.name, summary=summary, facts=facts, parent=parent),
            f"Top entities: {_counts(pairs=top_entities)}",
        ]
    )


def format_period_recall(*, name: str, between: str, summary: str | None, facts: Sequence[FactLine], parent: str) -> str:
    more = f"{CLI} facts --between {between} --limit {len(facts)} --parent {parent}"
    if summary:
        return "\n".join([f"{name} ({between})", summary, f"{len(facts)} facts beneath: {more}"])
    return "\n".join([f"{name} ({between})", format_fact_list(facts=facts, limit=FACTS_SHOWN, more_command=more)])


def format_unknown(*, name: str, near: Sequence[str]) -> str:
    closest = f" Closest: {', '.join(near)}." if near else " Try search instead."
    return f"Nothing called {name!r}.{closest}"


_HIT_LABELS = {SearchKind.FACT: "fact #{key}", SearchKind.TAG: "tag: {key}", SearchKind.TAG_SUMMARY: "tag summary: {key}", SearchKind.PERIOD: "period: {key}"}


def format_search(*, hits: Sequence[SearchHit]) -> str:
    return "\n".join(f"{_HIT_LABELS[hit.kind].format(key=hit.key)} — {hit.snippet}" for hit in hits) or "No matches."


def format_tags(*, tags: Sequence[TagLine]) -> str:
    def listing(kind: TagKind) -> str:
        return ", ".join(f"{tag.name} ({tag.fact_count})" for tag in tags if tag.kind is kind) or "none"

    return f"Categories: {listing(TagKind.CATEGORY)}\nEntities: {listing(TagKind.ENTITY)}"


def format_periods(*, periods: Sequence[Period], tz: ZoneInfo) -> str:
    def line(period: Period) -> str:
        end = "ongoing" if period.end == ONGOING_END else period.end.isoformat()
        refreshed = period.refreshed_at.astimezone(tz).date() if period.refreshed_at else "never"
        return f"{period.name} ({period.kind}) {period.start}..{end} — refreshed {refreshed}"

    return "\n".join(line(period) for period in periods) or "No periods yet."
