"""Where one parent skill's memory lives on disk."""

from pathlib import Path

from pydantic import BaseModel


class ParentPaths(BaseModel):
    parent: str
    root: Path
    db: Path
    summary: Path  # the high-level summary
    config: Path
