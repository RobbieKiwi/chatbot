"""Plumbing shared by the command-line entry points."""

import argparse
import io
import sys
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from memorylayers.adapters.paths import parent_paths
from memorylayers.adapters.state_files import load_config
from memorylayers.adapters.store import MemoryStore
from memorylayers.models.paths import ParentPaths

CLI = ".venv/Scripts/python -m memorylayers"


class CliError(Exception):
    """A validation error: exit 2 with a message an agent can act on."""


def use_utf8_streams() -> None:
    # Windows pipes default to the ANSI code page, which cannot encode most of what the assistant says.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def add_parent(*, parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--parent", required=True, help="The parent skill whose memory to use, e.g. chatbot.")


def paths_of(*, args: argparse.Namespace) -> ParentPaths:
    return parent_paths(parent=args.parent)


def open_store(*, paths: ParentPaths) -> MemoryStore:
    return MemoryStore(db_path=paths.db)


def text_argument(*, args: argparse.Namespace) -> str:
    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        raise CliError("no text given: pass --text or pipe it on stdin")
    return text.strip()


def now_utc() -> datetime:
    return datetime.now(UTC)


def local_zone(*, paths: ParentPaths) -> ZoneInfo:
    return ZoneInfo(load_config(paths=paths).local_timezone)
