# chatbot

**A friendly chatbot with a human touch and a deep persistent memory.**

`chatbot` turns [Claude Code](https://claude.com/claude-code) into a companion you talk to over
weeks and months. It runs as a Claude Code skill with a set of hooks and small Python packages,
and everything it learns about you stays on your machine.

## Features

- **A personality you can customise.** One persona file and one small config set the character,
  its name and your name. The shipped character is Nova: witty, curious and a little sarcastic.
- **Interesting conversations.** Fresh topics are developed from random seed words and subjects,
  steered away from what you have already talked about and from topics you dislike
  (`freshtopics`).
- **Deep, local memory.** What you tell it is filed as facts in layered memory on your machine:
  facts, tag summaries, periods and a high-level summary, refreshed and consolidated by headless
  workers in the background (`memorylayers`).
- **Only the context it needs.** Instead of loading everything it knows, memory hints on each
  message and a librarian agent pull in what the conversation calls for.
- **A mood that moves.** Five mood scales — cheerfulness, playfulness, irritation, melancholy and
  restlessness — are rolled for each session and nudged by an observer as the conversation goes
  (`mood`).
- **Webchat.** A chat page for talking to the assistant from any device on your local network
  (`webchat`).

Feedback typed as `fb: <text>` mid-conversation is filed for an offline review of the prompts
(`feedback`), and `folderaccess` lets the assistant read or edit folders you choose outside the
project.

## Requirements

- [Claude Code](https://claude.com/claude-code), signed in
- [uv](https://docs.astral.sh/uv/)
- Python 3.13 (uv installs it if needed)
- Windows: the hooks, skill and agents run `.venv/Scripts/python`, and folder access expects drive-letter paths

## Setup

```bash
git clone <this repo> chatbot
cd chatbot
uv sync
```

Every package writes its runtime data under its own `data/` folder, which is gitignored, so a
fresh clone starts with an empty memory.

## Talking to it

Start Claude Code in the project folder and run the skill:

```bash
claude
> /chatbot
```

On the first conversation the assistant asks your name and saves it. The hooks in
`.claude/settings.json` run on every message: they add memory hints and the assistant's mood,
file `fb:` feedback, and launch the background workers that file memory.

Memory settings live in `memorylayers/data/chatbot/config.json`; set `local_timezone` there
(an IANA name such as `Europe/Berlin`, `UTC` by default) so dates in memory match your day.

## Customising the persona

The shipped persona is in `persona/default/`: `PERSONA.md` holds the character and the
descriptions of each mood level, and `persona.json` holds the names. To make your own, copy it
to `persona/local/`, which is gitignored and takes its place whenever it exists:

```bash
cp -r persona/default persona/local
```

Then edit `persona/local/PERSONA.md` and `persona/local/persona.json`:

```json
{"assistant_name": "Nova", "user_name": "Alex"}
```

Check what is in use with:

```bash
uv run python -m persona show
```

## Webchat

Set a passphrase, then start the server:

```bash
uv run python -m webchat.scripts.set_passphrase
uv run python -m webchat
```

Open `http://<this pc>:8765` from any device on the same network. The webchat drives Claude Code
headless through the Agent SDK; its files and log are under `webchat/data/`.

## Development

The gate runs ruff format, ruff check, ty, import-linter and pytest, stopping at the first
failure:

```bash
make all
```
