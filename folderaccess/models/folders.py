"""The folders the assistant may read or edit, and the Claude Code permissions they become."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Access(StrEnum):
    READ = "read"
    EDIT = "edit"  # implies read


class FolderAccess(BaseModel):
    """One line of the list."""

    model_config = ConfigDict(extra="forbid")

    path: str  # absolute, forward slashes, upper-case drive letter, no trailing slash
    access: Access


class Permissions(BaseModel):
    """The part of the project settings the list owns."""

    model_config = ConfigDict(extra="forbid")

    allow: list[str]  # the Read(…) and Edit(…) rules, in list order
    additional_directories: list[str]
