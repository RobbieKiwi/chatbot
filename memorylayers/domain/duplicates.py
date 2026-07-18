"""Whether a new fact repeats one already stored."""

from memorylayers.models.views import FactCandidate
from memorylayers.models.vocab import TagKind
from memorylayers.tools.text import content_tokens, jaccard


def close_matches(*, detail: str, tags: list[str], kinds: dict[str, TagKind], candidates: list[FactCandidate], threshold: float) -> list[FactCandidate]:
    """Candidates sharing an entity tag (or a category, when the new fact names no entity) whose wording overlaps enough."""
    entities = {tag for tag in tags if kinds.get(tag) is TagKind.ENTITY}
    required = entities or set(tags)
    tokens = content_tokens(text=detail)
    return [candidate for candidate in candidates if required & set(candidate.tags) and jaccard(a=tokens, b=content_tokens(text=candidate.detail)) >= threshold]
