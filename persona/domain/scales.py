"""Cutting the mood-scale table out of a persona's character file."""

import re

SCALE_HEADER = re.compile(r"^\s*\|\s*scale\s*\|", flags=re.IGNORECASE)


def cut_mood_scales(*, persona_md: str) -> str | None:
    """The markdown table whose header row starts `| Scale |`, header and separator included; None without one holding at least one row."""
    lines = persona_md.splitlines()
    for start, line in enumerate(lines):
        if SCALE_HEADER.match(line):
            table = []
            for row in lines[start:]:
                if not row.strip().startswith("|"):
                    break
                table.append(row.rstrip())
            return "\n".join(table) if len(table) >= 3 else None
    return None
