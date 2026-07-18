"""Tag names: canonical forms, alias resolution and near-spellings."""

import difflib
import re
from collections.abc import Iterable

from memorylayers.models.views import TagVocabulary


def canonical_form(*, name: str) -> str:
    """Lowercase words joined by underscores."""
    parts = re.findall(r"[a-z0-9]+", name.lower())
    if not parts:
        raise ValueError(f"tag name {name!r} has no letters or digits")
    return "_".join(parts)


def singular_form(*, name: str) -> str:
    """Categories are singular; entities keep their own spelling and never pass through here."""
    head, _, last = name.rpartition("_")
    if len(last) > 3 and last.endswith("ies"):
        last = last[:-3] + "y"
    elif len(last) > 3 and last.endswith("s") and not last.endswith(("ss", "us", "is")):
        last = last[:-1]
    return f"{head}_{last}" if head else last


def resolve_known(*, name: str, vocabulary: TagVocabulary) -> str | None:
    canonical = canonical_form(name=name)
    for candidate in (canonical, singular_form(name=canonical)):
        if candidate in vocabulary.kinds:
            return candidate
        if candidate in vocabulary.aliases:
            return vocabulary.aliases[candidate]
    return None


def closest_names(*, name: str, candidates: Iterable[str], limit: int = 3) -> list[str]:
    return difflib.get_close_matches(name, list(candidates), n=limit, cutoff=0.6)
