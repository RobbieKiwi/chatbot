import pytest

from folderaccess.domain.listing import normalise_path, parse_list, remove, render_list, upsert
from folderaccess.models.folders import Access, FolderAccess

INBOX = FolderAccess(path="C:/Users/alex/projects/notes", access=Access.READ)
DRAFTS = FolderAccess(path="C:/Users/alex/writing/drafts", access=Access.EDIT)


def test_parse_skips_comments_and_blanks() -> None:
    text = "# folders\n\nread C:/Users/alex/projects/notes\n  # indented comment\nedit C:/Users/alex/writing/drafts\n"
    assert parse_list(text=text) == [INBOX, DRAFTS]


def test_render_then_parse_round_trips() -> None:
    text = render_list(entries=[INBOX, DRAFTS])
    assert text.startswith("#")
    assert "read C:/Users/alex/projects/notes\nedit C:/Users/alex/writing/drafts\n" in text
    assert parse_list(text=text) == [INBOX, DRAFTS]


def test_render_of_no_entries_is_only_comments() -> None:
    text = render_list(entries=[])
    assert text and all(line.startswith("#") for line in text.splitlines() if line)
    assert parse_list(text=text) == []


def test_parse_keeps_spaces_in_a_path() -> None:
    assert parse_list(text="read C:/Users/alex/My Documents\n")[0].path == "C:/Users/alex/My Documents"


@pytest.mark.parametrize("line", ["write C:/x", "read", "C:/x"])
def test_parse_names_the_malformed_line(line: str) -> None:
    with pytest.raises(ValueError, match="line 2"):
        parse_list(text=f"# header\n{line}\n")


@pytest.mark.parametrize("path", ["c:\\Users\\alex\\projects\\notes", "C:/Users/alex/projects/notes/", "c:/Users/alex/projects/notes\\"])
def test_normalise_path(path: str) -> None:
    assert normalise_path(path=path) == "C:/Users/alex/projects/notes"


def test_normalise_keeps_a_drive_root() -> None:
    assert normalise_path(path="c:\\") == "C:/"


def test_upsert_relevels_a_listed_path_in_place() -> None:
    relevelled = FolderAccess(path="c:\\users\\alex\\projects\\notes\\", access=Access.EDIT)
    assert upsert(entries=[INBOX, DRAFTS], entry=relevelled) == [FolderAccess(path=INBOX.path, access=Access.EDIT), DRAFTS]


def test_upsert_appends_a_new_path() -> None:
    assert upsert(entries=[INBOX], entry=DRAFTS) == [INBOX, DRAFTS]


def test_remove_matches_after_normalising() -> None:
    assert remove(entries=[INBOX, DRAFTS], path="c:\\Users\\alex\\projects\\notes\\") == [DRAFTS]


def test_remove_of_an_unlisted_path_raises() -> None:
    with pytest.raises(ValueError, match="not listed"):
        remove(entries=[INBOX], path="C:/elsewhere")
