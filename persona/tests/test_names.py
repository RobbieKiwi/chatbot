from persona.domain.names import user_label
from persona.models import PersonaNames


def test_user_label_is_the_user_name_when_set() -> None:
    assert user_label(names=PersonaNames(assistant_name="Nova", user_name="Alex")) == "Alex"


def test_user_label_is_the_user_until_the_name_is_set() -> None:
    assert user_label(names=PersonaNames(assistant_name="Nova")) == "the user"
