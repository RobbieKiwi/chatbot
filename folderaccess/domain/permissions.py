"""Turning the list into Claude Code permissions, and merging them into the local project settings. The list owns only the rules and directories it synced last time; rules the user approved in Claude Code stay."""

import copy

from folderaccess.models.folders import Access, FolderAccess, Permissions


def _rule_path(*, path: str) -> str:
    # Claude Code reads //c/... as an absolute path; C:/Users/x -> //c/Users/x/**
    return f"//{path[0].lower()}{path[2:]}/**"


def to_permissions(*, entries: list[FolderAccess]) -> Permissions:
    """Every listed folder lies outside the project, so each is also an additional directory."""
    allow = []
    for entry in entries:
        allow.append(f"Read({_rule_path(path=entry.path)})")
        if entry.access == Access.EDIT:
            allow.append(f"Edit({_rule_path(path=entry.path)})")
    return Permissions(allow=allow, additional_directories=[entry.path for entry in entries])


def _replace(*, current: list[str], previous: list[str], new: list[str]) -> list[str]:
    kept = [item for item in current if item not in previous]
    return kept + [item for item in new if item not in kept]


def merge(*, settings: dict[str, object], permissions: Permissions, previous: Permissions) -> dict[str, object]:
    """A copy of the settings with the previously synced rules and directories replaced by the new ones; every other rule and key keeps its place."""
    merged = copy.deepcopy(settings)
    section = merged.setdefault("permissions", {})
    assert isinstance(section, dict)
    section["allow"] = _replace(current=section.get("allow", []), previous=previous.allow, new=permissions.allow)
    section["additionalDirectories"] = _replace(current=section.get("additionalDirectories", []), previous=previous.additional_directories, new=permissions.additional_directories)
    return merged
