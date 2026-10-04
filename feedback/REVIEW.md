# Reviewing feedback on the assistant

The user files feedback mid-conversation with `fb: <text>` (or `fb: #id <text>` to add to an item). Each item carries the ten turns before it. This is the offline review that turns it into prompt changes.

Commands, from the project root:

```bash
.venv/Scripts/python -m feedback open --parent chatbot
.venv/Scripts/python -m feedback show ID --parent chatbot
.venv/Scripts/python -m feedback record-change --summary "..." --files a,b --resolved 3,7 --partly 5 --parent chatbot
.venv/Scripts/python -m feedback history --parent chatbot
```

## Steps

1. Run `open`. Read each item's context with `show ID`: judge the behaviour from what the assistant actually said, not from the one-line complaint alone.
2. Group related items. Read the prompt files they concern — usually the `PERSONA.md` that `.venv/Scripts/python -m persona show` names, `.claude/skills/chatbot/TOPICS.md`, `SKILL.md`, `.claude/agents/muse.md` or `mood/prompts/observer.md` — and propose edits to the user. For each partly-addressed item, say what was already tried (its changes are listed under it) and why this edit goes further.
3. Apply the edits the user approves. Write each prompt file as the character and rules stand now, with no notes about what changed.
4. Run `record-change` once per coherent edit, with `--resolved` or `--partly` for every item it addresses. An item the user reopens later with `fb: #id` shows up in `open` again on its own.

`fb:` tunes the prompts. A request the user makes in the conversation itself ("don't ask about sport") belongs in memory under `agent_preferences`, where the scribe files it; it is not a prompt change.
