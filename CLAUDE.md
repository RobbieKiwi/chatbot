## Skills

- `chatbot` — conversation with the assistant in its persona's character; start it with `/chatbot`. Its skill files are in `.claude/skills/chatbot/`.
- The `persona` package holds the persona: `persona/default/` ships the character Nova (`PERSONA.md`) and `persona.json` (`assistant_name`); a user's own copy in `persona/local/` (gitignored) takes its place whenever it exists, and holds the `user_name`. `.venv/Scripts/python -m persona show` prints both names and the `PERSONA.md` in use; `.venv/Scripts/python -m persona set-user --name NAME` saves the user's name, creating `persona/local/` from the default. Until the user's name is set, prompts say "the user".
- Its memory is the `memorylayers` package and its topic history the `freshtopics` package, both at the project root. Each package writes its runtime data under its own `data/`, which is gitignored. Agents reach the packages only through their CLIs: `.venv/Scripts/python -m memorylayers --help` and `.venv/Scripts/python -m freshtopics --help`.
- `memorylayers/data/chatbot/config.json`, when present, overrides the `MemoryConfig` defaults, such as `local_timezone` (an IANA zone name, `UTC` by default) for the dates memory shows.

## Python

Python 3.13, managed with uv. The gate is `make all`, run from the project root:

```bash
make all
```

It runs, in order and stopping at the first failure, the `Makefile` targets `format` (ruff format), `lint` (ruff check --fix), `types` (ty check), `imports` (lint-imports) and `test` (pytest). Each target can also be run on its own.

Fix anything ruff cannot fix itself.

## Git

- The main branch is `master`. Work on a feature branch and merge it once it is ready.
- Every commit passes `make all`.
