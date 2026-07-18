"""The tag names a writer passes, turned into canonical tags. New tags are registered only on request."""

from memorylayers.models.views import NewTag, TagResolution, TagVocabulary
from memorylayers.models.vocab import TagKind
from memorylayers.tools.tags import canonical_form, closest_names, resolve_known, singular_form


def parse_new_tag_spec(*, spec: str) -> tuple[str, str]:
    name, separator, description = spec.partition(":")
    if not separator or not name.strip() or not description.strip():
        raise ValueError(f'{spec!r}: expected "name: description"')
    return canonical_form(name=name), description.strip()


def _unknown_tag_message(*, raw: str, canonical: str, vocabulary: TagVocabulary) -> str:
    near = closest_names(name=canonical, candidates=[*vocabulary.kinds, *vocabulary.aliases])
    closest = f" Closest: {', '.join(near)}." if near else ""
    return f'Unknown tag {raw!r}.{closest} Use an existing tag, or register it with --new-entity "{canonical}: <short profile>" or --new-category "{singular_form(name=canonical)}: <description>".'


def _register(*, specs: list[str], kind: TagKind, vocabulary: TagVocabulary, flag: str, names: list[str], to_create: list[NewTag], errors: list[str]) -> None:
    for spec in specs:
        try:
            name, description = parse_new_tag_spec(spec=spec)
        except ValueError as error:
            errors.append(f"{flag} {error}")
            continue
        if kind is TagKind.CATEGORY:
            name = singular_form(name=name)
        known = resolve_known(name=name, vocabulary=vocabulary)
        if known is None:
            to_create.append(NewTag(name=name, kind=kind, description=description))
        names.append(known or name)


def resolve_tags(*, requested: list[str], vocabulary: TagVocabulary, new_categories: list[str], new_entities: list[str]) -> TagResolution:
    names: list[str] = []
    to_create: list[NewTag] = []
    errors: list[str] = []
    for raw in requested:
        try:
            canonical = canonical_form(name=raw)
        except ValueError as error:
            errors.append(str(error))
            continue
        known = resolve_known(name=raw, vocabulary=vocabulary)
        if known is not None:
            names.append(known)
            continue
        new_names = {canonical_form(name=parse_new_tag_spec(spec=spec)[0]) for spec in new_entities if ":" in spec}
        new_names |= {singular_form(name=canonical_form(name=parse_new_tag_spec(spec=spec)[0])) for spec in new_categories if ":" in spec}
        if canonical not in new_names and singular_form(name=canonical) not in new_names:
            errors.append(_unknown_tag_message(raw=raw, canonical=canonical, vocabulary=vocabulary))
    _register(specs=new_categories, kind=TagKind.CATEGORY, vocabulary=vocabulary, flag="--new-category", names=names, to_create=to_create, errors=errors)
    _register(specs=new_entities, kind=TagKind.ENTITY, vocabulary=vocabulary, flag="--new-entity", names=names, to_create=to_create, errors=errors)
    return TagResolution(names=list(dict.fromkeys(names)), to_create=to_create, errors=errors)
