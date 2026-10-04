"""Read-only memory queries for the hook, in stdlib sqlite3 so it starts fast."""

import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

from memorylayers.models.tables import FACT_TABLE, FACT_TAG_TABLE, GAP_TABLE, PERIOD_TABLE, REFRESH_STATE_TABLE, SEARCH_TABLE, TAG_ALIAS_TABLE, TAG_SUMMARY_TABLE, TAG_TABLE
from memorylayers.models.views import GapLine, HintIndex, RefreshStatus, TagLine
from memorylayers.models.vocab import PeriodKind, SearchKind, TagKind
from memorylayers.tools.text import fts_query

_TAGS = f"""
    SELECT t.name, t.kind, t.description,
           (SELECT COUNT(*) FROM {FACT_TAG_TABLE} ft JOIN {FACT_TABLE} f ON f.id = ft.fact_id
            WHERE ft.tag = t.name AND f.superseded_by IS NULL),
           EXISTS (SELECT 1 FROM {TAG_SUMMARY_TABLE} s WHERE s.tag = t.name)
    FROM {TAG_TABLE} t ORDER BY t.name
"""
_SUMMARY_HITS = f"SELECT key FROM {SEARCH_TABLE} WHERE {SEARCH_TABLE} MATCH ? AND kind IN (?, ?) ORDER BY rank LIMIT 3"


def _connect(*, db_path: Path) -> sqlite3.Connection | None:
    return sqlite3.connect(db_path, timeout=1.0) if db_path.exists() else None


def read_hint_index(*, db_path: Path, message: str) -> HintIndex:
    connection = _connect(db_path=db_path)
    if connection is None:
        return HintIndex()
    with closing(connection):
        tags = [
            TagLine(name=name, kind=TagKind(kind), description=description, fact_count=count, has_summary=bool(summarised)) for name, kind, description, count, summarised in connection.execute(_TAGS)
        ]
        aliases = dict(connection.execute(f"SELECT alias, tag FROM {TAG_ALIAS_TABLE}").fetchall())
        periods = connection.execute(f"SELECT name, kind FROM {PERIOD_TABLE} ORDER BY start").fetchall()
        query = fts_query(text=message)
        hits = [key for (key,) in connection.execute(_SUMMARY_HITS, (query, SearchKind.TAG_SUMMARY.value, SearchKind.PERIOD.value))] if query else []
    return HintIndex(
        tags=tags,
        aliases=aliases,
        period_names=[name for name, kind in periods if kind != PeriodKind.ERA.value],
        era_names=[name for name, kind in periods if kind == PeriodKind.ERA.value],
        summary_hits=hits,
    )


def read_refresh_status(*, db_path: Path) -> RefreshStatus:
    connection = _connect(db_path=db_path)
    if connection is None:
        return RefreshStatus(facts_since_refresh=0, fact_count=0, calendar_week_start=None)
    with closing(connection):
        row = connection.execute(f"SELECT through_revision, calendar_week_start FROM {REFRESH_STATE_TABLE} WHERE id = 1").fetchone()
        through, week = row if row else (0, None)
        since = connection.execute(f"SELECT COUNT(*) FROM {FACT_TABLE} WHERE revision > ?", (through,)).fetchone()[0]
        count = connection.execute(f"SELECT COUNT(*) FROM {FACT_TABLE} WHERE superseded_by IS NULL").fetchone()[0]
    return RefreshStatus(facts_since_refresh=since, fact_count=count, calendar_week_start=date.fromisoformat(week) if week else None)


def read_gaps(*, db_path: Path) -> list[GapLine]:
    connection = _connect(db_path=db_path)
    if connection is None:
        return []
    with closing(connection):
        try:
            rows = connection.execute(f"SELECT id, tag, text, last_shown_at FROM {GAP_TABLE} ORDER BY id").fetchall()
        except sqlite3.OperationalError:  # a database from before gaps; the next CLI run creates the table
            return []
    return [GapLine(id=gap_id, tag=tag, text=text, last_shown_at=datetime.fromisoformat(shown) if shown else None) for gap_id, tag, text, shown in rows]


def stamp_gap(*, db_path: Path, gap_id: int, now: datetime) -> bool:
    connection = _connect(db_path=db_path)
    if connection is None:
        return False
    try:
        with closing(connection), connection:
            connection.execute(f"UPDATE {GAP_TABLE} SET last_shown_at = ? WHERE id = ?", (now.astimezone(UTC).isoformat(), gap_id))
    except sqlite3.OperationalError:  # no gap table, or the database stayed locked past the timeout
        return False
    return True
