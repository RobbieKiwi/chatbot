from pathlib import Path

import pytest

import webchat.__main__
from webchat.adapters.files import write_config
from webchat.domain.auth import new_passphrase_record
from webchat.models.config import WebchatConfig
from webchat.models.paths import WebchatPaths


def test_serve_with_a_broken_persona_stops_naming_the_file(paths: WebchatPaths, shipped_persona: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_config(paths=paths, config=WebchatConfig(passphrase=new_passphrase_record(passphrase="correct horse")))
    local = shipped_persona / "local"
    local.mkdir()
    (local / "persona.json").write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(webchat.__main__.uvicorn, "run", lambda **kwargs: pytest.fail("served without a persona"))
    monkeypatch.setattr(webchat.__main__.webbrowser, "open", lambda **kwargs: pytest.fail("opened a browser without a persona"))
    with pytest.raises(SystemExit) as stop:
        webchat.__main__.serve()
    assert str(local / "persona.json") in str(stop.value)


def test_serve_in_an_untrusted_project_stops_saying_how_to_trust_it(paths: WebchatPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_config(paths=paths, config=WebchatConfig(passphrase=new_passphrase_record(passphrase="correct horse")))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(webchat.__main__.uvicorn, "run", lambda **kwargs: pytest.fail("served in an untrusted project"))
    monkeypatch.setattr(webchat.__main__.webbrowser, "open", lambda **kwargs: pytest.fail("opened a browser in an untrusted project"))
    with pytest.raises(SystemExit) as stop:
        webchat.__main__.serve()
    assert "trust dialog" in str(stop.value)
