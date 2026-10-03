"""
The assistant's persona: its name and the user's, read from `persona.json` beside the character file `PERSONA.md`.

The shipped persona sits in `default/`; a user's own copy in `local/` (gitignored) takes its place whenever it exists.
"""

from pydantic import BaseModel, ConfigDict


class PersonaError(ValueError):
    """A persona file is missing or unusable. The message names the file."""


class PersonaNames(BaseModel):
    model_config = ConfigDict(frozen=True)

    assistant_name: str
    user_name: str | None = None  # unset until the user says it; prompts then say "the user"
