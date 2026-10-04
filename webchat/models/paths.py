"""Where webchat keeps its files."""

from pathlib import Path

from pydantic import BaseModel


class WebchatPaths(BaseModel):
    root: Path
    config: Path
    state: Path
    conversations: Path  # one display log per Claude Code session
    logs: Path
