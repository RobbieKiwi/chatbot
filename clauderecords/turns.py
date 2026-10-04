"""The last text turns of a Claude Code transcript, and how they read as plain text."""

import json
import re
from pathlib import Path

from clauderecords.models import Role, TextTurn

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
    "curiosity",
    "mood",
)
_HIDDEN_ALTERNATIVES = "|".join(map(re.escape, _HIDDEN_TAGS))
_HIDDEN = re.compile(rf"<({_HIDDEN_ALTERNATIVES})\b[^>]*>.*?</\1>", re.DOTALL)
_SKIP_FLAGS = ("isMeta", "isSidechain", "isCompactSummary")


def _text_turn(*, line: str) -> TextTurn | None:
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(entry, dict):
        return None
    kind = entry.get("type")
    if kind not in (Role.USER, Role.ASSISTANT) or "toolUseResult" in entry or any(entry.get(flag) for flag in _SKIP_FLAGS):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        parts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"]
    else:
        return None
    text = _HIDDEN.sub("", "\n".join(parts)).strip()
    return TextTurn(role=Role(kind), text=text) if text else None


def last_text_turns(*, transcript_path: Path, count: int) -> list[TextTurn]:
    if count <= 0:
        return []
    try:
        text = transcript_path.read_bytes().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return []
    complete, _, _ = text.rpartition("\n")  # a final line still being written is left out
    turns = (_text_turn(line=line) for line in complete.split("\n"))
    return [turn for turn in turns if turn is not None][-count:]


def render_turns(*, turns: list[TextTurn], user_name: str, assistant_name: str) -> str:
    names = {Role.USER: user_name, Role.ASSISTANT: assistant_name}
    return "\n\n".join(f"{names[turn.role]}: {turn.text}" for turn in turns)
