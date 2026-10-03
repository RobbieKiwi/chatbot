"""Briefs for headless workers: everything a run needs, and nothing else."""

from collections.abc import Sequence
from datetime import datetime
from string import Template

from memorylayers.domain.due import must_settle
from memorylayers.domain.recall import format_fact
from memorylayers.domain.refresh import format_plan
from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import PendingNote
from memorylayers.models.dates import ONGOING_END
from memorylayers.models.memory import Period
from memorylayers.models.transcript import ScribeWindow, Turn
from memorylayers.models.views import BriefSection, FactLine, RefreshPlan, TagLine
from memorylayers.models.vocab import Role, TagKind
from persona.domain.names import user_label
from persona.models import PersonaNames


def render_turns(*, turns: Sequence[Turn], names: PersonaNames) -> str:
    speakers = {Role.USER: user_label(names=names), Role.ASSISTANT: names.assistant_name}
    return "\n\n".join(f"[{turn.at:%Y-%m-%d %a %H:%M}] {speakers[turn.role]}: {turn.text}" for turn in turns) or "(none)"


def _facts(*, facts: Sequence[FactLine]) -> str:
    return "\n".join(format_fact(fact=fact) for fact in facts) or "(none)"


def _vocabulary(*, tags: Sequence[TagLine]) -> str:
    def listing(kind: TagKind) -> str:
        return "\n".join(f"- {tag.name} ({tag.fact_count}): {tag.description}" for tag in tags if tag.kind is kind) or "(none)"

    return f"Categories (closed):\n{listing(TagKind.CATEGORY)}\n\nEntities:\n{listing(TagKind.ENTITY)}"


def _pending(*, notes: Sequence[PendingNote], settle_runs: int, idle: bool) -> str:
    def line(note: PendingNote) -> str:
        settle = " — MUST SETTLE: promote it with store, or drop it" if must_settle(note=note, settle_runs=settle_runs, idle=idle) else ""
        return f"{note.number}. {note.text} (survived {note.runs_survived} runs){settle}"

    return "\n".join(line(note) for note in notes) or "(none)"


def build_scribe_brief(
    *,
    template: str,
    parent: str,
    run_id: str,
    conversation_id: str,
    now_local: datetime,
    window: ScribeWindow,
    rolling_summary: str,
    ledger: Sequence[FactLine],
    pending: Sequence[PendingNote],
    tags: Sequence[TagLine],
    guide: str,
    config: MemoryConfig,
    names: PersonaNames,
    idle: bool,
) -> str:
    return Template(template).substitute(
        parent=parent,
        run=run_id,
        conversation=conversation_id,
        now=f"{now_local:%Y-%m-%d %A %H:%M %Z}".strip(),
        context_turns=render_turns(turns=window.context, names=names),
        new_turns=render_turns(turns=window.new, names=names),
        rolling_summary=rolling_summary or "(empty: this conversation has just begun)",
        ledger=_facts(facts=ledger),
        pending=_pending(notes=pending, settle_runs=config.pending_settle_runs, idle=idle),
        tags=_vocabulary(tags=tags),
        guide=guide,
        user=user_label(names=names),
        assistant=names.assistant_name,
    )


def _section(*, section: BriefSection) -> str:
    parts = [f"### {section.title}", "Existing summary:", section.existing_summary or "(none)", "Facts:", _facts(facts=section.facts)]
    if section.child_summaries:
        parts += ["Summaries of the periods inside it:", *(f"- {name}: {summary}" for name, summary in section.child_summaries.items())]
    return "\n".join(parts)


def _period_line(*, period: Period) -> str:
    end = "ongoing" if period.end == ONGOING_END else period.end.isoformat()
    return f"- {period.name}: {period.start}..{end}"


def build_summariser_brief(
    *,
    template: str,
    parent: str,
    run_id: str,
    now_local: datetime,
    plan: RefreshPlan,
    tag_sections: Sequence[BriefSection],
    period_sections: Sequence[BriefSection],
    eras: Sequence[Period],
    core: Sequence[FactLine],
    preferences: Sequence[FactLine],
    recent: Sequence[Period],
    high_level_summary: str,
    guide: str,
    names: PersonaNames,
) -> str:
    return Template(template).substitute(
        parent=parent,
        run=run_id,
        now=f"{now_local:%Y-%m-%d %A %H:%M %Z}".strip(),
        plan=format_plan(plan=plan),
        tag_sections="\n\n".join(_section(section=section) for section in tag_sections) or "(none due)",
        period_sections="\n\n".join(_section(section=section) for section in period_sections) or "(none due)",
        eras="\n".join(_period_line(period=era) for era in eras) or "(none yet)",
        core=_facts(facts=core),
        preferences=_facts(facts=preferences),
        recent="\n".join(f"- {period.name}: {period.summary}" for period in recent if period.summary) or "(none)",
        high_level_summary=high_level_summary or "(none yet)",
        guide=guide,
        user=user_label(names=names),
        assistant=names.assistant_name,
    )


def build_consolidator_brief(*, template: str, parent: str, run_id: str, now_local: datetime, tags: Sequence[TagLine], aliases: dict[str, str], facts: Sequence[FactLine], guide: str) -> str:
    return Template(template).substitute(
        parent=parent,
        run=run_id,
        now=f"{now_local:%Y-%m-%d %A %H:%M %Z}".strip(),
        tags=_vocabulary(tags=tags),
        aliases="\n".join(f"- {alias} -> {tag}" for alias, tag in sorted(aliases.items())) or "(none)",
        facts=_facts(facts=facts),
        guide=guide,
    )
