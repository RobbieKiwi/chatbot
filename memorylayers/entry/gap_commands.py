"""The gap list: written by the summariser, read by freshtopics through this CLI."""

import argparse
import sys
from typing import Any

from pydantic import TypeAdapter, ValidationError

from memorylayers.adapters.state_files import load_config
from memorylayers.domain.curiosity import available_gaps
from memorylayers.entry.common import CliError, add_parent, now_utc, open_store, paths_of
from memorylayers.models.views import NewGap, TagVocabulary
from memorylayers.tools.tags import resolve_known

GAPS_LIMIT = 10
_GAP_LIST = TypeAdapter(list[NewGap])


def register(*, subparsers: Any) -> None:
    gaps = subparsers.add_parser("gaps", help="What memory knows exists but knows little about.")
    gaps.add_argument("action", choices=["set", "list"])
    gaps.add_argument("--json", dest="json_text", help='set: the whole list as [{"tag": "...", "text": "..."}, ...]; read from stdin when omitted.')
    gaps.add_argument("--available", action="store_true", help="list: only gaps outside the cooldown.")
    add_parent(parser=gaps)
    gaps.set_defaults(handler=_gaps)


def _gaps(args: argparse.Namespace) -> None:
    if args.action == "set":
        _set(args=args)
    else:
        _list(args=args)


def _known_or_none(*, name: str, vocabulary: TagVocabulary) -> str | None:
    try:
        return resolve_known(name=name, vocabulary=vocabulary)
    except ValueError:  # a name with no letters or digits
        return None


def _set(*, args: argparse.Namespace) -> None:
    text = args.json_text if args.json_text is not None else sys.stdin.read()
    try:
        gaps = _GAP_LIST.validate_json(text)
    except ValidationError as error:
        raise CliError(f'invalid gaps: give a JSON list of {{"tag": "...", "text": "..."}}\n{error}') from error
    if len(gaps) > GAPS_LIMIT:
        raise CliError(f"{len(gaps)} gaps; write at most {GAPS_LIMIT} gaps")
    with open_store(paths=paths_of(args=args)) as store:
        vocabulary = store.vocabulary()
        resolved = [(gap, _known_or_none(name=gap.tag, vocabulary=vocabulary)) for gap in gaps]
        unknown = [gap.tag for gap, name in resolved if name is None]
        if unknown:
            raise CliError(f"unknown tags: {', '.join(unknown)}; run tags to list them")
        store.replace_gaps(gaps=[NewGap(tag=name, text=gap.text.strip()) for gap, name in resolved if name is not None], now=now_utc())
    print(f"gaps set: {len(gaps)}")


def _list(*, args: argparse.Namespace) -> None:
    paths = paths_of(args=args)
    with open_store(paths=paths) as store:
        gaps = store.gaps()
    if args.available:
        gaps = available_gaps(gaps=gaps, now=now_utc(), cooldown_days=load_config(paths=paths).gap_cooldown_days)
    for gap in gaps:
        print(f"{gap.tag}: {gap.text}")
