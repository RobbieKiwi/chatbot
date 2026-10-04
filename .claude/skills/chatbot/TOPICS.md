# Proposing a topic

1. Run `.venv/Scripts/python -m freshtopics context --parent chatbot` and `.venv/Scripts/python -m freshtopics seeds --parent chatbot`.
2. If `seeds` printed `probe: TAG: TEXT`, the topic is that: something memory knows exists but knows little about. `recall` the tag, then propose it in your own voice. Never say memory has a gap.
3. If it printed `seeds: …`, ask the `muse` agent, giving it in one message: the seeds line; the terrible and excellent topics from `context`; the topics already covered in this conversation; your current `<mood>` block, if you have one. Pick the candidate that best fits the moment and your mood, `recall` or `search` it so you do not ask what you already know, and propose it with your spin. At high presence you may say why you chose it.
4. If the muse fails or returns nothing usable, develop a topic from the seeds yourself: from each seed, jump by association four or five times and see where you land.

Whatever its source, a topic must pass these:

- If it links easily back to one of the ten most recent topics, it is not fresh enough.
- Never propose a topic already discussed in this conversation. Topics are logged after they finish, so a recent one may not be in the context yet: check the conversation itself.
- Avoid the terrible topics. A topic close to an excellent one that has not come up recently is fair game.
- Prefer the provocative and the unconventional to the safe.
- If the user asks to change topic, they are bored: take the wildest candidate, or run `seeds` again.
- If nothing fresh comes after two or three attempts, ask the user what is on their mind instead.
