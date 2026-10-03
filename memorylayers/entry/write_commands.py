"""Scribe write commands. Only headless workers are allowed to run these."""

import argparse
from typing import Any

from memorylayers.adapters.state_files import load_config, update_conversation
from memorylayers.adapters.store import MemoryStore
from memorylayers.domain.duplicates import close_matches
from memorylayers.domain.recall import format_fact
from memorylayers.domain.tag_resolution import resolve_tags
from memorylayers.entry.common import CliError, add_parent, now_utc, open_store, paths_of, text_argument
from memorylayers.models.conversation import ConversationState, PendingNote
from memorylayers.models.dates import OccurredRange
from memorylayers.tools.occurred import TIMELESS, OccurredFormatError, parse_occurred

ROLLING_SUMMARY_WORDS = 450


def _add_tag_flags(*, parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tags", help="Comma-separated tag names or aliases.")
    parser.add_argument("--new-category", action="append", default=[], help='Register a category: "name: description".')
    parser.add_argument("--new-entity", action="append", default=[], help='Register a person, place or organisation: "name: short profile".')


def _add_occurred_flags(*, parser: argparse.ArgumentParser, required: bool) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--occurred", help="YYYY-MM-DD, YYYY-MM, YYYY, YYYYs, A..B or unknown.")
    group.add_argument("--timeless", action="store_true", help="A standing trait that belongs to no period.")


def register(*, subparsers: Any) -> None:
    store = subparsers.add_parser("store", help="Store a settled fact.")
    store.add_argument("--detail", required=True)
    store.add_argument("--relevance", type=int, required=True, help="1–10, per the memory guide.")
    _add_tag_flags(parser=store)
    _add_occurred_flags(parser=store, required=True)
    store.add_argument("--force-new", action="store_true", help="Store even though close matches exist.")
    store.add_argument("--conversation", help="Record the fact in this conversation's ledger.")
    add_parent(parser=store)
    store.set_defaults(handler=_store)

    update = subparsers.add_parser("update", help="Amend a fact.")
    update.add_argument("id", type=int)
    update.add_argument("--detail")
    update.add_argument("--relevance", type=int)
    _add_tag_flags(parser=update)
    _add_occurred_flags(parser=update, required=False)
    add_parent(parser=update)
    update.set_defaults(handler=_update)

    supersede = subparsers.add_parser("supersede", help="Mark a fact as replaced by a newer one.")
    supersede.add_argument("old", type=int)
    supersede.add_argument("--by", type=int, required=True)
    add_parent(parser=supersede)
    supersede.set_defaults(handler=_supersede)

    pending = subparsers.add_parser("pending", help="Park, refine or drop facts still forming.")
    pending.add_argument("action", choices=["add", "refine", "drop"])
    pending.add_argument("--conversation", required=True)
    pending.add_argument("--number", type=int)
    pending.add_argument("--text", help="The note; read from stdin when omitted (add, refine).")
    add_parent(parser=pending)
    pending.set_defaults(handler=_pending)

    rolling = subparsers.add_parser("rolling-summary", help="Replace the conversation's rolling summary.")
    rolling.add_argument("action", choices=["set"])
    rolling.add_argument("--conversation", required=True)
    rolling.add_argument("--text", help="The summary; read from stdin when omitted.")
    add_parent(parser=rolling)
    rolling.set_defaults(handler=_rolling_summary)


def _relevance(*, value: int) -> int:
    if not 1 <= value <= 10:
        raise CliError("relevance must be 1–10; a fact worth 0 should not be stored")
    return value


def _occurred(*, args: argparse.Namespace) -> OccurredRange | None:
    if args.timeless:
        return TIMELESS
    if args.occurred is None:
        return None
    try:
        return parse_occurred(text=args.occurred)
    except OccurredFormatError as error:
        raise CliError(str(error)) from error


def _resolve(*, store: MemoryStore, args: argparse.Namespace) -> tuple[list[str], Any]:
    requested = [name for name in (args.tags or "").split(",") if name.strip()]
    vocabulary = store.vocabulary()
    resolution = resolve_tags(requested=requested, vocabulary=vocabulary, new_categories=args.new_category, new_entities=args.new_entity)
    if resolution.errors:
        raise CliError("\n".join(resolution.errors))
    return resolution.names, resolution


def _store(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    relevance = _relevance(value=args.relevance)
    occurred = _occurred(args=args)
    assert occurred is not None  # the flag group is required
    with open_store(paths=paths) as store:
        names, resolution = _resolve(store=store, args=args)
        if not names:
            raise CliError("a fact needs at least one tag")
        if not args.force_new:
            kinds = store.vocabulary().kinds | {new.name: new.kind for new in resolution.to_create}
            threshold = load_config(paths=paths).duplicate_overlap
            matches = close_matches(detail=args.detail, tags=names, kinds=kinds, candidates=store.duplicate_candidates(detail=args.detail), threshold=threshold)
            if matches:
                listed = "\n".join(format_fact(fact=fact) for fact in store.facts_by_ids(ids=[match.id for match in matches]))
                raise CliError(f"Not stored: possible duplicates:\n{listed}\nSkip it, amend one with update <id>, or store anyway with --force-new.")
        now = now_utc()
        for new in resolution.to_create:
            store.create_tag(new=new, now=now)
        fact_id = store.add_fact(detail=args.detail, relevance=relevance, occurred=occurred, tags=names, source_conversation=args.conversation, now=now)
    if args.conversation:
        update_conversation(paths=paths, conversation_id=args.conversation, change=lambda state: state.ledger.append(fact_id))
    print(f"stored fact #{fact_id}")


def _update(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    relevance = _relevance(value=args.relevance) if args.relevance is not None else None
    with open_store(paths=paths) as store:
        tags = None
        if args.tags is not None or args.new_category or args.new_entity:
            tags, resolution = _resolve(store=store, args=args)
            for new in resolution.to_create:
                store.create_tag(new=new, now=now_utc())
        try:
            store.update_fact(fact_id=args.id, detail=args.detail, relevance=relevance, occurred=_occurred(args=args), tags=tags)
        except KeyError as error:
            raise CliError(f"no fact #{args.id}") from error
    print(f"updated fact #{args.id}")


def _supersede(args: argparse.Namespace) -> None:
    with open_store(paths=paths_of(args=args)) as store:
        try:
            store.supersede(old_id=args.old, new_id=args.by)
        except (KeyError, ValueError) as error:
            raise CliError(f"cannot supersede #{args.old} by #{args.by}: {error}") from error
    print(f"fact #{args.old} superseded by #{args.by}")


def _pending(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    text = text_argument(args=args) if args.action in ("add", "refine") else ""

    def change(state: ConversationState) -> None:
        if args.action == "add":
            number = max((note.number for note in state.pending_notes), default=0) + 1
            state.pending_notes.append(PendingNote(number=number, text=text))
            return
        note = next((note for note in state.pending_notes if note.number == args.number), None)
        if note is None:
            raise CliError(f"no pending note {args.number}; notes are {[n.number for n in state.pending_notes]}")
        if args.action == "refine":
            note.text = text
        else:
            state.pending_notes.remove(note)

    update_conversation(paths=paths, conversation_id=args.conversation, change=change)
    print(f"pending {args.action}: done")


def _rolling_summary(args: argparse.Namespace) -> None:
    text = text_argument(args=args)
    if len(text.split()) > ROLLING_SUMMARY_WORDS:
        raise CliError(f"rolling summary has {len(text.split())} words; keep it under ~400")
    update_conversation(paths=paths_of(args=args), conversation_id=args.conversation, change=lambda state: setattr(state, "rolling_summary", text))
    print("rolling summary set")
