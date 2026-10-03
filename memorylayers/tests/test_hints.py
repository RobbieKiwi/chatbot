from memorylayers.domain.hints import match_hints, render_hints
from memorylayers.models.views import HintIndex, TagLine
from memorylayers.models.vocab import TagKind

INDEX = HintIndex(
    tags=[
        TagLine(name="jordan", kind=TagKind.ENTITY, description="", fact_count=5, has_summary=True),
        TagLine(name="friend", kind=TagKind.CATEGORY, description="", fact_count=9, has_summary=True),
        TagLine(name="canada", kind=TagKind.ENTITY, description="", fact_count=4, has_summary=False),
        TagLine(name="core", kind=TagKind.CATEGORY, description="", fact_count=6, has_summary=False),
        TagLine(name="ghost", kind=TagKind.ENTITY, description="", fact_count=0, has_summary=False),
    ],
    aliases={"ca": "canada"},
    period_names=["2026 Q3", "2014"],
    era_names=["Portugal"],
)


def test_names_aliases_plurals_and_periods_become_pointers() -> None:
    pointers = match_hints(message="My friends and Jordan, last summer", index=INDEX, mentions=[["2026 Q3", "2026"]], shown=set(), limit=3)
    # Pointers follow the message: "friends" comes before "Jordan".
    assert render_hints(pointers=pointers) == "<memory-hints>friend (summary) · jordan (entity, 5 facts) · 2026 Q3</memory-hints>"


def test_shown_pointers_are_not_repeated_and_the_limit_holds() -> None:
    pointers = match_hints(message="Jordan in CA, then Portugal", index=INDEX, mentions=[], shown={"jordan"}, limit=3)
    assert [pointer.key for pointer in pointers] == ["canada", "Portugal"]


def test_core_and_empty_tags_are_never_hinted() -> None:
    assert match_hints(message="core ghost", index=INDEX, mentions=[], shown=set(), limit=3) == []
    assert render_hints(pointers=[]) == ""
