"""Claude Code transcript lines read as the visible conversation."""

import json
import re
from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

from memorylayers.models.transcript import Turn
from memorylayers.models.vocab import Role

_HIDDEN_TAGS = (
    "system-reminder",
    "ide_opened_file",
    "ide_selection",
    "command-name",
    "command-message",
    "command-args",
    "local-command-stdout",
    "local-command-stderr",
    "local-command-caveat",
    "memory-hints",
)
_HIDDEN_ALTERNATIVES = "|".join(map(re.escape, _HIDDEN_TAGS))
_HIDDEN = re.compile(rf"<({_HIDDEN_ALTERNATIVES})>.*?</\1>", re.DOTALL)
_SKIP_FLAGS = ("isMeta", "isSidechain", "isCompactSummary")


def parse_turn(*, line: str, line_number: int, session_id: str, tz: ZoneInfo) -> Turn | None:
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        return None
    kind = entry.get("type")
    if kind not in (Role.USER, Role.ASSISTANT) or "toolUseResult" in entry:
        return None
    if any(entry.get(flag) for flag in _SKIP_FLAGS):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        parts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"]
    else:
        return None
    text = _HIDDEN.sub("", "\n".join(parts)).strip()
    if not text:
        return None
    at = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")).astimezone(tz)
    return Turn(role=Role(kind), text=text, at=at, session_id=session_id, line=line_number)


def parse_turns(*, lines: Sequence[str], first_line: int, session_id: str, tz: ZoneInfo) -> list[Turn]:
    turns = (parse_turn(line=line, line_number=first_line + index, session_id=session_id, tz=tz) for index, line in enumerate(lines))
    return [turn for turn in turns if turn is not None]
