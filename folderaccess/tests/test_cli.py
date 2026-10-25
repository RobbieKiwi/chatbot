import json
from pathlib import Path

import pytest

from folderaccess.entry.cli import main
from folderaccess.tests.conftest import SETTINGS, Layout

NEW_CONVERSATION = "Takes effect in a new conversation."


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv=argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _slash(path: Path) -> str:
    return str(path).replace("\\", "/")


def _rule(path: Path) -> str:
    text = _slash(path)
    return f"//{text[0].lower()}{text[2:]}/**"


def _settings(layout: Layout) -> dict:
    return json.loads(layout.settings_path.read_text(encoding="utf-8"))


def test_list_of_an_empty_list(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["list"], capsys)
    assert (code, out.strip()) == (0, "No folders listed.")


def test_add_lists_the_folder_and_creates_the_local_settings(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    shared_before = layout.shared_settings_path.read_bytes()
    drafts = layout.home / "drafts"
    code, out, _ = _run(["add", str(drafts), "--access", "edit"], capsys)
    assert code == 0
    assert out.strip().endswith(NEW_CONVERSATION)
    _, out, _ = _run(["list"], capsys)
    assert out.strip() == f"edit {_slash(drafts)}"
    assert _settings(layout) == {"permissions": {"allow": [f"Read({_rule(drafts)})", f"Edit({_rule(drafts)})"], "additionalDirectories": [_slash(drafts)]}}
    assert layout.settings_path.read_text(encoding="utf-8").endswith("}\n")
    assert layout.shared_settings_path.read_bytes() == shared_before


def test_add_keeps_everything_else_in_the_local_settings(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    layout.settings_path.write_text(json.dumps(SETTINGS, indent=2) + "\n", encoding="utf-8")
    drafts = layout.home / "drafts"
    _run(["add", str(drafts), "--access", "edit"], capsys)
    settings = _settings(layout)
    assert settings["permissions"]["allow"] == ["Bash(git status)", "Glob(./notes/**)", f"Read({_rule(drafts)})", f"Edit({_rule(drafts)})"]
    assert settings["permissions"]["additionalDirectories"] == [_slash(drafts)]
    assert list(settings) == ["permissions", "hooks"]
    assert settings["hooks"]["Stop"][0]["hooks"][0]["command"] == "stop"


def test_add_relevels_a_listed_path_given_another_way(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    drafts = layout.home / "drafts"
    _run(["add", str(drafts), "--access", "edit"], capsys)
    spelled_differently = _slash(drafts)[0].lower() + str(drafts)[1:] + "\\"
    code, _, _ = _run(["add", spelled_differently, "--access", "read"], capsys)
    assert code == 0
    _, out, _ = _run(["list"], capsys)
    assert out.strip() == f"read {_slash(drafts)}"
    assert f"Edit({_rule(drafts)})" not in _settings(layout)["permissions"]["allow"]


def test_remove_of_the_last_entry_clears_rules(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    documents = layout.home / "documents"
    _run(["add", str(documents), "--access", "read"], capsys)
    code, out, _ = _run(["remove", str(documents).replace("\\", "/").lower() + "/"], capsys)
    assert code == 0
    assert out.strip().endswith(NEW_CONVERSATION)
    permissions = _settings(layout)["permissions"]
    assert permissions["additionalDirectories"] == []
    assert not [rule for rule in permissions["allow"] if rule.startswith(("Read(", "Edit("))]
    assert all(line.startswith("#") for line in layout.list_path.read_text(encoding="utf-8").splitlines() if line)


def test_sync_rewrites_settings_from_a_hand_edited_list(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    documents = layout.home / "documents"
    layout.list_path.parent.mkdir(parents=True)
    layout.list_path.write_text(f"# mine\nread {_slash(documents)}\n", encoding="utf-8")
    code, _, _ = _run(["sync"], capsys)
    assert code == 0
    assert _settings(layout)["permissions"]["additionalDirectories"] == [_slash(documents)]


def _refusal_leaves_files_alone(*, layout: Layout, capsys: pytest.CaptureFixture[str], argv: list[str], reason: str) -> None:
    _run(["add", str(layout.home / "documents"), "--access", "read"], capsys)
    before = layout.snapshot()
    code, out, err = _run(argv, capsys)
    assert code != 0
    assert reason in err and len(err.strip().splitlines()) == 1
    assert NEW_CONVERSATION not in out
    assert layout.snapshot() == before


@pytest.mark.parametrize(
    ("folder", "reason"),
    [
        (lambda layout: "relative/folder", "absolute"),
        (lambda layout: str(layout.home / "nowhere"), "does not exist"),
        (lambda layout: layout.home.anchor, "drive root"),
        (lambda layout: str(layout.home), "home folder"),
        (lambda layout: str(layout.home.parent), "contains the project"),
        (lambda layout: str(layout.project_root / "src"), "inside the project"),
    ],
)
def test_add_refusals_leave_both_files_untouched(layout: Layout, capsys: pytest.CaptureFixture[str], folder, reason: str) -> None:
    _refusal_leaves_files_alone(layout=layout, capsys=capsys, argv=["add", folder(layout), "--access", "edit"], reason=reason)


def test_remove_of_an_unlisted_path_is_refused(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    _refusal_leaves_files_alone(layout=layout, capsys=capsys, argv=["remove", str(layout.home / "drafts")], reason="not listed")


def test_sync_refuses_the_whole_list_when_a_folder_is_gone(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    gone = layout.home / "gone"
    gone.mkdir()
    _run(["add", str(gone), "--access", "read"], capsys)
    gone.rmdir()
    before = layout.snapshot()
    code, _, err = _run(["sync"], capsys)
    assert code != 0 and "does not exist" in err
    assert layout.snapshot() == before


def test_a_malformed_list_line_is_refused(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    layout.list_path.parent.mkdir(parents=True)
    layout.list_path.write_text("write C:/x\n", encoding="utf-8")
    _refusal_leaves_files_alone(layout=layout, capsys=capsys, argv=["sync"], reason="line 1")


@pytest.mark.parametrize("content", ["{ not json", "[1, 2]"])
def test_unreadable_local_settings_stop_before_any_write(layout: Layout, capsys: pytest.CaptureFixture[str], content: str) -> None:
    layout.settings_path.write_text(content, encoding="utf-8")
    before = layout.snapshot()
    code, _, err = _run(["add", str(layout.home / "documents"), "--access", "read"], capsys)
    assert code != 0 and str(layout.settings_path) in err
    assert layout.snapshot() == before


def test_sync_names_the_local_settings(layout: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["sync"], capsys)
    assert code == 0 and str(layout.settings_path) in out
    assert layout.settings_path.exists()
