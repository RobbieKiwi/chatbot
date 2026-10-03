# Memory guide: chatbot

What the assistant's memory of the user keeps, and how it is filed. Read by the scribe, the summariser and the consolidator. The brief names the user; the examples below use a user called Alex.

## Relevance

- **10** Core identity: name, age, origin, partner's name, current job.
- **9** Major life events: moves, big purchases, major changes.
- **8** Important details and strong preferences.
- **7** Activities, routines, habits; feelings the user elaborates on.
- **6** Work details and experiences: projects, tools.
- **5** General facts and relationship details.
- **4** Minor preferences and details.
- **3** Places and contextual details.
- **2** Temporary issues: arguments, short-term concerns.
- **1** Trivial facts.

Below 1 is not stored at all.

## Not stored

- Small talk: "how are you?" "good" is not a fact.
- Answers to silly questions in a silly exchange.
- Questions the user asks.
- Feedback on conversation topics; the topic log holds that.
- The assistant's own words and opinions.

A feeling is stored when the user elaborates on it in a serious conversation (relevance 7), not when it is mentioned in passing.

## Special categories

- `core`: the few facts that define the user: name, home, partner, job, family. Keep it small.
- `agent_preferences`: how the assistant should behave ("don't ask about sport"). Not the user's own tastes in food, music or anything else.

## Tagging

- Facts are about the user, by name, in English, in the third person: "Alex's friend Jordan teaches tango".
- Tag every person, place and organisation a fact names as an entity: `jordan`, `lisbon`, `acme`.
- Add one to three categories: `friend`, `family`, `work`, `music`, `dance`, `home`, `education`.
- Dates go in `--occurred`, never in tags: no `2020`, no `march`.
- If the user already has a friend called Sam in memory and says "Sam likes chocolate", store "Sam likes chocolate", not "Alex has a friend called Sam who likes chocolate".

Examples:

| Fact | Tags | Occurred | Relevance |
|---|---|---|---|
| Alex was born in June 1990 | `core` | `1990-06` | 10 |
| Alex enjoys hiking in the mountains at weekends | `hobby`, `outdoors` | timeless | 7 |
| Alex works as a software engineer at Acme | `core`, `work`, `acme` | unknown | 10 |
| Alex moved into a new apartment in Lisbon with Jordan | `home`, `lisbon`, `jordan` | `2025-04` | 9 |
| Sam is a friend of Alex's | `friend`, `sam` | timeless | 8 |
| Alex graduated from university | `education` | `2014` | 9 |
