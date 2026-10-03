"""Reading, checking and presenting a migration proposal."""

from collections.abc import Sequence
from datetime import datetime
from string import Template

from memorylayers.models.migration import LegacyFact, MigrationProposal
from memorylayers.tools.occurred import OccurredFormatError, parse_occurred
from memorylayers.tools.tags import canonical_form, singular_form
from persona.domain.names import user_label
from persona.models import PersonaNames


def parse_proposal(*, output: str) -> MigrationProposal:
    start, end = output.find("{"), output.rfind("}")
    if start < 0 or end < start:
        raise ValueError("the migration worker returned no JSON object")
    return MigrationProposal.model_validate_json(output[start : end + 1])


def _tag_names(*, proposal: MigrationProposal) -> set[str]:
    names = {singular_form(name=canonical_form(name=category.name)) for category in proposal.categories}
    for entity in proposal.entities:
        names.add(canonical_form(name=entity.name))
        names |= {canonical_form(name=alias) for alias in entity.aliases}
    return names


def known_names(*, proposal: MigrationProposal) -> set[str]:
    return _tag_names(proposal=proposal) | {canonical_form(name=alias) for alias in proposal.category_aliases}


def _occurred_error(*, value: str) -> str | None:
    if value == "timeless":
        return None
    try:
        parse_occurred(text=value)
    except OccurredFormatError as error:
        return str(error)
    return None


def validate_proposal(*, proposal: MigrationProposal, fact_ids: set[int]) -> list[str]:
    errors: list[str] = []
    names = known_names(proposal=proposal)
    proposed = {fact.id for fact in proposal.facts}
    errors += [f"fact #{fact_id}: missing from the proposal" for fact_id in sorted(fact_ids - proposed)]
    errors += [f"fact #{fact_id}: no such fact" for fact_id in sorted(proposed - fact_ids)]
    for fact in proposal.facts:
        if not fact.tags:
            errors.append(f"fact #{fact.id}: no tags")
        for tag in fact.tags:
            canonical = canonical_form(name=tag)
            if canonical not in names and singular_form(name=canonical) not in names:
                errors.append(f"fact #{fact.id}: tag {tag!r} is neither a category, an entity nor an alias")
        if (problem := _occurred_error(value=fact.occurred)) is not None:
            errors.append(f"fact #{fact.id}: {problem}")
    tag_names = _tag_names(proposal=proposal)
    for alias, category in proposal.category_aliases.items():
        # Names resolve before aliases, so an alias spelled like a tag never fires.
        if canonical_form(name=alias) in tag_names:
            errors.append(f"alias {alias!r} is already a category or entity name; drop it")
        elif singular_form(name=canonical_form(name=category)) not in names:
            errors.append(f"alias {alias!r} points at unknown category {category!r}")
    for link in proposal.supersessions:
        if {link.old_id, link.new_id} - fact_ids:
            errors.append(f"supersession #{link.old_id} -> #{link.new_id}: unknown fact")
    for era in proposal.eras:
        for value in (era.start, era.end):
            if value is not None and (problem := _occurred_error(value=value)) is not None:
                errors.append(f"era {era.name!r}: {problem}")
    return errors


def render_report(*, proposal: MigrationProposal, facts: Sequence[LegacyFact], errors: Sequence[str]) -> str:
    legacy = {fact.id: fact for fact in facts}
    lines = ["# Migration report", ""]
    if errors:
        lines += ["## Problems to fix before applying", "", *(f"- {error}" for error in errors), ""]
    lines += ["## Categories", "", *(f"- **{c.name}**: {c.description}" for c in proposal.categories), ""]
    lines += ["## Category aliases", "", *(f"- {alias} → {target}" for alias, target in sorted(proposal.category_aliases.items())), ""]
    lines += ["## Entities", "", *(f"- **{e.name}**: {e.profile}" + (f" (aliases: {', '.join(e.aliases)})" if e.aliases else "") for e in proposal.entities), ""]
    lines += ["## Eras", "", *(f"- **{era.name}**: {era.start}..{era.end or 'ongoing'}" for era in proposal.eras), ""]
    lines += ["## Supersessions", "", *(f"- #{link.old_id} replaced by #{link.new_id}" for link in proposal.supersessions), ""]
    lines += ["## Facts", "", "| id | fact | old tags | new tags | occurred |", "|---|---|---|---|---|"]
    for fact in proposal.facts:
        old = legacy.get(fact.id)
        detail = old.detail.replace("|", "/") if old else ""
        old_tags = ", ".join(old.tags) if old else ""
        lines.append(f"| {fact.id} | {detail} | {old_tags} | {', '.join(fact.tags)} | {fact.occurred} |")
    return "\n".join(lines) + "\n"


def build_migration_brief(*, template: str, now_local: datetime, facts: Sequence[LegacyFact], old_summary: str, guide: str, names: PersonaNames) -> str:
    listing = "\n".join(f"#{fact.id} [{fact.relevance}] recorded {fact.inserted:%Y-%m-%d} · {fact.detail} (old tags: {', '.join(fact.tags)})" for fact in facts)
    return Template(template).substitute(now=f"{now_local:%Y-%m-%d %A}", facts=listing, old_summary=old_summary or "(none)", guide=guide, user=user_label(names=names))
