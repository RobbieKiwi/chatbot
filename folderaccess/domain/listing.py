"""The list file's text, and the path form entries are stored and compared in."""

from folderaccess.models.folders import Access, FolderAccess

HEADER = """\
# Folders the assistant may read or edit, one per line: <read|edit> <absolute path>.
# Change it with `python -m folderaccess add|remove`; after a hand edit, run `python -m folderaccess sync`.
"""


def normalise_path(*, path: str) -> str:
    normalised = path.replace("\\", "/")
    if len(normalised) >= 2 and normalised[1] == ":":
        normalised = normalised[0].upper() + normalised[1:]
    stripped = normalised.rstrip("/")
    return stripped + "/" if stripped.endswith(":") else stripped


def same_path(*, a: str, b: str) -> bool:
    # Windows paths are case-insensitive
    return normalise_path(path=a).casefold() == normalise_path(path=b).casefold()


def is_within(*, path: str, root: str) -> bool:
    """True when `path` is `root` or a folder below it, compared without regard to case."""
    folded_path = normalise_path(path=path).casefold()
    folded_root = normalise_path(path=root).casefold().rstrip("/")
    return folded_path == folded_root or folded_path.startswith(folded_root + "/")


def parse_list(*, text: str) -> list[FolderAccess]:
    entries = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(maxsplit=1)
        if len(parts) != 2 or parts[0] not in Access:
            raise ValueError(f"line {number} is not '<read|edit> <path>': {stripped!r}")
        entries.append(FolderAccess(path=normalise_path(path=parts[1]), access=Access(parts[0])))
    return entries


def render_list(*, entries: list[FolderAccess]) -> str:
    return HEADER + "".join(f"{entry.access} {entry.path}\n" for entry in entries)


def upsert(*, entries: list[FolderAccess], entry: FolderAccess) -> list[FolderAccess]:
    """Add the entry, or change the access of the listed entry for the same path, keeping its place."""
    for index, existing in enumerate(entries):
        if same_path(a=existing.path, b=entry.path):
            return [*entries[:index], existing.model_copy(update={"access": entry.access}), *entries[index + 1 :]]
    return [*entries, entry.model_copy(update={"path": normalise_path(path=entry.path)})]


def remove(*, entries: list[FolderAccess], path: str) -> list[FolderAccess]:
    kept = [entry for entry in entries if not same_path(a=entry.path, b=path)]
    if len(kept) == len(entries):
        raise ValueError(f"{normalise_path(path=path)} is not listed")
    return kept
