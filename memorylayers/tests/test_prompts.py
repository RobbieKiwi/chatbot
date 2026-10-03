from datetime import UTC, date, datetime

from memorylayers.adapters.prompts import load_prompt
from memorylayers.domain.briefs import build_consolidator_brief, build_scribe_brief, build_summariser_brief
from memorylayers.models.config import MemoryConfig
from memorylayers.models.transcript import ScribeWindow
from memorylayers.models.views import RefreshPlan
from persona.models import PersonaNames

NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)
NAMES = PersonaNames(assistant_name="Nova", user_name="Alex")


def test_the_real_templates_fill_without_gaps() -> None:
    scribe = build_scribe_brief(
        template=load_prompt(name="scribe"),
        parent="chatbot",
        run_id="scribe-1",
        conversation_id="c1",
        now_local=NOW,
        window=ScribeWindow(context=[], new=[], end={}),
        rolling_summary="",
        ledger=[],
        pending=[],
        tags=[],
        guide="GUIDE",
        config=MemoryConfig(),
        names=NAMES,
        idle=False,
    )
    assert "commit --run scribe-1 --parent chatbot" in scribe
    assert "GUIDE" in scribe and "$" not in scribe
    assert "about Alex in the third person" in scribe and "conversation with Nova" in scribe
    plan = RefreshPlan(through_revision=1, calendar_week_start=date(2026, 9, 28), tag_names=[], periods=[], expired_periods=[])
    summariser = build_summariser_brief(
        template=load_prompt(name="summariser"),
        parent="chatbot",
        run_id="summariser-1",
        now_local=NOW,
        plan=plan,
        tag_sections=[],
        period_sections=[],
        eras=[],
        core=[],
        preferences=[],
        recent=[],
        high_level_summary="",
        guide="GUIDE",
        names=NAMES,
    )
    assert "refresh commit --run summariser-1 --parent chatbot" in summariser
    assert "$" not in summariser
    consolidator = build_consolidator_brief(template=load_prompt(name="consolidate"), parent="chatbot", run_id="consolidator-1", now_local=NOW, tags=[], aliases={}, facts=[], guide="GUIDE")
    assert "refresh reset --parent chatbot" in consolidator
