from memorylayers.domain.tag_resolution import resolve_tags
from memorylayers.models.views import NewTag, TagVocabulary
from memorylayers.models.vocab import TagKind

VOCABULARY = TagVocabulary(kinds={"friend": TagKind.CATEGORY, "jordan": TagKind.ENTITY, "core": TagKind.CATEGORY}, aliases={"jordy": "jordan"})


def test_known_names_aliases_and_plurals_resolve() -> None:
    resolution = resolve_tags(requested=["Friends", "jordy"], vocabulary=VOCABULARY, new_categories=[], new_entities=[])
    assert resolution.names == ["friend", "jordan"]
    assert resolution.errors == []


def test_an_unknown_tag_is_an_actionable_error() -> None:
    resolution = resolve_tags(requested=["jordn"], vocabulary=VOCABULARY, new_categories=[], new_entities=[])
    assert len(resolution.errors) == 1
    assert "Closest: jordan" in resolution.errors[0]
    assert '--new-entity "jordn: <short profile>"' in resolution.errors[0]


def test_new_tags_register_and_are_applied() -> None:
    resolution = resolve_tags(requested=["dance"], vocabulary=VOCABULARY, new_categories=["dances: dancing of any kind"], new_entities=["Blue Note: a tango festival in Tiergarten"])
    assert resolution.errors == []
    assert resolution.names == ["dance", "blue_note"]
    assert resolution.to_create == [
        NewTag(name="dance", kind=TagKind.CATEGORY, description="dancing of any kind"),
        NewTag(name="blue_note", kind=TagKind.ENTITY, description="a tango festival in Tiergarten"),
    ]


def test_a_malformed_spec_is_an_error() -> None:
    resolution = resolve_tags(requested=[], vocabulary=VOCABULARY, new_categories=["dance"], new_entities=[])
    assert resolution.errors and "name: description" in resolution.errors[0]
