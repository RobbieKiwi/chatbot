"""The folder list on disk, and the permissions it last synced. A missing file is an empty list."""

from folderaccess.adapters import paths
from folderaccess.adapters.files import write_text_atomically
from folderaccess.domain.listing import parse_list, render_list
from folderaccess.models.folders import FolderAccess, Permissions


def read_list() -> list[FolderAccess]:
    try:
        text = paths.list_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return parse_list(text=text)


def write_list(*, entries: list[FolderAccess]) -> None:
    write_text_atomically(path=paths.list_path(), text=render_list(entries=entries))


def read_synced() -> Permissions:
    path = paths.synced_path()
    try:
        return Permissions.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return Permissions(allow=[], additional_directories=[])
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error


def write_synced(*, permissions: Permissions) -> None:
    write_text_atomically(path=paths.synced_path(), text=permissions.model_dump_json(indent=2) + "\n")
