"""Propose how a legacy flat memory (data/<parent>.db and data/<parent>.md) moves into layered memory. Run: uv run python -m memorylayers.scripts.migrate_propose"""

import shutil
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from memorylayers.adapters.legacy import read_legacy_facts, stage_legacy_tags
from memorylayers.adapters.paths import PROJECT_ROOT, data_root, parent_paths
from memorylayers.adapters.processes import find_claude, run_claude
from memorylayers.adapters.prompts import load_memory_guide, load_prompt
from memorylayers.adapters.state_files import write_model
from memorylayers.adapters.store import MemoryStore
from memorylayers.domain.migration_report import build_migration_brief, parse_proposal, render_report, validate_proposal
from memorylayers.models.config import MemoryConfig
from persona.adapters.files import load_names
from persona.models import PersonaError


def propose(*, parent: str, now: datetime) -> None:
    paths = parent_paths(parent=parent)
    legacy_db, legacy_summary = data_root() / f"{parent}.db", data_root() / f"{parent}.md"
    if paths.db.exists():
        raise SystemExit(f"{paths.db} already exists; delete it to migrate again")
    missing = [str(source) for source in (legacy_db, legacy_summary) if not source.exists()]
    if missing:
        raise SystemExit(f"nothing to migrate: the legacy memory needs {' and '.join(missing)}")
    try:
        names = load_names()
    except PersonaError as error:
        raise SystemExit(str(error)) from None
    backup = data_root() / "backups" / f"{now:%Y%m%d-%H%M%S}"
    backup.mkdir(parents=True)
    for source in (legacy_db, legacy_summary):
        shutil.copy2(source, backup / source.name)
    config = MemoryConfig()
    write_model(path=paths.config, value=config)
    tz = ZoneInfo(config.local_timezone)

    facts = read_legacy_facts(db_path=legacy_db)
    with MemoryStore(db_path=paths.db) as store:
        for fact in facts:
            # Legacy times are naive local time in the configured timezone.
            store.import_fact(fact_id=fact.id, detail=fact.detail, relevance=max(1, fact.relevance), recorded_at=fact.inserted.replace(tzinfo=tz).astimezone(UTC))
    stage_legacy_tags(db_path=paths.db, facts=facts)
    print(f"Copied {len(facts)} facts into {paths.db}; backups in {backup}")

    claude = find_claude(executable=config.claude_executable)
    if claude is None:
        raise SystemExit(f"{config.claude_executable!r} not found on PATH")
    paths.logs.mkdir(parents=True, exist_ok=True)
    brief_path, log_path = paths.logs / "migration.brief.md", paths.logs / "migration.log"
    log_path.unlink(missing_ok=True)
    brief_path.write_text(
        build_migration_brief(
            template=load_prompt(name="migrate"), now_local=now.astimezone(tz), facts=facts, old_summary=legacy_summary.read_text(encoding="utf-8"), guide=load_memory_guide(paths=paths), names=names
        ),
        encoding="utf-8",
    )
    print("Asking the migration worker for a proposal; this takes a few minutes…")
    run_claude(claude=claude, model=config.summariser_model, allowed_tools=[], brief_path=brief_path, log_path=log_path, timeout_s=3600, cwd=PROJECT_ROOT)
    proposal = parse_proposal(output=log_path.read_text(encoding="utf-8"))
    errors = validate_proposal(proposal=proposal, fact_ids={fact.id for fact in facts})
    proposal_path, report_path = paths.root / "migration-proposal.json", paths.root / "migration-report.md"
    write_model(path=proposal_path, value=proposal)
    report_path.write_text(render_report(proposal=proposal, facts=facts, errors=errors), encoding="utf-8")
    print(f"Review {report_path} and edit {proposal_path} if needed, then run: uv run python -m memorylayers.scripts.migrate_apply")
    if errors:
        print(f"{len(errors)} problems must be fixed first; they are listed at the top of the report.")


if __name__ == "__main__":
    propose(parent="chatbot", now=datetime.now(UTC))
