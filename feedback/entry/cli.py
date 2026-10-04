"""The feedback command line: reading feedback and recording the changes that answer it."""

import argparse
import sys
from datetime import UTC, datetime

from pydantic import ValidationError

from feedback.adapters.paths import feedback_path
from feedback.adapters.store import editing_feedback, load_feedback
from feedback.domain.filing import FeedbackError, record_change
from feedback.domain.report import format_history, format_item, format_open


def now_utc() -> datetime:
    return datetime.now(UTC)


def _ids(*, text: str | None) -> list[int]:
    try:
        return [int(part) for part in text.split(",") if part.strip()] if text else []
    except ValueError as error:
        raise FeedbackError(f"item ids are comma-separated numbers, got {text!r}") from error


def _open(args: argparse.Namespace) -> None:
    print(format_open(feedback=load_feedback(path=feedback_path(parent=args.parent))))


def _show(args: argparse.Namespace) -> None:
    feedback = load_feedback(path=feedback_path(parent=args.parent))
    item = next((item for item in feedback.items if item.id == args.id), None)
    if item is None:
        raise FeedbackError(f"no feedback item #{args.id}")
    print(format_item(item=item, changes=feedback.changes, with_context=True))


def _record_change(args: argparse.Namespace) -> None:
    files = [part.strip() for part in args.files.split(",") if part.strip()] if args.files else []
    with editing_feedback(path=feedback_path(parent=args.parent)) as feedback:
        change = record_change(feedback=feedback, summary=args.summary, files=files, resolved=_ids(text=args.resolved), partly=_ids(text=args.partly), now=now_utc())
    print(f"change #{change.id} recorded")


def _history(args: argparse.Namespace) -> None:
    print(format_history(changes=load_feedback(path=feedback_path(parent=args.parent)).changes))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m feedback", description="Feedback on the assistant, filed with fb:, and the prompt changes that answer it.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    open_items = subparsers.add_parser("open", help="Items still open or partly addressed, with their notes and changes so far.")
    open_items.set_defaults(handler=_open)
    show = subparsers.add_parser("show", help="One item in full, with the turns before it.")
    show.add_argument("id", type=int)
    show.set_defaults(handler=_show)
    change = subparsers.add_parser("record-change", help="Record one coherent prompt edit and the items it addressed.")
    change.add_argument("--summary", required=True)
    change.add_argument("--files", help="Comma-separated paths of the files edited.")
    change.add_argument("--resolved", help="Comma-separated item ids this change resolves.")
    change.add_argument("--partly", help="Comma-separated item ids this change partly addresses.")
    change.set_defaults(handler=_record_change)
    history = subparsers.add_parser("history", help="Every change, newest first.")
    history.set_defaults(handler=_history)
    for sub in (open_items, show, change, history):
        sub.add_argument("--parent", required=True, help="The parent skill, e.g. chatbot.")
    return parser


def main(*, argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except FeedbackError as error:
        print(str(error), file=sys.stderr)
        return 2
    except ValidationError as error:
        print(f"invalid feedback file {feedback_path(parent=args.parent)}:\n{error}", file=sys.stderr)
        return 2
    return 0
