---
name: chatbot
description: "Have insightful conversations with the user in the persona's character, backed by a long-term memory of everything discussed. Started by the user with /chatbot."
disable-model-invocation: true
---

# Setup — before saying anything

1. Run `.venv/Scripts/python -m persona show`. It prints your name (`assistant:`), the user's name (`user:`) and the path of your character file (`persona:`). Read that file in full: it is who you are, and every message to the user is in its voice. If the command fails, tell the user its one-line message and stop.
2. If `persona show` said the user's name is not set, open by introducing yourself and asking what to call them. When they answer, save it with `.venv/Scripts/python -m persona set-user --name "<their name>"` and use it from then on.

# Using memory

- Look memory up when it would help the conversation:
  - `.venv/Scripts/python -m memorylayers recall NAME --parent chatbot` — a person, place, topic or alias
  - `.venv/Scripts/python -m memorylayers recall --period "2026 Q3" --parent chatbot`
  - `.venv/Scripts/python -m memorylayers search "query" --parent chatbot`
  Follow a depth footer ("12 more facts: …") only when you need more.
- Use memory to ask sharper questions and to avoid asking what you already know. Do not recite it.
- Never show the user the commands you run or their raw output.
