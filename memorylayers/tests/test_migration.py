import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from memorylayers.adapters.legacy import drop_staged_tags, read_legacy_facts, stage_legacy_tags
from memorylayers.adapters.paths import data_root
from memorylayers.adapters.prompts import load_prompt
from memorylayers.adapters.state_files import write_model
from memorylayers.adapters.store import MemoryStore
from memorylayers.domain.migration_report import build_migration_brief, parse_proposal, render_report, validate_proposal
from memorylayers.models.migration import MigrationProposal, ProposedCategory, ProposedEntity, ProposedEra, ProposedFact, ProposedSupersession
from memorylayers.models.paths import ParentPaths
from memorylayers.scripts.migrate_apply import apply, apply_proposal
from memorylayers.scripts.migrate_propose import propose
from persona.models import PersonaNames

NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)
PROPOSAL = MigrationProposal(
    categories=[ProposedCategory(name="friends", description="Alex's friends")],
    entities=[ProposedEntity(name="Jordan", profile="tango friend", aliases=["jordy"])],
    category_aliases={"social": "friend"},
    facts=[ProposedFact(id=1, tags=["jordan", "social"], occurred="timeless"), ProposedFact(id=2, tags=["jordy"], occurred="2026-07")],
    supersessions=[ProposedSupersession(old_id=1, new_id=2)],
    eras=[ProposedEra(name="Germany", start="2020", end=None)],
)


def _legacy_db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE fact (id INTEGER PRIMARY KEY, tags JSON NOT NULL, inserted DATETIME NOT NULL, detail VARCHAR NOT NULL, relevance INTEGER NOT NULL DEFAULT 5)")
        connection.execute("INSERT INTO fact VALUES (1, '[\"social\", \"jordan\"]', '2026-07-18 17:48:18.932785', 'Jordan is a friend', 8)")
        connection.execute("INSERT INTO fact VALUES (2, '[\"jordan\"]', '2026-07-19 09:00:00', 'Jordan is a close friend', 0)")


def test_legacy_facts_are_read_and_staged(tmp_path: Path) -> None:
    legacy = tmp_path / "old.db"
    _legacy_db(legacy)
    facts = read_legacy_facts(db_path=legacy)
    assert [(fact.id, fact.tags, fact.relevance) for fact in facts] == [(1, ["social", "jordan"], 8), (2, ["jordan"], 0)]
    db = tmp_path / "memory.db"
    with MemoryStore(db_path=db) as store:
        store.import_fact(fact_id=1, detail="Jordan is a friend", relevance=8, recorded_at=NOW)
    stage_legacy_tags(db_path=db, facts=facts[:1])
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT staged_tags FROM fact").fetchone() == ('["social", "jordan"]',)
    drop_staged_tags(db_path=db)
    with sqlite3.connect(db) as connection:
        assert "staged_tags" not in [row[1] for row in connection.execute("PRAGMA table_info(fact)")]


def test_parse_proposal_ignores_surrounding_noise() -> None:
    assert parse_proposal(output="Here you go:\n" + PROPOSAL.model_dump_json() + "\nDone.") == PROPOSAL


def test_validation_catches_unknown_tags_missing_facts_and_bad_dates() -> None:
    broken = PROPOSAL.model_copy(update={"facts": [ProposedFact(id=1, tags=["nobody"], occurred="last summer")]})
    errors = validate_proposal(proposal=broken, fact_ids={1, 2})
    assert any("nobody" in error for error in errors)
    assert any("last summer" in error for error in errors)
    assert any("fact #2" in error for error in errors)
    assert validate_proposal(proposal=PROPOSAL, fact_ids={1, 2}) == []


def test_validation_rejects_an_alias_that_shadows_a_tag() -> None:
    shadowing = PROPOSAL.model_copy(update={"category_aliases": {"social": "friend", "Jordan": "friend"}})
    errors = validate_proposal(proposal=shadowing, fact_ids={1, 2})
    assert errors == ["alias 'Jordan' is already a category or entity name; drop it"]


def test_apply_files_every_fact(tmp_path: Path) -> None:
    with MemoryStore(db_path=tmp_path / "memory.db") as store:
        store.import_fact(fact_id=1, detail="Jordan is a friend", relevance=8, recorded_at=NOW)
        store.import_fact(fact_id=2, detail="Jordan is a close friend", relevance=1, recorded_at=NOW)
        apply_proposal(store=store, proposal=PROPOSAL, now=NOW)
        assert [fact.id for fact in store.facts_for_tag(name="jordan")] == [2]
        assert store.facts_for_tag(name="friend", include_superseded=True)[0].tags == ["friend", "jordan"]
        assert store.vocabulary().aliases == {"jordy": "jordan", "social": "friend"}
        assert store.period(name="Germany") is not None


def test_report_lists_each_fact() -> None:
    report = render_report(proposal=PROPOSAL, facts=[], errors=["fact #9: example"])
    assert "fact #9: example" in report
    assert "| 2 |" in report and "2026-07" in report


def test_the_migration_brief_names_the_user() -> None:
    brief = build_migration_brief(template=load_prompt(name="migrate"), now_local=NOW, facts=[], old_summary="", guide="GUIDE", names=PersonaNames(assistant_name="Nova", user_name="Alex"))
    assert brief.startswith("You are migrating a flat memory of Alex into a layered memory.") and "$" not in brief


def test_propose_without_the_legacy_memory_says_what_is_missing(paths: ParentPaths) -> None:
    with pytest.raises(SystemExit) as stop:
        propose(parent="pk", now=NOW)
    message = str(stop.value)
    assert "pk.db" in message and "pk.md" in message and "nothing to migrate" in message
    assert not paths.db.exists() and not (data_root() / "backups").exists()


def test_apply_without_a_proposal_says_to_propose_first(paths: ParentPaths) -> None:
    with pytest.raises(SystemExit, match="run migrate_propose first"):
        apply(parent="pk", now=NOW)
    assert not paths.db.exists()


def test_apply_without_the_migrated_store_says_to_propose_first(paths: ParentPaths) -> None:
    write_model(path=paths.root / "migration-proposal.json", value=PROPOSAL)
    with pytest.raises(SystemExit, match="memory.db"):
        apply(parent="pk", now=NOW)
    assert not paths.db.exists()


def test_propose_with_a_broken_persona_names_the_file(paths: ParentPaths, broken_persona: Path) -> None:
    data_root().mkdir(parents=True)
    _legacy_db(data_root() / "pk.db")
    (data_root() / "pk.md").write_text("old summary", encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        propose(parent="pk", now=NOW)
    assert str(broken_persona) in str(stop.value)
    assert not paths.db.exists() and not (data_root() / "backups").exists()
