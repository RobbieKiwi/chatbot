"""Claude Code transcript files: the record of every conversation."""

import re
from pathlib import Path
from zoneinfo import ZoneInfo

from memorylayers.models.conversation import ConversationState
from memorylayers.models.transcript import ConversationTurns, Turn
from memorylayers.tools.transcript import parse_turns


def read_complete_lines(*, path: Path) -> list[str]:
    """Every line that ends in a newline; a final line still being written is left for next time."""
    try:
        text = path.read_bytes().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return []
    complete, _, _ = text.rpartition("\n")
    return complete.split("\n") if complete else []


def read_conversation_turns(*, state: ConversationState, tz: ZoneInfo, include_processed: bool = True) -> ConversationTurns:
    processed: list[Turn] = []
    unprocessed: list[Turn] = []
    ends: dict[str, int] = {}
    for link in state.sessions:
        lines = read_complete_lines(path=link.transcript_path)
        ends[link.session_id] = len(lines)
        if include_processed:
            processed += parse_turns(lines=lines[: link.processed_line], first_line=0, session_id=link.session_id, tz=tz)
        unprocessed += parse_turns(lines=lines[link.processed_line :], first_line=link.processed_line, session_id=link.session_id, tz=tz)
    return ConversationTurns(processed=processed, unprocessed=unprocessed, ends=ends)


def project_transcript_dir(*, project_dir: Path, home: Path) -> Path | None:
    """Claude Code's transcript folder for a project: its path with every non-alphanumeric turned into '-'."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(project_dir)).lower()
    root = home / ".claude" / "projects"
    if not root.exists():
        return None
    return next((folder for folder in root.iterdir() if folder.is_dir() and folder.name.lower() == slug), None)


def newest_session(*, project_dir: Path, home: Path) -> tuple[str, Path] | None:
    folder = project_transcript_dir(project_dir=project_dir, home=home)
    transcripts = list(folder.glob("*.jsonl")) if folder else []
    if not transcripts:
        return None
    newest = max(transcripts, key=lambda path: path.stat().st_mtime_ns)
    return newest.stem, newest
