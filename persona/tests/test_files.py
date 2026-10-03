import json
from pathlib import Path
from string import Template

import pytest

from persona.adapters.files import load_names, persona_dir, save_user_name
from persona.models import PersonaError, PersonaNames
from persona.tests.conftest import SCALES, write_persona


def test_a_fresh_clone_uses_the_default_persona(persona_root: Path) -> None:
    assert persona_dir() == persona_root / "default"
    assert load_names() == PersonaNames(assistant_name="Nova", user_name=None)


def test_load_names_prefers_the_local_persona(persona_root: Path) -> None:
    write_persona(folder=persona_root / "local", names={"assistant_name": "Iris", "user_name": "Sam"})
    assert persona_dir() == persona_root / "local"
    assert load_names() == PersonaNames(assistant_name="Iris", user_name="Sam")


def test_save_user_name_creates_the_local_persona_from_the_default(persona_root: Path) -> None:
    names = save_user_name(user_name="Alex")
    local = persona_root / "local"
    assert names == PersonaNames(assistant_name="Nova", user_name="Alex")
    assert json.loads((local / "persona.json").read_text(encoding="utf-8")) == {"assistant_name": "Nova", "user_name": "Alex"}
    assert (local / "PERSONA.md").read_text(encoding="utf-8") == (persona_root / "default" / "PERSONA.md").read_text(encoding="utf-8")
    assert load_names() == names
    assert json.loads((persona_root / "default" / "persona.json").read_text(encoding="utf-8")) == {"assistant_name": "Nova"}


def test_save_user_name_keeps_an_edited_local_persona(persona_root: Path) -> None:
    write_persona(folder=persona_root / "local", names={"assistant_name": "Iris", "user_name": "Sam"}, persona_md="# Iris\n\n" + SCALES + "\n")
    save_user_name(user_name="Alex")
    assert load_names() == PersonaNames(assistant_name="Iris", user_name="Alex")
    assert (persona_root / "local" / "PERSONA.md").read_text(encoding="utf-8").startswith("# Iris")


def test_save_user_name_fills_a_local_folder_that_lacks_persona_json(persona_root: Path) -> None:
    (persona_root / "local").mkdir()
    save_user_name(user_name="Alex")
    assert load_names() == PersonaNames(assistant_name="Nova", user_name="Alex")


@pytest.mark.parametrize("name", ["O'Brien", "$user $$ ${x}", "Mary Jane", "Zoë Ångström", "李明"])
def test_awkward_user_names_survive_the_json_round_trip_and_template_substitution(persona_root: Path, name: str) -> None:
    save_user_name(user_name=name)
    names = load_names()
    assert names.user_name == name
    assert Template("Hello $user, I am $assistant.").substitute(user=names.user_name, assistant=names.assistant_name) == f"Hello {name}, I am Nova."


def test_a_blank_user_name_is_refused(persona_root: Path) -> None:
    with pytest.raises(PersonaError, match="empty"):
        save_user_name(user_name="   ")
    assert not (persona_root / "local").exists()


def test_user_name_is_stripped(persona_root: Path) -> None:
    assert save_user_name(user_name="  Alex \n").user_name == "Alex"


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (None, "missing"),
        ("{ not json", "not valid JSON"),
        ('{"user_name": "Sam"}', "assistant_name"),
        ("[1, 2]", "assistant_name"),
    ],
)
def test_a_broken_local_persona_json_names_the_file(persona_root: Path, content: str | None, reason: str) -> None:
    local = persona_root / "local"
    local.mkdir()
    if content is not None:
        (local / "persona.json").write_text(content, encoding="utf-8")
    with pytest.raises(PersonaError, match=reason) as error:
        load_names()
    assert str(local / "persona.json") in str(error.value)


def test_save_user_name_refuses_a_malformed_local_persona_json(persona_root: Path) -> None:
    local = persona_root / "local"
    local.mkdir()
    (local / "persona.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(PersonaError, match="not valid JSON"):
        save_user_name(user_name="Alex")
    assert (local / "persona.json").read_text(encoding="utf-8") == "{ not json"


def test_the_shipped_default_persona_is_nova_with_no_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERSONA_ROOT", raising=False)
    monkeypatch.setattr("persona.adapters.files.local_dir", lambda: Path("no-such-local-persona"))
    assert load_names() == PersonaNames(assistant_name="Nova")
