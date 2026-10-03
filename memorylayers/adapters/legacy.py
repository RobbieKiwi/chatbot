"""The legacy flat memory database, read once for the migration."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from memorylayers.models.migration import LegacyFact
from memorylayers.models.tables import FACT_TABLE


def read_legacy_facts(*, db_path: Path) -> list[LegacyFact]:
    with closing(sqlite3.connect(db_path)) as connection:
        rows = connection.execute("SELECT id, detail, relevance, inserted, tags FROM fact ORDER BY id").fetchall()
    return [LegacyFact(id=fact_id, detail=detail, relevance=relevance, inserted=datetime.fromisoformat(inserted), tags=json.loads(tags)) for fact_id, detail, relevance, inserted, tags in rows]


def stage_legacy_tags(*, db_path: Path, facts: list[LegacyFact]) -> None:
    """Keep each fact's old tags beside it until the proposal is applied."""
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute(f"ALTER TABLE {FACT_TABLE} ADD COLUMN staged_tags TEXT")
        connection.executemany(f"UPDATE {FACT_TABLE} SET staged_tags = ? WHERE id = ?", [(json.dumps(fact.tags), fact.id) for fact in facts])


def drop_staged_tags(*, db_path: Path) -> None:
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute(f"ALTER TABLE {FACT_TABLE} DROP COLUMN staged_tags")
