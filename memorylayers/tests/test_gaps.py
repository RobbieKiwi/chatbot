import json
import sqlite3
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest

from memorylayers.adapters.store import MemoryStore
from memorylayers.domain.curiosity import available_gaps
from memorylayers.models.paths import ParentPaths
from memorylayers.models.views import GapLine, NewGap, NewTag
from memorylayers.models.vocab import TagKind
from memorylayers.tests.conftest import NOW

Cli = Callable[[list[str]], tuple[int, str, str]]


def _tags(store: MemoryStore) -> None:
    store.create_tag(new=NewTag(name="acme", kind=TagKind.ENTITY, description="employer"), now=NOW)
    store.create_tag(new=NewTag(name="lisbon", kind=TagKind.ENTITY, description="city"), now=NOW)
    store.add_alias(alias="acme_corp", tag="acme")


def test_replace_gaps_keeps_a_tags_cooldown(store: MemoryStore, tmp_path: Path) -> None:
    _tags(store)
    store.replace_gaps(gaps=[NewGap(tag="acme", text="old wording")], now=NOW)
    shown = NOW + timedelta(days=1)
    with sqlite3.connect(tmp_path / "memory.db") as connection:  # the hook stamps showings through sqlite3 too
        connection.execute("UPDATE gap SET last_shown_at = ?", (shown.isoformat(),))
    store.replace_gaps(gaps=[NewGap(tag="acme", text="new wording"), NewGap(tag="lisbon", text="never described")], now=NOW + timedelta(days=2))
    assert [(gap.tag, gap.text, gap.last_shown_at) for gap in store.gaps()] == [("acme", "new wording", shown), ("lisbon", "never described", None)]


def test_available_gaps_respect_the_cooldown() -> None:
    gaps = [
        GapLine(id=1, tag="a", text="never shown", last_shown_at=None),
        GapLine(id=2, tag="b", text="shown long ago", last_shown_at=NOW - timedelta(days=15)),
        GapLine(id=3, tag="c", text="shown lately", last_shown_at=NOW - timedelta(days=3)),
    ]
    assert [gap.id for gap in available_gaps(gaps=gaps, now=NOW, cooldown_days=14)] == [1, 2]


def test_gaps_set_and_list(paths: ParentPaths, run_cli: Cli) -> None:
    with MemoryStore(db_path=paths.db) as store:
        _tags(store)
    payload = json.dumps([{"tag": "Acme Corp", "text": "His days at Acme are a blank."}, {"tag": "lisbon", "text": "Lisbon is named but never described."}])
    assert run_cli(["gaps", "set", "--json", payload])[:2] == (0, "gaps set: 2\n")
    code, out, _ = run_cli(["gaps", "list"])
    assert (code, out) == (0, "acme: His days at Acme are a blank.\nlisbon: Lisbon is named but never described.\n")
    assert run_cli(["gaps", "list", "--available"])[1].count("\n") == 2


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ('[{"tag": "nobody", "text": "x"}]', "unknown tags: nobody"),
        ('[{"tag": "lisbon"}]', "invalid gaps"),
        ("not json", "invalid gaps"),
        (json.dumps([{"tag": "lisbon", "text": f"gap {index}"} for index in range(11)]), "at most 10 gaps"),
        ('[{"tag": "!!", "text": "x"}]', "unknown tags: !!"),
    ],
)
def test_gaps_set_rejects_bad_lists(paths: ParentPaths, run_cli: Cli, payload: str, message: str) -> None:
    with MemoryStore(db_path=paths.db) as store:
        _tags(store)
    code, _, err = run_cli(["gaps", "set", "--json", payload])
    assert code == 2
    assert message in err


def test_an_empty_list_prints_nothing(paths: ParentPaths, run_cli: Cli) -> None:
    assert run_cli(["gaps", "list", "--available"])[:2] == (0, "")
