"""freshtopics command line: the topic history of a parent skill."""

import argparse
import io
import random
import sys

from freshtopics.dao import add_topic_entry, get_topic_summary
from freshtopics.gap_probe import list_available_gaps
from freshtopics.seeds import choose_seed, render_seed
from freshtopics.word_lists import read_word_list


def _context(args: argparse.Namespace) -> None:
    summary = get_topic_summary(parent_name=args.parent, recent_count=args.recent)
    recent = [f"- {topic.phrase} ({topic.initiator}, {topic.score})" for topic in summary["recent_topics"]]
    print(
        "\n".join(
            ["Recent topics (newest last):", *recent, f"Terrible topics: {'; '.join(summary['terrible_topics']) or 'none'}", f"Excellent topics: {'; '.join(summary['excellent_topics']) or 'none'}"]
        )
    )


def _log(args: argparse.Namespace) -> None:
    add_topic_entry(parent_name=args.parent, phrase=args.phrase, initiator=args.initiator, score=args.score)
    print(f"logged: {args.phrase.strip().lower()}")


def _seeds(args: argparse.Namespace) -> None:
    seed = choose_seed(
        probe_chance=args.probe_chance,
        rng=random.Random(),
        list_gaps=lambda: list_available_gaps(parent=args.parent),
        words=read_word_list(name="seed_words.txt"),
        subjects=read_word_list(name="subjects.txt"),
    )
    print(render_seed(seed=seed))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m freshtopics", description="Conversation topic history for a parent skill.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    context = subparsers.add_parser("context", help="Recent, terrible and excellent topics.")
    context.add_argument("--parent", required=True)
    context.add_argument("--recent", type=int, default=10)
    context.set_defaults(handler=_context)
    log = subparsers.add_parser("log", help="Record a finished topic with how engaged the user was.")
    log.add_argument("--parent", required=True)
    log.add_argument("--phrase", required=True, help="3–8 words, lowercase.")
    log.add_argument("--initiator", required=True, choices=["skill", "user"])
    log.add_argument("--score", type=int, default=5, help="1 hated it · 3 asked to move on · 5 neutral · 7 good conversation · 10 loved it.")
    log.set_defaults(handler=_log)
    seeds = subparsers.add_parser("seeds", help="Where a new topic starts: a gap in memory to probe, or two nouns and a field of knowledge.")
    seeds.add_argument("--parent", required=True)
    seeds.add_argument("--probe-chance", type=float, default=0.25, help="Chance of a probe instead of seeds, 0–1.")
    seeds.set_defaults(handler=_seeds)
    return parser


def main(*, argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except ValueError as error:  # pydantic's ValidationError is a ValueError
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main(argv=sys.argv[1:]))
