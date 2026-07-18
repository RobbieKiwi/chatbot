import pytest

from memorylayers.models.views import TagVocabulary
from memorylayers.models.vocab import TagKind
from memorylayers.tools.tags import canonical_form, closest_names, resolve_known, singular_form


@pytest.mark.parametrize(("raw", "canonical"), [("Jordan", "jordan"), ("Canada", "canada"), (" agent-preferences ", "agent_preferences")])
def test_canonical_form(raw: str, canonical: str) -> None:
    assert canonical_form(name=raw) == canonical


@pytest.mark.parametrize(("name", "singular"), [("friends", "friend"), ("hobbies", "hobby"), ("glass", "glass"), ("bus", "bus"), ("music", "music")])
def test_singular_form(name: str, singular: str) -> None:
    assert singular_form(name=name) == singular


def test_resolve_known_uses_names_aliases_and_singulars() -> None:
    vocabulary = TagVocabulary(kinds={"friend": TagKind.CATEGORY, "berlin": TagKind.ENTITY}, aliases={"bln": "berlin"})
    assert resolve_known(name="Friends", vocabulary=vocabulary) == "friend"
    assert resolve_known(name="BLN", vocabulary=vocabulary) == "berlin"
    assert resolve_known(name="Berlin", vocabulary=vocabulary) == "berlin"
    assert resolve_known(name="bonn", vocabulary=vocabulary) is None


def test_closest_names() -> None:
    assert closest_names(name="jordn", candidates=["jordan", "riley", "jordy"]) == ["jordan", "jordy"]


def test_empty_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        canonical_form(name=" -- ")
