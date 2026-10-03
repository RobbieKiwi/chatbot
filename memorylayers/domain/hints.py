"""Which memory pointers a message deserves: names, aliases, eras, date mentions and summary matches."""

from memorylayers.models.views import HintIndex, HintPointer, TagLine
from memorylayers.models.vocab import SPECIAL_CATEGORIES, TagKind
from memorylayers.tools.tags import singular_form
from memorylayers.tools.text import words

HINT_LIMIT = 3


def _padded(*, tokens: list[str]) -> str:
    return " " + " ".join(tokens) + " "


def _label(*, tag: TagLine) -> str:
    if tag.kind is TagKind.ENTITY:
        return f"{tag.name} (entity, {tag.fact_count} facts)"
    return f"{tag.name} (summary)" if tag.has_summary else f"{tag.name} (category, {tag.fact_count} facts)"


def match_hints(*, message: str, index: HintIndex, mentions: list[list[str]], shown: set[str], limit: int) -> list[HintPointer]:
    tokens = words(text=message)
    padded = _padded(tokens=tokens)
    singular = _padded(tokens=[singular_form(name=token) for token in tokens])
    pointers: dict[str, HintPointer] = {}

    def offer(*, key: str, label: str) -> None:
        if key not in shown and key not in pointers:
            pointers[key] = HintPointer(key=key, label=label)

    tags = {tag.name: tag for tag in index.tags}
    surfaces = {name: name for name in tags} | index.aliases
    # Message order decides which pointers survive the limit.
    found = []
    for surface, name in surfaces.items():
        tag = tags.get(name)
        if tag is None or tag.fact_count == 0 or name in SPECIAL_CATEGORIES:
            continue
        phrase = _padded(tokens=surface.split("_"))
        position = min((text.find(phrase) for text in (padded, singular) if phrase in text), default=-1)
        if position >= 0:
            found.append((position, name))
    for era in index.era_names:
        position = padded.find(_padded(tokens=words(text=era)))
        if position >= 0:
            found.append((position, era))
    for _, key in sorted(found):
        offer(key=key, label=_label(tag=tags[key]) if key in tags else f"{key} (era)")
    for candidates in mentions:
        name = next((candidate for candidate in candidates if candidate in index.period_names), None)
        if name is not None:
            offer(key=name, label=name)
    for key in index.summary_hits:
        offer(key=key, label=_label(tag=tags[key]) if key in tags else key)
    return list(pointers.values())[:limit]


def render_hints(*, pointers: list[HintPointer]) -> str:
    return f"<memory-hints>{' · '.join(pointer.label for pointer in pointers)}</memory-hints>" if pointers else ""
