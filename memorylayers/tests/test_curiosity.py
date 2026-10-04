import random
import sqlite3
from datetime import timedelta
from pathlib import Path

from memorylayers.adapters.hook_store import read_gaps, stamp_gap
from memorylayers.adapters.store import MemoryStore
from memorylayers.domain.curiosity import curiosity_fires, pick_gap, render_curiosity
from memorylayers.models.views import GapLine, NewGap, NewTag
from memorylayers.models.vocab import TagKind
from memorylayers.tests.conftest import NOW


class _AlwaysFires(random.Random):
    def random(self) -> float:
        return 0.0


def test_the_dice_skip_the_first_messages() -> None:
    always = _AlwaysFires(0)
    assert [curiosity_fires(messages_seen=seen, skip_turns=3, every_turns=8, rng=always) for seen in range(1, 6)] == [False, False, False, True, True]


def test_the_dice_fire_about_once_in_every_turns() -> None:
    rng = random.Random(1)
    fired = sum(curiosity_fires(messages_seen=10, skip_turns=3, every_turns=8, rng=rng) for _ in range(8000))
    assert 850 < fired < 1150


def test_pick_and_render() -> None:
    gap = GapLine(id=1, tag="acme", text="Alex works at Acme, but nothing is known about what his days there are like.", last_shown_at=None)
    assert pick_gap(gaps=[], rng=random.Random(0)) is None
    assert pick_gap(gaps=[gap], rng=random.Random(0)) == gap
    assert render_curiosity(gap=gap) == '<curiosity tag="acme">Alex works at Acme, but nothing is known about what his days there are like.</curiosity>'


def test_read_and_stamp_through_sqlite(tmp_path: Path) -> None:
    db = tmp_path / "memory.db"
    with MemoryStore(db_path=db) as store:
        store.create_tag(new=NewTag(name="lisbon", kind=TagKind.ENTITY, description="city"), now=NOW)
        store.replace_gaps(gaps=[NewGap(tag="lisbon", text="never described")], now=NOW)
    [gap] = read_gaps(db_path=db)
    assert stamp_gap(db_path=db, gap_id=gap.id, now=NOW + timedelta(hours=1))
    with MemoryStore(db_path=db) as store:
        assert store.gaps()[0].last_shown_at == NOW + timedelta(hours=1)


def test_a_database_from_before_gaps_has_none(tmp_path: Path) -> None:
    db = tmp_path / "old.db"
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE fact (id INTEGER PRIMARY KEY)")
    assert read_gaps(db_path=db) == []
    assert not stamp_gap(db_path=db, gap_id=1, now=NOW)
    assert read_gaps(db_path=tmp_path / "missing.db") == []
