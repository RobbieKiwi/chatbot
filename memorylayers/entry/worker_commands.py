"""Worker bookkeeping commands: status, and the commits that end worker runs."""

import argparse
from typing import Any

from memorylayers.adapters.locks import read_lock, write_lock
from memorylayers.adapters.processes import pid_alive
from memorylayers.adapters.state_files import list_conversations, load_summariser_health, update_conversation, update_summariser_health
from memorylayers.domain.due import lock_status
from memorylayers.entry.common import CliError, add_parent, local_zone, now_utc, open_store, paths_of
from memorylayers.models.conversation import ConversationState
from memorylayers.models.vocab import WorkerKind
from memorylayers.models.worker import WorkerHealth

_RUN_KINDS = (WorkerKind.SCRIBE, WorkerKind.SUMMARISER, WorkerKind.CONSOLIDATOR)


def register(*, subparsers: Any) -> None:
    status = subparsers.add_parser("status", help="Worker locks, health and latest logs.")
    add_parent(parser=status)
    status.set_defaults(handler=_status)

    commit = subparsers.add_parser("commit", help="End a scribe run: mark its window filed. Run it last.")
    commit.add_argument("--run", required=True)
    add_parent(parser=commit)
    commit.set_defaults(handler=_commit)

    refresh = subparsers.add_parser("refresh", help="End a summariser run (commit), or ask for a full rebuild (reset).")
    refresh.add_argument("action", choices=["commit", "reset"])
    refresh.add_argument("--run", help="The run id from the brief (commit).")
    add_parent(parser=refresh)
    refresh.set_defaults(handler=_refresh)


def _health(*, health: WorkerHealth) -> str:
    if health.stopped_reason:
        return f"stopped: {health.stopped_reason}"
    return "ok" if not health.consecutive_failures else f"ok ({health.consecutive_failures} recent failures)"


def _status(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    tz = local_zone(paths=paths)
    now = now_utc()
    lines = []
    for kind in _RUN_KINDS:
        record = read_lock(paths=paths, kind=kind)
        if record is None:
            lines.append(f"{kind}: idle")
            continue
        state = lock_status(record=record, alive=pid_alive(pid=record.pid), now=now)
        lines.append(f"{kind}: {state} — run {record.run_id}, pid {record.pid}, since {record.started_at.astimezone(tz):%Y-%m-%d %H:%M}")
    lines.append(f"summariser health: {_health(health=load_summariser_health(paths=paths))}")
    lines += [f"conversation {state.id}: scribe {_health(health=state.scribe_health)}" for state in list_conversations(paths=paths)]
    for kind in _RUN_KINDS:
        logs = sorted(paths.logs.glob(f"{kind.value}-*.log")) if paths.logs.exists() else []
        if logs:
            lines.append(f"latest {kind} log: {logs[-1]}")
    print("\n".join(lines))


def _in_flight(*, args: argparse.Namespace, kind: WorkerKind) -> Any:
    paths = paths_of(args=args)
    record = read_lock(paths=paths, kind=kind)
    if record is None or record.run_id != args.run:
        raise CliError(f"no {kind} run {args.run!r} in flight; nothing committed")
    return paths, record


def _commit(args: argparse.Namespace) -> None:
    paths, record = _in_flight(args=args, kind=WorkerKind.SCRIBE)

    def change(state: ConversationState) -> None:
        for link in state.sessions:
            if link.session_id in record.window_end:
                link.processed_line = max(link.processed_line, record.window_end[link.session_id])
        for note in state.pending_notes:
            if note.number in record.pending_at_start:
                note.runs_survived += 1
        state.scribe_health = WorkerHealth()

    update_conversation(paths=paths, conversation_id=record.conversation_id, change=change)
    write_lock(paths=paths, record=record.model_copy(update={"committed": True}))
    print(f"committed {record.run_id}")


def _refresh(args: argparse.Namespace) -> None:
    if args.action == "reset":
        with open_store(paths=paths_of(args=args)) as store:
            store.reset_refresh_state()
        print("every summary will be rebuilt on the next refresh")
        return
    paths, record = _in_flight(args=args, kind=WorkerKind.SUMMARISER)
    with open_store(paths=paths) as store:
        store.set_refresh_state(through_revision=record.through_revision, calendar_week_start=record.calendar_week_start, now=now_utc())
        for name in record.expired_periods:
            store.delete_period(name=name)

    def healthy(health: WorkerHealth) -> None:
        health.consecutive_failures, health.stopped_reason = 0, None

    update_summariser_health(paths=paths, change=healthy)
    write_lock(paths=paths, record=record.model_copy(update={"committed": True}))
    print(f"committed {record.run_id}")
