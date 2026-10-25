"""Turning the list into Claude Code permissions, and merging them into the local project settings. The list owns every Read(…) and Edit(…) rule and the whole of additionalDirectories."""

import copy

from folderaccess.models.folders import Access, FolderAccess, Permissions

OWNED_RULE_PREFIXES = ("Read(", "Edit(")


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


def merge(*, settings: dict[str, object], permissions: Permissions) -> dict[str, object]:
    """A copy of the settings with the owned rules and directories replaced; every other rule and key keeps its place."""
    merged = copy.deepcopy(settings)
    section = merged.setdefault("permissions", {})
    assert isinstance(section, dict)
    kept = [rule for rule in section.get("allow", []) if not rule.startswith(OWNED_RULE_PREFIXES)]
    section["allow"] = kept + permissions.allow
    section["additionalDirectories"] = permissions.additional_directories
    return merged
