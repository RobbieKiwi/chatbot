You are migrating a flat memory of $user into a layered memory. Today is $now. You have no tools: answer with a single JSON object and nothing else.

## Memory guide

$guide

## The old high-level summary (for context, especially for eras)

$old_summary

## Every fact, with its old tags

Each line is `#id [relevance] recorded <date> · fact (old tags: ...)`. "recorded" is when the fact was said, not when it happened.

$facts

## What to produce

1. A small, closed vocabulary of **categories** (singular, general: friend, family, work, music, dance, home, education, …), each with a one-line description. Keep `core` and `agent_preferences`.
2. **Entities**: every person, place and organisation, each with a short profile drawn from the facts, and aliases for nicknames and alternative spellings.
3. **Category aliases**: only synonyms, plurals and spelling variants that will mean that category wherever they appear in future (`"friends": "friend"`, `"tango": "dance"`). An alias is permanent: every later mention of the word resolves to its category. An old tag needs no alias just because its facts moved, since each fact carries its new tags directly; leave out any word that only fit its old facts in context (`"alcohol"` on a night out is not `friend`).
4. For **every fact**, its new tags (categories and entities, by name or alias) and when it occurred: `YYYY-MM-DD`, `YYYY-MM`, `YYYY`, `YYYYs`, a range `A..B`, `unknown` for an event with no known date, or `timeless` for a standing trait. Resolve dates the fact implies ("the start of this month", "last year") against its recorded date. Old date tags (`2020`, `march`) become `occurred`, never tags.
5. **Supersessions** where a later fact replaces an earlier one as current.
6. **Eras**: named, irregular periods of $user's life bounded by life events (early childhood, university, the years abroad …), each with a start and an end (`null` while ongoing), in `occurred` format.

## Format

{"categories": [{"name": "friend", "description": "People $user is close to"}],
 "entities": [{"name": "jordan", "profile": "Friend from tango", "aliases": ["jordy"]}],
 "category_aliases": {"friends": "friend"},
 "facts": [{"id": 12, "tags": ["jordan", "friend"], "occurred": "2026-07"}],
 "supersessions": [{"old_id": 3, "new_id": 40}],
 "eras": [{"name": "Lisbon", "start": "2019-03", "end": "2021-06"}]}

Every fact id above must appear exactly once in `facts`.
