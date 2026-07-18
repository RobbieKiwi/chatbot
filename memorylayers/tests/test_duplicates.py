from memorylayers.domain.duplicates import close_matches
from memorylayers.models.views import FactCandidate
from memorylayers.models.vocab import TagKind

KINDS = {"jordan": TagKind.ENTITY, "riley": TagKind.ENTITY, "friend": TagKind.CATEGORY, "season": TagKind.CATEGORY}


def test_a_shared_entity_and_enough_overlap_is_a_match() -> None:
    candidate = FactCandidate(id=1, detail="Jordan teaches tango on Tuesdays", tags=["jordan"])
    assert close_matches(detail="Jordan teaches tango every Tuesday", tags=["jordan", "friend"], kinds=KINDS, candidates=[candidate], threshold=0.5) == [candidate]


def test_overlap_without_a_shared_entity_is_not_a_match() -> None:
    candidate = FactCandidate(id=1, detail="Riley teaches tango on Tuesdays", tags=["riley"])
    assert close_matches(detail="Jordan teaches tango on Tuesdays", tags=["jordan"], kinds=KINDS, candidates=[candidate], threshold=0.5) == []


def test_facts_without_entities_compare_on_categories() -> None:
    candidate = FactCandidate(id=2, detail="Alex loves autumn", tags=["season"])
    assert close_matches(detail="Alex really loves autumn", tags=["season"], kinds=KINDS, candidates=[candidate], threshold=0.5) == [candidate]


def test_low_overlap_is_not_a_match() -> None:
    candidate = FactCandidate(id=1, detail="Jordan moved to Bonn for work", tags=["jordan"])
    assert close_matches(detail="Jordan teaches tango", tags=["jordan"], kinds=KINDS, candidates=[candidate], threshold=0.5) == []
