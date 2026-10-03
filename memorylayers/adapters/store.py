"""SQLite memory store: the SQLModel tables in WAL mode, plus an FTS5 index over every layer."""

from collections import Counter, defaultdict
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from sqlalchemy import event, func
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, col, create_engine, delete, select

from memorylayers.models.dates import Bucket, OccurredRange
from memorylayers.models.memory import Fact, FactTag, Period, RefreshState, Tag, TagAlias, TagSummary
from memorylayers.models.tables import SEARCH_TABLE
from memorylayers.models.views import FactCandidate, FactLine, FactSpan, NewTag, SearchHit, TagDates, TagLine, TagVocabulary
from memorylayers.models.vocab import Precision, SearchKind
from memorylayers.tools.occurred import label_occurred
from memorylayers.tools.text import fts_query

_CANDIDATE_LIMIT = 20


def _configure(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def _id(fact: Fact) -> int:
    if fact.id is None:
        raise ValueError("fact has not been flushed")
    return fact.id


def _occurred(fact: Fact) -> OccurredRange:
    return OccurredRange(start=fact.occurred_start, end=fact.occurred_end, precision=fact.occurred_precision)


def _index(session: Session, *, kind: SearchKind, key: str, body: str | None) -> None:
    connection = session.connection()
    connection.exec_driver_sql(f"DELETE FROM {SEARCH_TABLE} WHERE kind = ? AND key = ?", (kind.value, key))
    if body:
        connection.exec_driver_sql(f"INSERT INTO {SEARCH_TABLE} (kind, key, body) VALUES (?, ?, ?)", (kind.value, key, body))


def _as_datetime(value: Any) -> datetime | None:
    # An aggregate may come back as raw ISO text or already converted, depending on SQLAlchemy's typing of it.
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def _next_revision(session: Session) -> int:
    return (session.exec(select(func.max(Fact.revision))).one() or 0) + 1


def _ranked(statement: Any) -> Any:
    return statement.order_by(col(Fact.relevance).desc(), col(Fact.recorded_at).desc())


def _fact_lines(session: Session, *, facts: Sequence[Fact]) -> list[FactLine]:
    ids = [_id(fact) for fact in facts]
    tags: defaultdict[int, list[str]] = defaultdict(list)
    if ids:
        for link in session.exec(select(FactTag).where(col(FactTag.fact_id).in_(ids)).order_by(col(FactTag.tag))):
            tags[link.fact_id].append(link.tag)
    return [
        FactLine(id=_id(fact), detail=fact.detail, occurred=label_occurred(occurred=_occurred(fact)), relevance=fact.relevance, tags=tags[_id(fact)], superseded_by=fact.superseded_by)
        for fact in facts
    ]


def _spans(session: Session, *, facts: Sequence[Fact]) -> list[FactSpan]:
    lines = {line.id: line for line in _fact_lines(session, facts=facts)}
    return [FactSpan(id=_id(fact), start=fact.occurred_start, end=fact.occurred_end, tags=lines[_id(fact)].tags) for fact in facts]


class MemoryStore:
    """Every read and write of one parent's memory database. Each call is its own short transaction."""

    def __init__(self, *, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine: Engine = create_engine(f"sqlite:///{db_path.as_posix()}")
        event.listen(self._engine, "connect", _configure)
        SQLModel.metadata.create_all(self._engine)
        with self._engine.begin() as connection:
            connection.exec_driver_sql(f"CREATE VIRTUAL TABLE IF NOT EXISTS {SEARCH_TABLE} USING fts5(kind UNINDEXED, key UNINDEXED, body, tokenize='porter unicode61')")
        with self._session() as session:
            if session.get(RefreshState, 1) is None:
                session.add(RefreshState(id=1))

    def __enter__(self) -> Self:
        return self

    def __exit__(self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None) -> None:
        self.close()

    def close(self) -> None:
        self._engine.dispose()

    @contextmanager
    def _session(self) -> Iterator[Session]:
        with Session(self._engine, expire_on_commit=False) as session:
            yield session
            session.commit()

    # Tags

    def vocabulary(self) -> TagVocabulary:
        with self._session() as session:
            kinds = {tag.name: tag.kind for tag in session.exec(select(Tag))}
            aliases = {alias.alias: alias.tag for alias in session.exec(select(TagAlias))}
        return TagVocabulary(kinds=kinds, aliases=aliases)

    def tag(self, *, name: str) -> Tag | None:
        with self._session() as session:
            return session.get(Tag, name)

    def tag_lines(self) -> list[TagLine]:
        with self._session() as session:
            counted = select(FactTag.tag, func.count()).join(Fact, col(Fact.id) == col(FactTag.fact_id)).where(col(Fact.superseded_by).is_(None)).group_by(col(FactTag.tag))
            counts = dict(session.exec(counted).all())
            summarised = set(session.exec(select(TagSummary.tag)).all())
            tags = session.exec(select(Tag).order_by(col(Tag.kind), col(Tag.name))).all()
        return [TagLine(name=tag.name, kind=tag.kind, description=tag.description, fact_count=counts.get(tag.name, 0), has_summary=tag.name in summarised) for tag in tags]

    def create_tag(self, *, new: NewTag, now: datetime) -> None:
        with self._session() as session:
            session.add(Tag(name=new.name, kind=new.kind, description=new.description, created_at=now))
            _index(session, kind=SearchKind.TAG, key=new.name, body=f"{new.name.replace('_', ' ')}: {new.description}")

    def describe_tag(self, *, name: str, description: str) -> None:
        with self._session() as session:
            tag = session.get(Tag, name)
            if tag is None:
                raise KeyError(name)
            tag.description = description
            _index(session, kind=SearchKind.TAG, key=name, body=f"{name.replace('_', ' ')}: {description}")

    def add_alias(self, *, alias: str, tag: str) -> None:
        with self._session() as session:
            session.merge(TagAlias(alias=alias, tag=tag))

    def merge_tag(self, *, source: str, target: str) -> int:
        """Move every fact from source to target, then make source an alias of target."""
        with self._session() as session:
            revision = _next_revision(session)
            links = session.exec(select(FactTag).where(FactTag.tag == source)).all()
            for link in links:
                if session.get(FactTag, (link.fact_id, target)) is None:
                    session.add(FactTag(fact_id=link.fact_id, tag=target))
                session.delete(link)
                fact = session.get(Fact, link.fact_id)
                if fact is not None:
                    fact.revision = revision
            for alias in session.exec(select(TagAlias).where(TagAlias.tag == source)):
                alias.tag = target
            summary = session.get(TagSummary, source)
            if summary is not None:
                session.delete(summary)
            session.flush()
            tag = session.get(Tag, source)
            if tag is not None:
                session.delete(tag)
            session.flush()
            session.add(TagAlias(alias=source, tag=target))
            _index(session, kind=SearchKind.TAG, key=source, body=None)
            _index(session, kind=SearchKind.TAG_SUMMARY, key=source, body=None)
            return len(links)

    # Facts

    def add_fact(self, *, detail: str, relevance: int, occurred: OccurredRange, tags: list[str], source_conversation: str | None, now: datetime) -> int:
        with self._session() as session:
            fact = Fact(
                detail=detail,
                relevance=relevance,
                recorded_at=now,
                occurred_start=occurred.start,
                occurred_end=occurred.end,
                occurred_precision=occurred.precision,
                revision=_next_revision(session),
                source_conversation=source_conversation,
            )
            session.add(fact)
            session.flush()
            for tag in dict.fromkeys(tags):
                session.add(FactTag(fact_id=_id(fact), tag=tag))
            _index(session, kind=SearchKind.FACT, key=str(_id(fact)), body=detail)
            return _id(fact)

    def import_fact(self, *, fact_id: int, detail: str, relevance: int, recorded_at: datetime) -> None:
        """A legacy fact, keeping its id; tags and dates arrive when the migration is applied."""
        with self._session() as session:
            session.add(Fact(id=fact_id, detail=detail, relevance=relevance, recorded_at=recorded_at, occurred_precision=Precision.UNKNOWN, revision=_next_revision(session)))
            _index(session, kind=SearchKind.FACT, key=str(fact_id), body=detail)

    def update_fact(self, *, fact_id: int, detail: str | None = None, relevance: int | None = None, occurred: OccurredRange | None = None, tags: list[str] | None = None) -> None:
        with self._session() as session:
            fact = session.get(Fact, fact_id)
            if fact is None:
                raise KeyError(fact_id)
            if detail is not None:
                fact.detail = detail
                if fact.superseded_by is None:
                    _index(session, kind=SearchKind.FACT, key=str(fact_id), body=detail)
            if relevance is not None:
                fact.relevance = relevance
            if occurred is not None:
                fact.occurred_start, fact.occurred_end, fact.occurred_precision = occurred.start, occurred.end, occurred.precision
            if tags is not None:
                session.exec(delete(FactTag).where(col(FactTag.fact_id) == fact_id))
                for tag in dict.fromkeys(tags):
                    session.add(FactTag(fact_id=fact_id, tag=tag))
            fact.revision = _next_revision(session)

    def supersede(self, *, old_id: int, new_id: int) -> None:
        if old_id == new_id:
            raise ValueError("a fact cannot supersede itself")
        with self._session() as session:
            old, new = session.get(Fact, old_id), session.get(Fact, new_id)
            if old is None or new is None:
                raise KeyError(old_id if old is None else new_id)
            old.superseded_by = new_id
            old.revision = _next_revision(session)
            _index(session, kind=SearchKind.FACT, key=str(old_id), body=None)

    def facts_for_tag(self, *, name: str, include_superseded: bool = False) -> list[FactLine]:
        with self._session() as session:
            statement = select(Fact).join(FactTag, col(FactTag.fact_id) == col(Fact.id)).where(FactTag.tag == name)
            if not include_superseded:
                statement = statement.where(col(Fact.superseded_by).is_(None))
            return _fact_lines(session, facts=session.exec(_ranked(statement)).all())

    def facts_between(self, *, start: date, end: date, include_superseded: bool = False) -> list[FactLine]:
        with self._session() as session:
            statement = select(Fact).where(col(Fact.occurred_start) <= end, col(Fact.occurred_end) >= start)
            if not include_superseded:
                statement = statement.where(col(Fact.superseded_by).is_(None))
            return _fact_lines(session, facts=session.exec(_ranked(statement)).all())

    def facts_by_ids(self, *, ids: list[int]) -> list[FactLine]:
        with self._session() as session:
            facts = session.exec(select(Fact).where(col(Fact.id).in_(ids))).all()
            by_id = {line.id: line for line in _fact_lines(session, facts=facts)}
        return [by_id[fact_id] for fact_id in ids if fact_id in by_id]

    def current_facts(self) -> list[FactLine]:
        with self._session() as session:
            return _fact_lines(session, facts=session.exec(_ranked(select(Fact).where(col(Fact.superseded_by).is_(None)))).all())

    def fact_spans(self) -> list[FactSpan]:
        """Current facts that have dates."""
        with self._session() as session:
            statement = select(Fact).where(col(Fact.superseded_by).is_(None), col(Fact.occurred_start).is_not(None))
            return _spans(session, facts=session.exec(statement).all())

    def touched_facts(self, *, above_revision: int) -> list[FactSpan]:
        with self._session() as session:
            return _spans(session, facts=session.exec(select(Fact).where(col(Fact.revision) > above_revision)).all())

    def max_revision(self) -> int:
        with self._session() as session:
            return session.exec(select(func.max(Fact.revision))).one() or 0

    def earliest_year(self) -> int | None:
        with self._session() as session:
            earliest = session.exec(select(func.min(Fact.occurred_start))).one()
        return earliest.year if earliest else None

    def duplicate_candidates(self, *, detail: str) -> list[FactCandidate]:
        query = fts_query(text=detail)
        if query is None:
            return []
        with self._session() as session:
            rows = session.connection().exec_driver_sql(
                f"SELECT key FROM {SEARCH_TABLE} WHERE {SEARCH_TABLE} MATCH ? AND kind = ? ORDER BY rank LIMIT ?",
                (query, SearchKind.FACT.value, _CANDIDATE_LIMIT),
            )
            ids = [int(key) for (key,) in rows]
        return [FactCandidate(id=line.id, detail=line.detail, tags=line.tags) for line in self.facts_by_ids(ids=ids)]

    def co_tags(self, *, name: str) -> Counter[str]:
        """How often each other tag appears on the current facts of this one."""
        return Counter(tag for fact in self.facts_for_tag(name=name) for tag in fact.tags if tag != name)

    def tag_dates(self, *, name: str) -> TagDates:
        with self._session() as session:
            statement = select(func.min(Fact.recorded_at), func.max(Fact.recorded_at), func.max(Fact.occurred_end)).join(FactTag, col(FactTag.fact_id) == col(Fact.id)).where(FactTag.tag == name)
            first, last, latest = session.exec(statement).one()
        return TagDates(first_recorded=_as_datetime(first), last_recorded=_as_datetime(last), latest_occurred=date.fromisoformat(latest) if isinstance(latest, str) else latest)

    # Summaries and periods

    def tag_summary(self, *, name: str) -> TagSummary | None:
        with self._session() as session:
            return session.get(TagSummary, name)

    def set_tag_summary(self, *, name: str, summary: str, now: datetime) -> None:
        with self._session() as session:
            session.merge(TagSummary(tag=name, summary=summary, refreshed_at=now))
            _index(session, kind=SearchKind.TAG_SUMMARY, key=name, body=summary)

    def periods(self) -> list[Period]:
        with self._session() as session:
            return list(session.exec(select(Period).order_by(col(Period.start), col(Period.name))).all())

    def period(self, *, name: str) -> Period | None:
        with self._session() as session:
            return session.get(Period, name)

    def set_period(self, *, bucket: Bucket, summary: str | None, now: datetime) -> None:
        """Create or move a period; a None summary keeps the existing one."""
        with self._session() as session:
            period = session.get(Period, bucket.name)
            if period is None:
                period = Period(name=bucket.name, kind=bucket.kind, start=bucket.start, end=bucket.end)
                session.add(period)
            period.kind, period.start, period.end = bucket.kind, bucket.start, bucket.end
            if summary is not None:
                period.summary, period.refreshed_at = summary, now
            _index(session, kind=SearchKind.PERIOD, key=bucket.name, body=period.summary)

    def delete_period(self, *, name: str) -> None:
        with self._session() as session:
            period = session.get(Period, name)
            if period is not None:
                session.delete(period)
            _index(session, kind=SearchKind.PERIOD, key=name, body=None)

    def refresh_state(self) -> RefreshState:
        with self._session() as session:
            state = session.get(RefreshState, 1)
            if state is None:
                raise RuntimeError("refresh_state row missing")
            return state

    def set_refresh_state(self, *, through_revision: int, calendar_week_start: date, now: datetime) -> None:
        with self._session() as session:
            session.merge(RefreshState(id=1, through_revision=through_revision, refreshed_at=now, calendar_week_start=calendar_week_start))

    def reset_refresh_state(self) -> None:
        """The next summariser run rebuilds every summary."""
        with self._session() as session:
            session.merge(RefreshState(id=1, through_revision=0, refreshed_at=None, calendar_week_start=None))

    # Search

    def search(self, *, query: str, limit: int) -> list[SearchHit]:
        match = fts_query(text=query)
        if match is None:
            return []
        with self._session() as session:
            rows = session.connection().exec_driver_sql(
                f"SELECT kind, key, snippet({SEARCH_TABLE}, 2, '[', ']', '…', 12) FROM {SEARCH_TABLE} WHERE {SEARCH_TABLE} MATCH ? ORDER BY rank LIMIT ?",
                (match, limit),
            )
            return [SearchHit(kind=SearchKind(kind), key=key, snippet=snippet) for kind, key, snippet in rows]
