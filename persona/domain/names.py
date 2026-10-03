"""How prompts name the user."""

from persona.models import PersonaNames

UNNAMED_USER = "the user"


def user_label(*, names: PersonaNames) -> str:
    return names.user_name or UNNAMED_USER
