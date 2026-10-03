from pathlib import Path

from memorylayers.adapters.hook_store import read_hint_index, read_refresh_status
from memorylayers.adapters.store import MemoryStore
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import TagKind
from memorylayers.tests.conftest import NOW
from memorylayers.tools.calendar import parse_bucket_name
from memorylayers.tools.occurred import TIMELESS


def test_the_hook_reads_what_the_store_wrote(tmp_path: Path) -> None:
    db = tmp_path / "memory.db"
    with MemoryStore(db_path=db) as store:
        store.create_tag(new=NewTag(name="jordan", kind=TagKind.ENTITY, description="tango friend"), now=NOW)
        store.add_alias(alias="jordy", tag="jordan")
        store.add_fact(detail="Jordan dances", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
        store.set_tag_summary(name="jordan", summary="A tango friend from Blue Note", now=NOW)
        bucket = parse_bucket_name(name="2026 Q3")
        assert bucket is not None
        store.set_period(bucket=bucket, summary="Summer", now=NOW)
    index = read_hint_index(db_path=db, message="what about blue note?")
    assert [(tag.name, tag.kind, tag.fact_count, tag.has_summary) for tag in index.tags] == [("jordan", TagKind.ENTITY, 1, True)]
    assert index.aliases == {"jordy": "jordan"}
    assert index.period_names == ["2026 Q3"]
    assert index.summary_hits == ["jordan"]
    status = read_refresh_status(db_path=db)
    assert (status.facts_since_refresh, status.fact_count, status.calendar_week_start) == (1, 1, None)


def test_a_missing_database_reads_as_empty(tmp_path: Path) -> None:
    assert read_hint_index(db_path=tmp_path / "none.db", message="x").tags == []
    assert read_refresh_status(db_path=tmp_path / "none.db").fact_count == 0
