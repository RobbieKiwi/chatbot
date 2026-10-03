from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from memorylayers.domain.briefs import build_scribe_brief, render_turns
from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import PendingNote
from memorylayers.models.transcript import ScribeWindow, Turn
from memorylayers.models.views import FactLine, TagLine
from memorylayers.models.vocab import Role, TagKind
from persona.models import PersonaNames

BERLIN = ZoneInfo("Europe/Berlin")
AT = datetime(2026, 10, 1, 23, 31, tzinfo=UTC).astimezone(BERLIN)
TEMPLATE = "Run $run for $conversation at $now\n$user with $assistant\nOLD\n$context_turns\nNEW\n$new_turns\n$ledger\n$pending\n$tags\n$guide\n$$5"
NAMES = PersonaNames(assistant_name="Nova", user_name="Alex")


def test_turns_are_stamped_with_their_local_date() -> None:
    turn = Turn(role=Role.USER, text="Yesterday I went dancing.", at=AT, session_id="s", line=1)
    assert render_turns(turns=[turn], names=NAMES) == "[2026-10-02 Fri 01:31] Alex: Yesterday I went dancing."


def test_turns_of_an_unnamed_user_are_the_users() -> None:
    turn = Turn(role=Role.USER, text="Hi.", at=AT, session_id="s", line=1)
    assert render_turns(turns=[turn], names=PersonaNames(assistant_name="Nova")) == "[2026-10-02 Fri 01:31] the user: Hi."


def _scribe_brief(*, names: PersonaNames) -> str:
    window = ScribeWindow(context=[], new=[Turn(role=Role.ASSISTANT, text="Tango?", at=AT, session_id="s", line=2)], end={"s": 3})
    return build_scribe_brief(
        template=TEMPLATE,
        parent="pk",
        run_id="scribe-1",
        conversation_id="c1",
        now_local=AT,
        window=window,
        rolling_summary="",
        ledger=[FactLine(id=4, detail="Alex dances tango", occurred="timeless", relevance=6, tags=["dance"])],
        pending=[PendingNote(number=1, text="may move to Bonn", runs_survived=2)],
        tags=[TagLine(name="dance", kind=TagKind.CATEGORY, description="dancing", fact_count=1, has_summary=False)],
        guide="GUIDE",
        config=MemoryConfig(),
        names=names,
        idle=False,
    )


def test_scribe_brief_carries_everything_the_run_needs() -> None:
    brief = _scribe_brief(names=NAMES)
    assert brief.startswith("Run scribe-1 for c1 at 2026-10-02 Friday 01:31") and "Alex with Nova" in brief.splitlines()[1]
    assert "(none)" in brief.split("NEW")[0]
    assert "Nova: Tango?" in brief
    assert "#4 [6] timeless · Alex dances tango (dance)" in brief
    assert "1. may move to Bonn (survived 2 runs) — MUST SETTLE" in brief
    assert "- dance (1): dancing" in brief
    assert brief.endswith("$5")


def test_scribe_brief_for_an_unnamed_user_says_the_user() -> None:
    assert "\nthe user with Nova\n" in _scribe_brief(names=PersonaNames(assistant_name="Nova"))


def test_awkward_names_survive_the_scribe_brief() -> None:
    brief = _scribe_brief(names=PersonaNames(assistant_name="Zoë", user_name="O'Brien $user"))
    assert "\nO'Brien $user with Zoë\n" in brief and "Zoë: Tango?" in brief


def test_the_config_holds_no_names() -> None:
    assert "user_name" not in MemoryConfig.model_fields and "assistant_name" not in MemoryConfig.model_fields
