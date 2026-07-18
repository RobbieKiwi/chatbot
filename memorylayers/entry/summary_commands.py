"""Summariser and consolidator commands. Only headless workers are allowed to run these."""

import argparse
from typing import Any

from memorylayers.domain.refresh import format_plan
from memorylayers.domain.tag_resolution import resolve_tags
from memorylayers.entry.common import CliError, add_parent, local_zone, now_utc, open_store, paths_of, text_argument
from memorylayers.entry.planning import period_bucket, plan_for
from memorylayers.models.dates import ONGOING_END, Bucket
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import PeriodKind
from memorylayers.tools.occurred import OccurredFormatError, parse_occurred
from memorylayers.tools.tags import canonical_form, resolve_known

TAG_SUMMARY_WORDS = 1200


def _sub(*, subparsers: Any, name: str, help_text: str, actions: list[str]) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text)
    parser.add_argument("action", choices=actions)
    add_parent(parser=parser)
    return parser


def register(*, subparsers: Any) -> None:
    plan = subparsers.add_parser("refresh-plan", help="List exactly which summaries are due.")
    add_parent(parser=plan)
    plan.set_defaults(handler=_refresh_plan)

    tag_summary = _sub(subparsers=subparsers, name="tag-summary", help_text="Write a tag summary (≤ ~1000 words).", actions=["set"])
    tag_summary.add_argument("--tag", required=True)
    tag_summary.add_argument("--text", help="Read from stdin when omitted.")
    tag_summary.set_defaults(handler=_tag_summary)

    period = _sub(subparsers=subparsers, name="period", help_text="Write a calendar period's summary.", actions=["set"])
    period.add_argument("--name", required=True, help='"2026-W40", "2026-10", "2026 Q3", "2026", or an existing era.')
    period.add_argument("--text", help="Read from stdin when omitted.")
    period.set_defaults(handler=_period)

    era = _sub(subparsers=subparsers, name="era", help_text="Create, move, summarise or delete an era.", actions=["set", "delete"])
    era.add_argument("--name", required=True)
    era.add_argument("--start", help="An --occurred value; the era starts at its start.")
    era.add_argument("--end", help="An --occurred value; the era ends at its end. Omit for an ongoing era.")
    era.add_argument("--text", help="The era's summary. Omit to keep the existing one.")
    era.set_defaults(handler=_era)

    high_level = _sub(subparsers=subparsers, name="high-level-summary", help_text="Replace the high-level summary.", actions=["set"])
    high_level.add_argument("--text", help="Read from stdin when omitted.")
    high_level.set_defaults(handler=_high_level_summary)

    tag = _sub(subparsers=subparsers, name="tag", help_text="Maintain the tag vocabulary.", actions=["merge", "rename", "describe"])
    tag.add_argument("--from", dest="source")
    tag.add_argument("--into")
    tag.add_argument("--to")
    tag.add_argument("--name")
    tag.add_argument("--description")
    tag.set_defaults(handler=_tag)

    alias = _sub(subparsers=subparsers, name="alias", help_text="Add an alias for a tag.", actions=["add"])
    alias.add_argument("--alias", required=True)
    alias.add_argument("--tag", required=True)
    alias.set_defaults(handler=_alias)

    fact = _sub(subparsers=subparsers, name="fact", help_text="Retag a fact.", actions=["retag"])
    fact.add_argument("id", type=int)
    fact.add_argument("--tags", required=True)
    fact.set_defaults(handler=_fact)


def _refresh_plan(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    today = now_utc().astimezone(local_zone(paths=paths)).date()
    with open_store(paths=paths) as store:
        print(format_plan(plan=plan_for(store=store, today=today)))


def _known(*, store: Any, name: str) -> str:
    known = resolve_known(name=name, vocabulary=store.vocabulary())
    if known is None:
        raise CliError(f"unknown tag {name!r}; run tags to list them")
    return known


def _tag_summary(args: argparse.Namespace) -> None:
    text = text_argument(args=args)
    if len(text.split()) > TAG_SUMMARY_WORDS:
        raise CliError(f"tag summary has {len(text.split())} words; keep it under ~1000")
    with open_store(paths=paths_of(args=args)) as store:
        name = _known(store=store, name=args.tag)
        store.set_tag_summary(name=name, summary=text, now=now_utc())
    print(f"tag summary set: {name}")


def _period(args: argparse.Namespace) -> None:
    text = text_argument(args=args)
    with open_store(paths=paths_of(args=args)) as store:
        bucket = period_bucket(store=store, name=args.name)
        if bucket is None:
            raise CliError(f'unknown period {args.name!r}: calendar periods are named like "2026-W40", "2026-10", "2026 Q3", "2026"; create eras with era set')
        store.set_period(bucket=bucket, summary=text, now=now_utc())
    print(f"period summary set: {bucket.name}")


def _era(args: argparse.Namespace) -> None:
    with open_store(paths=paths_of(args=args)) as store:
        if args.action == "delete":
            store.delete_period(name=args.name)
            print(f"era deleted: {args.name}")
            return
        existing = store.period(name=args.name)
        try:
            start = parse_occurred(text=args.start).start if args.start else (existing.start if existing else None)
            end = parse_occurred(text=args.end).end if args.end else ONGOING_END
        except OccurredFormatError as error:
            raise CliError(str(error)) from error
        if start is None or end is None:
            raise CliError("a new era needs --start")
        summary = args.text.strip() if args.text else None
        store.set_period(bucket=Bucket(name=args.name, kind=PeriodKind.ERA, start=start, end=end), summary=summary, now=now_utc())
    print(f"era set: {args.name}")


def _high_level_summary(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    text = text_argument(args=args)
    refreshed = now_utc().astimezone(local_zone(paths=paths))
    paths.summary.parent.mkdir(parents=True, exist_ok=True)
    paths.summary.write_text(f"Refreshed: {refreshed:%Y-%m-%d %H:%M %Z}\n\n{text}\n", encoding="utf-8")
    print("high-level summary set")


def _tag(args: argparse.Namespace) -> None:
    with open_store(paths=paths_of(args=args)) as store:
        if args.action == "describe":
            if not (args.name and args.description):
                raise CliError("tag describe needs --name and --description")
            store.describe_tag(name=_known(store=store, name=args.name), description=args.description)
            print(f"described {args.name}")
            return
        if not args.source:
            raise CliError(f"tag {args.action} needs --from")
        source = _known(store=store, name=args.source)
        if args.action == "merge":
            if not args.into:
                raise CliError("tag merge needs --into")
            target = _known(store=store, name=args.into)
        else:
            if not args.to:
                raise CliError("tag rename needs --to")
            target = canonical_form(name=args.to)
            if store.tag(name=target) is not None:
                raise CliError(f"{target!r} already exists; use tag merge")
            old = store.tag(name=source)
            assert old is not None
            store.create_tag(new=NewTag(name=target, kind=old.kind, description=old.description), now=now_utc())
        moved = store.merge_tag(source=source, target=target)
    print(f"{source} -> {target}: {moved} facts moved; {source} is now an alias")


def _alias(args: argparse.Namespace) -> None:
    with open_store(paths=paths_of(args=args)) as store:
        target = _known(store=store, name=args.tag)
        store.add_alias(alias=canonical_form(name=args.alias), tag=target)
    print(f"alias {args.alias} -> {target}")


def _fact(args: argparse.Namespace) -> None:
    with open_store(paths=paths_of(args=args)) as store:
        resolution = resolve_tags(requested=args.tags.split(","), vocabulary=store.vocabulary(), new_categories=[], new_entities=[])
        if resolution.errors:
            raise CliError("\n".join(resolution.errors))
        try:
            store.update_fact(fact_id=args.id, tags=resolution.names)
        except KeyError as error:
            raise CliError(f"no fact #{args.id}") from error
    print(f"fact #{args.id} retagged: {', '.join(resolution.names)}")
