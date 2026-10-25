"""The folder list on disk. A missing file is an empty list."""

from folderaccess.adapters import paths
from folderaccess.adapters.files import write_text_atomically
from folderaccess.domain.listing import parse_list, render_list
from folderaccess.models.folders import FolderAccess


def read_list() -> list[FolderAccess]:
    try:
        text = paths.list_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return parse_list(text=text)


def write_list(*, entries: list[FolderAccess]) -> None:
    write_text_atomically(path=paths.list_path(), text=render_list(entries=entries))
