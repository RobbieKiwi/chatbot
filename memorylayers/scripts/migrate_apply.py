"""Apply the reviewed migration proposal, then rebuild every summary. Run: uv run python -m memorylayers.scripts.migrate_apply"""

import subprocess
from datetime import UTC, datetime

from memorylayers.adapters.legacy import drop_staged_tags
from memorylayers.adapters.paths import PROJECT_ROOT, parent_paths
from memorylayers.adapters.processes import runner_command
from memorylayers.adapters.state_files import read_model
from memorylayers.adapters.store import MemoryStore
from memorylayers.domain.migration_report import validate_proposal
from memorylayers.models.dates import ONGOING_END, Bucket
from memorylayers.models.migration import MigrationProposal
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import PeriodKind, TagKind, WorkerKind
from memorylayers.tools.occurred import TIMELESS, parse_occurred
from memorylayers.tools.tags import canonical_form, resolve_known, singular_form

REBUILD_MINUTES = 120


def apply_proposal(*, store: MemoryStore, proposal: MigrationProposal, now: datetime) -> None:
    for category in proposal.categories:
        store.create_tag(new=NewTag(name=singular_form(name=canonical_form(name=category.name)), kind=TagKind.CATEGORY, description=category.description), now=now)
    for entity in proposal.entities:
        name = canonical_form(name=entity.name)
        store.create_tag(new=NewTag(name=name, kind=TagKind.ENTITY, description=entity.profile), now=now)
        for alias in entity.aliases:
            store.add_alias(alias=canonical_form(name=alias), tag=name)
    for alias, category in proposal.category_aliases.items():
        store.add_alias(alias=canonical_form(name=alias), tag=singular_form(name=canonical_form(name=category)))
    vocabulary = store.vocabulary()
    for fact in proposal.facts:
        tags = [name for tag in fact.tags if (name := resolve_known(name=tag, vocabulary=vocabulary)) is not None]
        occurred = TIMELESS if fact.occurred == "timeless" else parse_occurred(text=fact.occurred)
        store.update_fact(fact_id=fact.id, occurred=occurred, tags=tags)
    for link in proposal.supersessions:
        store.supersede(old_id=link.old_id, new_id=link.new_id)
    for era in proposal.eras:
        start = parse_occurred(text=era.start).start
        end = parse_occurred(text=era.end).end if era.end else ONGOING_END
        assert start is not None and end is not None
        store.set_period(bucket=Bucket(name=era.name, kind=PeriodKind.ERA, start=start, end=end), summary="", now=now)


def apply(*, parent: str, now: datetime) -> None:
    paths = parent_paths(parent=parent)
    proposal = read_model(path=paths.root / "migration-proposal.json", model=MigrationProposal)
    if proposal is None:
        raise SystemExit("no migration-proposal.json; run migrate_propose first")
    if not paths.db.exists():
        raise SystemExit(f"no {paths.db}; run migrate_propose first")
    with MemoryStore(db_path=paths.db) as store:
        errors = validate_proposal(proposal=proposal, fact_ids={fact.id for fact in store.current_facts()})
        if errors:
            raise SystemExit("Fix these in migration-proposal.json first:\n" + "\n".join(errors))
        apply_proposal(store=store, proposal=proposal, now=now)
        store.reset_refresh_state()
    drop_staged_tags(db_path=paths.db)
    print("Proposal applied. Rebuilding every summary; this can take a while…")
    subprocess.run([*runner_command(parent=parent, kind=WorkerKind.SUMMARISER), "--timeout-minutes", str(REBUILD_MINUTES)], cwd=PROJECT_ROOT, check=False)
    print(f"Done. Check: .venv/Scripts/python -m memorylayers status --parent {parent}")


if __name__ == "__main__":
    apply(parent="chatbot", now=datetime.now(UTC))
