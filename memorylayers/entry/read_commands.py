"""Read commands: open to the assistant, the librarian and every worker."""

import argparse
from typing import Any

from memorylayers.domain.recall import (
    CLI,
    format_category_recall,
    format_entity_recall,
    format_fact_list,
    format_period_recall,
    format_periods,
    format_search,
    format_tags,
    format_unknown,
)
from memorylayers.entry.common import CliError, add_parent, local_zone, open_store, paths_of
from memorylayers.models.dates import ONGOING_END
from memorylayers.models.vocab import TagKind
from memorylayers.tools.occurred import OccurredFormatError, parse_occurred
from memorylayers.tools.tags import closest_names, resolve_known

FACTS_LIMIT = 20


def register(*, subparsers: Any) -> None:
    summary = subparsers.add_parser("summary", help="Print the high-level summary.")
    add_parent(parser=summary)
    summary.set_defaults(handler=_summary)

    recall = subparsers.add_parser("recall", help="The top layer of what is known about a tag, alias or period.")
    recall.add_argument("name", nargs="?", help="A tag name or alias.")
    scope = recall.add_mutually_exclusive_group()
    scope.add_argument("--period", help='A period name: "2026-W40", "2026-10", "2026 Q3", "2026" or an era.')
    scope.add_argument("--between", help="An --occurred range such as 2014..2016.")
    add_parent(parser=recall)
    recall.set_defaults(handler=_recall)

    facts = subparsers.add_parser("facts", help="Current facts for a tag or a date range, by relevance then recency.")
    facts.add_argument("name", nargs="?", help="A tag name or alias.")
    facts.add_argument("--between", help="An --occurred range such as 2026-07..2026-09.")
    facts.add_argument("--limit", type=int, default=FACTS_LIMIT)
    facts.add_argument("--history", action="store_true", help="Include superseded facts.")
    add_parent(parser=facts)
    facts.set_defaults(handler=_facts)

    search = subparsers.add_parser("search", help="Full-text search across facts, tags, tag summaries and periods.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    add_parent(parser=search)
    search.set_defaults(handler=_search)

    for name, handler, text in (("periods", _periods, "List periods."), ("tags", _tags, "List categories and entities with fact counts.")):
        listing = subparsers.add_parser(name, help=text)
        add_parent(parser=listing)
        listing.set_defaults(handler=handler)


def _between(*, text: str) -> tuple[Any, Any, str]:
    try:
        occurred = parse_occurred(text=text)
    except OccurredFormatError as error:
        raise CliError(str(error)) from error
    if occurred.start is None or occurred.end is None:
        raise CliError(f"{text!r} has no dates to search between")
    return occurred.start, occurred.end, text


def _summary(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    print(paths.summary.read_text(encoding="utf-8") if paths.summary.exists() else "No high-level summary yet.")


def _recall(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    with open_store(paths=paths) as store:
        if args.period:
            period = store.period(name=args.period)
            if period is None:
                print(format_unknown(name=args.period, near=closest_names(name=args.period, candidates=[p.name for p in store.periods()])))
                return
            end = "ongoing" if period.end == ONGOING_END else period.end.isoformat()
            facts = store.facts_between(start=period.start, end=period.end)
            print(format_period_recall(name=period.name, between=f"{period.start}..{end}", summary=period.summary, facts=facts, parent=args.parent))
            return
        if args.between:
            start, end, label = _between(text=args.between)
            print(format_period_recall(name="Between", between=label, summary=None, facts=store.facts_between(start=start, end=end), parent=args.parent))
            return
        if not args.name:
            raise CliError("give a name, --period or --between")
        vocabulary = store.vocabulary()
        name = resolve_known(name=args.name, vocabulary=vocabulary)
        if name is None:
            print(format_unknown(name=args.name, near=closest_names(name=args.name.lower(), candidates=[*vocabulary.kinds, *vocabulary.aliases])))
            return
        tag = next(line for line in store.tag_lines() if line.name == name)
        facts = store.facts_for_tag(name=name)
        stored = store.tag_summary(name=name)
        summary = stored.summary if stored else None
        co_tags = store.co_tags(name=name).most_common()
        entities = [(other, count) for other, count in co_tags if vocabulary.kinds.get(other) is TagKind.ENTITY][:5]
        categories = [(other, count) for other, count in co_tags if vocabulary.kinds.get(other) is TagKind.CATEGORY][:5]
        if tag.kind is TagKind.ENTITY:
            dates = store.tag_dates(name=name)
            print(format_entity_recall(tag=tag, summary=summary, facts=facts, related=entities, categories=categories, dates=dates, tz=local_zone(paths=paths), parent=args.parent))
        else:
            print(format_category_recall(tag=tag, summary=summary, facts=facts, top_entities=entities, parent=args.parent))


def _facts(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    with open_store(paths=paths) as store:
        if args.between:
            start, end, label = _between(text=args.between)
            facts = store.facts_between(start=start, end=end, include_superseded=args.history)
            selector = f"--between {label}"
        elif args.name:
            name = resolve_known(name=args.name, vocabulary=store.vocabulary())
            if name is None:
                raise CliError(f"unknown tag {args.name!r}; run tags to list them")
            facts = store.facts_for_tag(name=name, include_superseded=args.history)
            selector = name
        else:
            raise CliError("give a tag name or --between")
    history = " --history" if args.history else ""
    print(format_fact_list(facts=facts, limit=args.limit, more_command=f"{CLI} facts {selector} --limit {len(facts)}{history} --parent {args.parent}"))


def _search(args: argparse.Namespace) -> None:
    with open_store(paths=paths_of(args=args)) as store:
        print(format_search(hits=store.search(query=args.query, limit=args.limit)))


def _periods(args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    with open_store(paths=paths) as store:
        print(format_periods(periods=store.periods(), tz=local_zone(paths=paths)))


def _tags(args: argparse.Namespace) -> None:
    with open_store(paths=paths_of(args=args)) as store:
        print(format_tags(tags=store.tag_lines()))
