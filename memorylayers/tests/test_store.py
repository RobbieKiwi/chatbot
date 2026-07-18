from datetime import UTC, date

import pytest

from memorylayers.adapters.store import MemoryStore
from memorylayers.models.dates import Bucket
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import PeriodKind, SearchKind, TagKind
from memorylayers.tests.conftest import NOW
from memorylayers.tools.occurred import TIMELESS, parse_occurred


def _seed(store: MemoryStore) -> None:
    store.create_tag(new=NewTag(name="friend", kind=TagKind.CATEGORY, description="Alex's friends"), now=NOW)
    store.create_tag(new=NewTag(name="jordan", kind=TagKind.ENTITY, description="tango friend"), now=NOW)


def test_facts_come_back_by_relevance(store: MemoryStore) -> None:
    _seed(store)
    low = store.add_fact(detail="Jordan likes tea", relevance=3, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
    high = store.add_fact(detail="Jordan is a close friend", relevance=8, occurred=TIMELESS, tags=["jordan", "friend"], source_conversation="c1", now=NOW)
    facts = store.facts_for_tag(name="jordan")
    assert [fact.id for fact in facts] == [high, low]
    assert facts[0].tags == ["friend", "jordan"]
    assert facts[0].occurred == "timeless"


def test_every_write_bumps_the_revision(store: MemoryStore) -> None:
    _seed(store)
    first = store.add_fact(detail="Jordan dances", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
    second = store.add_fact(detail="Jordan dances tango", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
    assert store.max_revision() == 2
    store.update_fact(fact_id=first, relevance=6)
    store.supersede(old_id=first, new_id=second)
    assert store.max_revision() == 4
    assert {span.id for span in store.touched_facts(above_revision=2)} == {first}


def test_superseded_facts_leave_default_reads_and_search(store: MemoryStore) -> None:
    _seed(store)
    old = store.add_fact(detail="Jordan lives in Pankow", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
    new = store.add_fact(detail="Jordan lives in Bonn", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
    store.supersede(old_id=old, new_id=new)
    assert [fact.id for fact in store.facts_for_tag(name="jordan")] == [new]
    history = store.facts_for_tag(name="jordan", include_superseded=True)
    assert {fact.id: fact.superseded_by for fact in history} == {new: None, old: new}
    assert [hit.key for hit in store.search(query="Pankow", limit=5)] == []


def test_merge_moves_facts_and_leaves_an_alias(store: MemoryStore) -> None:
    _seed(store)
    store.create_tag(new=NewTag(name="friends", kind=TagKind.CATEGORY, description="dup"), now=NOW)
    fact_id = store.add_fact(detail="Beatrix annoys Alex", relevance=4, occurred=TIMELESS, tags=["friends"], source_conversation=None, now=NOW)
    assert store.merge_tag(source="friends", target="friend") == 1
    assert store.tag(name="friends") is None
    assert store.vocabulary().aliases == {"friends": "friend"}
    assert [fact.id for fact in store.facts_for_tag(name="friend")] == [fact_id]


def test_search_spans_layers(store: MemoryStore) -> None:
    _seed(store)
    store.add_fact(detail="Went dancing tango with Jordan", relevance=6, occurred=parse_occurred(text="2026-10-01"), tags=["jordan"], source_conversation=None, now=NOW)
    store.set_tag_summary(name="friend", summary="Friends met through tango", now=NOW)
    kinds = {hit.kind for hit in store.search(query="tango", limit=10)}
    assert kinds == {SearchKind.FACT, SearchKind.TAG, SearchKind.TAG_SUMMARY}


def test_duplicate_candidates_come_from_full_text_search(store: MemoryStore) -> None:
    _seed(store)
    fact_id = store.add_fact(detail="Jordan teaches tango on Tuesdays", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
    candidates = store.duplicate_candidates(detail="Jordan gives tango lessons")
    assert [candidate.id for candidate in candidates] == [fact_id]
    assert candidates[0].tags == ["jordan"]


def test_periods_and_refresh_state(store: MemoryStore) -> None:
    bucket = Bucket(name="2026 Q3", kind=PeriodKind.QUARTER, start=date(2026, 7, 1), end=date(2026, 9, 30))
    store.set_period(bucket=bucket, summary="A summer of tango", now=NOW)
    store.set_period(bucket=bucket, summary=None, now=NOW)
    period = store.period(name="2026 Q3")
    assert period is not None and period.summary == "A summer of tango"
    store.set_refresh_state(through_revision=7, calendar_week_start=date(2026, 9, 28), now=NOW)
    state = store.refresh_state()
    assert (state.through_revision, state.calendar_week_start) == (7, date(2026, 9, 28))
    assert state.refreshed_at is not None and state.refreshed_at.tzinfo is not None


def test_recorded_at_stays_timezone_aware(store: MemoryStore) -> None:
    _seed(store)
    store.add_fact(detail="x y", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
    assert store.tag_dates(name="jordan").first_recorded == NOW.astimezone(UTC)


def test_naive_datetimes_are_refused(store: MemoryStore) -> None:
    with pytest.raises(Exception, match="naive"):
        store.create_tag(new=NewTag(name="x", kind=TagKind.CATEGORY, description="x"), now=NOW.replace(tzinfo=None))
