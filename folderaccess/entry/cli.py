"""The folderaccess command line: the folders the assistant may read or edit, synced into the local project settings."""

import argparse
import sys
from pathlib import Path

from folderaccess.adapters import paths
from folderaccess.adapters.settings import read_settings, write_settings
from folderaccess.adapters.store import read_list, read_synced, write_list, write_synced
from folderaccess.domain.listing import normalise_path, remove, upsert
from folderaccess.domain.permissions import merge, to_permissions
from folderaccess.domain.validation import validate
from folderaccess.models.folders import Access, FolderAccess

NEW_CONVERSATION = "Takes effect in a new conversation."


def _save(*, entries: list[FolderAccess]) -> None:
    """Write the list and the settings built from it, once both are known to be good."""
    permissions = to_permissions(entries=entries)
    settings = merge(settings=read_settings(), permissions=permissions, previous=read_synced())
    write_list(entries=entries)
    write_settings(settings=settings)
    write_synced(permissions=permissions)


def _validate(*, path: Path) -> None:
    validate(path=path, project_root=paths.PROJECT_ROOT, home=Path.home())


def _list(args: argparse.Namespace) -> None:
    entries = read_list()
    print("\n".join(f"{entry.access} {entry.path}" for entry in entries) if entries else "No folders listed.")


def _add(args: argparse.Namespace) -> None:
    path = Path(args.path)
    _validate(path=path)
    entry = FolderAccess(path=normalise_path(path=str(path.resolve())), access=Access(args.access))
    _save(entries=upsert(entries=read_list(), entry=entry))
    print(f"Listed {entry.access} {entry.path}. {NEW_CONVERSATION}")


def _remove(args: argparse.Namespace) -> None:
    _save(entries=remove(entries=read_list(), path=args.path))
    print(f"Removed {normalise_path(path=args.path)}. {NEW_CONVERSATION}")


def _sync(args: argparse.Namespace) -> None:
    entries = read_list()
    for entry in entries:
        _validate(path=Path(entry.path))
    _save(entries=entries)
    print(f"Synced {len(entries)} folder(s) into {paths.settings_path()}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m folderaccess",
        description="The folders the assistant may read or edit, kept in a list and synced into the project's local Claude Code permissions (.claude/settings.local.json).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="Each listed folder, access then path.").set_defaults(handler=_list)
    add = subparsers.add_parser("add", help="List a folder, or change the access of a listed one, then sync.")
    add.add_argument("path", help="Absolute path of the folder.")
    add.add_argument("--access", required=True, choices=[access.value for access in Access])
    add.set_defaults(handler=_add)
    remove_folder = subparsers.add_parser("remove", help="Take a folder off the list, then sync.")
    remove_folder.add_argument("path", help="The listed folder's path.")
    remove_folder.set_defaults(handler=_remove)
    subparsers.add_parser("sync", help="Validate every listed folder and rewrite the settings from the list, after a hand edit.").set_defaults(handler=_sync)
    return parser


def main(*, argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except ValueError as error:
        print(str(error).splitlines()[0], file=sys.stderr)
        return 2
    return 0
