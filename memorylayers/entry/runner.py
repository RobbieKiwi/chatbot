"""Run one kind of headless worker to completion: take the lock, write the brief, run claude, account for the outcome."""

import argparse
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from memorylayers.adapters.locks import read_lock, remove_lock, try_create_lock, write_lock
from memorylayers.adapters.paths import PROJECT_ROOT, parent_paths
from memorylayers.adapters.processes import find_claude, pid_alive, run_claude
from memorylayers.adapters.prompts import load_memory_guide, load_prompt
from memorylayers.adapters.state_files import list_conversations, load_config, load_conversation, load_summariser_health, update_conversation, update_summariser_health
from memorylayers.adapters.store import MemoryStore
from memorylayers.adapters.transcripts import read_conversation_turns
from memorylayers.domain.briefs import build_consolidator_brief, build_scribe_brief, build_summariser_brief
from memorylayers.domain.due import lock_status, record_failure
from memorylayers.domain.permissions import allowed_tools
from memorylayers.domain.window import select_window, unprocessed_chars
from memorylayers.entry.common import use_utf8_streams
from memorylayers.entry.planning import period_sections, plan_for, tag_sections
from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import ConversationState
from memorylayers.models.paths import ParentPaths
from memorylayers.models.vocab import PeriodKind, WorkerKind
from memorylayers.models.worker import LockStatus, RunRecord
from persona.adapters.files import load_names
from persona.models import PersonaError

MAX_WINDOWS = 10  # per scribe launch, so a long backlog cannot run unbounded

Clock = Callable[[], datetime]


class ClaudeCall(Protocol):
    def __call__(self, *, model: str, allowed_tools: list[str], brief_path: Path, log_path: Path, timeout_s: float) -> int: ...


def account_failure(*, paths: ParentPaths, config: MemoryConfig, record: RunRecord, reason: str) -> None:
    limit = config.max_consecutive_failures
    if record.kind is WorkerKind.SCRIBE and record.conversation_id:
        update_conversation(paths=paths, conversation_id=record.conversation_id, change=lambda state: record_failure(health=state.scribe_health, limit=limit, reason=reason))
    elif record.kind is WorkerKind.SUMMARISER:
        update_summariser_health(paths=paths, change=lambda health: record_failure(health=health, limit=limit, reason=reason))


def acquire(*, paths: ParentPaths, config: MemoryConfig, kind: WorkerKind, now: datetime, timeout_minutes: int, conversation_id: str | None = None) -> RunRecord | None:
    """Take the kind's lock, breaking an abandoned one. None when another run is live."""
    record = RunRecord(
        run_id=f"{kind.value}-{now:%Y%m%d-%H%M%S}-{os.getpid()}",
        kind=kind,
        pid=os.getpid(),
        started_at=now,
        deadline=now + timedelta(minutes=timeout_minutes + 1),
        conversation_id=conversation_id,
    )
    for _ in range(2):
        if try_create_lock(paths=paths, record=record):
            return record
        existing = read_lock(paths=paths, kind=kind)
        if existing is None:
            return None  # another runner is writing its lock this instant
        if lock_status(record=existing, alive=pid_alive(pid=existing.pid), now=now) is LockStatus.LIVE:
            return None
        if not existing.committed:
            account_failure(paths=paths, config=config, record=existing, reason=f"run {existing.run_id} was abandoned without committing")
        remove_lock(paths=paths, kind=kind)
    return None


def _call(*, call_claude: ClaudeCall, paths: ParentPaths, record: RunRecord, model: str, brief: str, timeout_s: float) -> None:
    paths.logs.mkdir(parents=True, exist_ok=True)
    brief_path = paths.logs / f"{record.run_id}.brief.md"
    brief_path.write_text(brief, encoding="utf-8")
    try:
        call_claude(model=model, allowed_tools=allowed_tools(kind=record.kind), brief_path=brief_path, log_path=paths.logs / f"{record.run_id}.log", timeout_s=timeout_s)
    except subprocess.TimeoutExpired:
        pass  # an overrun is a run that did not commit


def _finish(*, paths: ParentPaths, config: MemoryConfig, record: RunRecord) -> bool:
    finished = read_lock(paths=paths, kind=record.kind)
    committed = finished is not None and finished.run_id == record.run_id and finished.committed
    if not committed:
        account_failure(paths=paths, config=config, record=record, reason=f"run {record.run_id} ended without committing; see logs/{record.run_id}.log")
    remove_lock(paths=paths, kind=record.kind)
    return committed


def run_scribe(*, paths: ParentPaths, config: MemoryConfig, conversation_id: str, catch_up: bool, call_claude: ClaudeCall, now: Clock) -> None:
    tz = ZoneInfo(config.local_timezone)
    names = load_names()
    for _ in range(MAX_WINDOWS):
        state = load_conversation(paths=paths, conversation_id=conversation_id)
        if state.scribe_health.stopped_reason:
            return
        turns = read_conversation_turns(state=state, tz=tz)
        if not turns.unprocessed:
            update_conversation(paths=paths, conversation_id=conversation_id, change=lambda conversation: _advance(conversation=conversation, ends=turns.ends))
            return
        if not catch_up and unprocessed_chars(turns=turns.unprocessed) < config.scribe_threshold_chars:
            return
        record = acquire(paths=paths, config=config, kind=WorkerKind.SCRIBE, now=now(), timeout_minutes=config.stale_lock_minutes, conversation_id=conversation_id)
        if record is None:
            return
        window = select_window(turns=turns, threshold_chars=config.scribe_threshold_chars, overlap_fraction=config.overlap_fraction)
        record = record.model_copy(update={"window_end": window.end, "pending_at_start": [note.number for note in state.pending_notes]})
        write_lock(paths=paths, record=record)
        with MemoryStore(db_path=paths.db) as store:
            ledger, tags = store.facts_by_ids(ids=state.ledger), store.tag_lines()
        brief = build_scribe_brief(
            template=load_prompt(name="scribe"),
            parent=paths.parent,
            run_id=record.run_id,
            conversation_id=conversation_id,
            now_local=now().astimezone(tz),
            window=window,
            rolling_summary=state.rolling_summary,
            ledger=ledger,
            pending=state.pending_notes,
            tags=tags,
            guide=load_memory_guide(paths=paths),
            config=config,
            names=names,
            idle=now() - state.last_activity >= timedelta(hours=config.idle_hours),
        )
        _call(call_claude=call_claude, paths=paths, record=record, model=config.scribe_model, brief=brief, timeout_s=config.stale_lock_minutes * 60)
        if not _finish(paths=paths, config=config, record=record):
            return


def _advance(*, conversation: ConversationState, ends: dict[str, int]) -> None:
    """Mark transcript lines that hold no visible turns as processed."""
    for link in conversation.sessions:
        link.processed_line = max(link.processed_line, ends.get(link.session_id, 0))


def run_scribe_catch_up(*, paths: ParentPaths, config: MemoryConfig, call_claude: ClaudeCall, now: Clock) -> None:
    """File every conversation's unprocessed tail, oldest conversation first, however short."""
    for state in list_conversations(paths=paths):
        run_scribe(paths=paths, config=config, conversation_id=state.id, catch_up=True, call_claude=call_claude, now=now)


def run_summariser(*, paths: ParentPaths, config: MemoryConfig, call_claude: ClaudeCall, now: Clock, timeout_minutes: int) -> None:
    if load_summariser_health(paths=paths).stopped_reason:
        return
    tz = ZoneInfo(config.local_timezone)
    names = load_names()
    today = now().astimezone(tz).date()
    record = acquire(paths=paths, config=config, kind=WorkerKind.SUMMARISER, now=now(), timeout_minutes=timeout_minutes)
    if record is None:
        return
    with MemoryStore(db_path=paths.db) as store:
        plan = plan_for(store=store, today=today)
        if plan.is_empty:
            store.set_refresh_state(through_revision=plan.through_revision, calendar_week_start=plan.calendar_week_start, now=now())
            remove_lock(paths=paths, kind=WorkerKind.SUMMARISER)
            return
        periods = store.periods()
        brief = build_summariser_brief(
            template=load_prompt(name="summariser"),
            parent=paths.parent,
            run_id=record.run_id,
            now_local=now().astimezone(tz),
            plan=plan,
            tag_sections=tag_sections(store=store, plan=plan),
            period_sections=period_sections(store=store, plan=plan, today=today),
            eras=[period for period in periods if period.kind is PeriodKind.ERA],
            core=store.facts_for_tag(name="core"),
            preferences=store.facts_for_tag(name="agent_preferences"),
            recent=[period for period in periods if period.kind in (PeriodKind.WEEK, PeriodKind.MONTH, PeriodKind.QUARTER)],
            high_level_summary=paths.summary.read_text(encoding="utf-8") if paths.summary.exists() else "",
            guide=load_memory_guide(paths=paths),
            names=names,
        )
    record = record.model_copy(update={"through_revision": plan.through_revision, "calendar_week_start": plan.calendar_week_start, "expired_periods": plan.expired_periods})
    write_lock(paths=paths, record=record)
    _call(call_claude=call_claude, paths=paths, record=record, model=config.summariser_model, brief=brief, timeout_s=timeout_minutes * 60)
    _finish(paths=paths, config=config, record=record)


def run_consolidator(*, paths: ParentPaths, config: MemoryConfig, call_claude: ClaudeCall, now: Clock, timeout_minutes: int) -> None:
    record = acquire(paths=paths, config=config, kind=WorkerKind.CONSOLIDATOR, now=now(), timeout_minutes=timeout_minutes)
    if record is None:
        return
    with MemoryStore(db_path=paths.db) as store:
        brief = build_consolidator_brief(
            template=load_prompt(name="consolidate"),
            parent=paths.parent,
            run_id=record.run_id,
            now_local=now().astimezone(ZoneInfo(config.local_timezone)),
            tags=store.tag_lines(),
            aliases=store.vocabulary().aliases,
            facts=store.current_facts(),
            guide=load_memory_guide(paths=paths),
        )
    _call(call_claude=call_claude, paths=paths, record=record, model=config.summariser_model, brief=brief, timeout_s=timeout_minutes * 60)
    remove_lock(paths=paths, kind=WorkerKind.CONSOLIDATOR)


def main(*, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m memorylayers.entry.runner", description="Run one headless memory worker.")
    parser.add_argument("--parent", required=True)
    parser.add_argument("--kind", required=True, choices=[WorkerKind.SCRIBE.value, WorkerKind.SUMMARISER.value, WorkerKind.CONSOLIDATOR.value])
    parser.add_argument("--conversation")
    parser.add_argument("--catch-up", action="store_true")
    parser.add_argument("--timeout-minutes", type=int)
    args = parser.parse_args(argv)
    paths = parent_paths(parent=args.parent)
    config = load_config(paths=paths)
    claude = find_claude(executable=config.claude_executable)
    if claude is None:
        print(f"{config.claude_executable!r} not found on PATH; no worker run", file=sys.stderr)
        return 1
    call: ClaudeCall = partial(run_claude, claude=claude, cwd=PROJECT_ROOT)
    timeout = args.timeout_minutes or config.stale_lock_minutes

    def now() -> datetime:
        return datetime.now(UTC)

    try:
        match WorkerKind(args.kind):
            case WorkerKind.SCRIBE if args.catch_up:
                run_scribe_catch_up(paths=paths, config=config, call_claude=call, now=now)
            case WorkerKind.SCRIBE:
                if not args.conversation:
                    parser.error("--conversation or --catch-up is required for the scribe")
                run_scribe(paths=paths, config=config, conversation_id=args.conversation, catch_up=False, call_claude=call, now=now)
            case WorkerKind.SUMMARISER:
                run_summariser(paths=paths, config=config, call_claude=call, now=now, timeout_minutes=timeout)
            case WorkerKind.CONSOLIDATOR:
                run_consolidator(paths=paths, config=config, call_claude=call, now=now, timeout_minutes=timeout)
    except PersonaError as error:
        print(f"no worker run: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    use_utf8_streams()
    raise SystemExit(main(argv=sys.argv[1:]))
