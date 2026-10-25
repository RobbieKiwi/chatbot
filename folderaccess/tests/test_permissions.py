import json

from folderaccess.domain.permissions import merge, to_permissions
from folderaccess.models.folders import Access, FolderAccess, Permissions

DOCUMENTS = FolderAccess(path="C:/Users/alex/Documents", access=Access.READ)
NOTES = FolderAccess(path="D:/notes/content", access=Access.EDIT)


def test_rules_use_the_absolute_form() -> None:
    permissions = to_permissions(entries=[DOCUMENTS, NOTES])
    assert permissions.allow == [
        "Read(//c/Users/alex/Documents/**)",
        "Read(//d/notes/content/**)",
        "Edit(//d/notes/content/**)",
    ]


def test_every_listed_folder_is_an_additional_directory() -> None:
    assert to_permissions(entries=[DOCUMENTS, NOTES]).additional_directories == ["C:/Users/alex/Documents", "D:/notes/content"]


SETTINGS: dict[str, object] = {
    "permissions": {
        "allow": ["Bash(.venv/Scripts/python -m memorylayers:*)", "Read(./inbox/**)", "Glob(./inbox/**)", "Edit(//c/old/**)", "Bash(git status)"],
        "additionalDirectories": ["C:/old"],
        "deny": [],
    },
    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x"}]}]},
    "env": {"A": "1"},
}


PREVIOUS = Permissions(allow=["Edit(//c/old/**)"], additional_directories=["C:/old"])
NOTHING = Permissions(allow=[], additional_directories=[])


def test_merge_replaces_only_the_previously_synced_rules_and_directories() -> None:
    before = json.dumps(SETTINGS)
    permissions = Permissions(allow=["Read(//c/new/**)"], additional_directories=["C:/new"])
    merged = merge(settings=SETTINGS, permissions=permissions, previous=PREVIOUS)
    assert merged["permissions"] == {
        "allow": ["Bash(.venv/Scripts/python -m memorylayers:*)", "Read(./inbox/**)", "Glob(./inbox/**)", "Bash(git status)", "Read(//c/new/**)"],
        "additionalDirectories": ["C:/new"],
        "deny": [],
    }
    assert list(merged) == ["permissions", "hooks", "env"]
    section = merged["permissions"]
    assert isinstance(section, dict) and list(section) == ["allow", "additionalDirectories", "deny"]
    assert merged["hooks"] == SETTINGS["hooks"]
    assert json.dumps(SETTINGS) == before


def test_merge_keeps_rules_and_directories_the_user_approved() -> None:
    settings: dict[str, object] = {"permissions": {"allow": ["Read(//c/x/**)", "Edit(//c/old/**)"], "additionalDirectories": ["C:/x", "C:/old"]}}
    merged = merge(settings=settings, permissions=Permissions(allow=["Read(//c/new/**)", "Read(//c/x/**)"], additional_directories=["C:/new", "C:/x"]), previous=PREVIOUS)
    assert merged["permissions"] == {"allow": ["Read(//c/x/**)", "Read(//c/new/**)"], "additionalDirectories": ["C:/x", "C:/new"]}


def test_merge_into_settings_without_permissions() -> None:
    merged = merge(settings={"hooks": {}}, permissions=Permissions(allow=["Read(//c/a/**)"], additional_directories=[]), previous=NOTHING)
    assert merged == {"hooks": {}, "permissions": {"allow": ["Read(//c/a/**)"], "additionalDirectories": []}}


def test_merge_into_permissions_without_allow() -> None:
    merged = merge(settings={"permissions": {"deny": ["Bash(rm:*)"]}}, permissions=Permissions(allow=[], additional_directories=["C:/a"]), previous=NOTHING)
    assert merged == {"permissions": {"deny": ["Bash(rm:*)"], "allow": [], "additionalDirectories": ["C:/a"]}}
