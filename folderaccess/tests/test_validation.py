from pathlib import Path

import pytest

from folderaccess.domain.validation import validate


@pytest.fixture
def layout(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    project_root = home / "project"
    for folder in (project_root / "src", home / "documents"):
        folder.mkdir(parents=True)
    return project_root, home


def _refused(*, path: Path, layout: tuple[Path, Path], reason: str) -> None:
    project_root, home = layout
    with pytest.raises(ValueError, match=reason):
        validate(path=path, project_root=project_root, home=home)


def test_a_folder_outside_the_project_passes(layout: tuple[Path, Path]) -> None:
    project_root, home = layout
    validate(path=home / "documents", project_root=project_root, home=home)


def test_relative_path_is_refused(layout: tuple[Path, Path]) -> None:
    _refused(path=Path("documents"), layout=layout, reason="absolute")


def test_missing_path_is_refused(layout: tuple[Path, Path]) -> None:
    _refused(path=layout[1] / "nowhere", layout=layout, reason="does not exist")


def test_a_file_is_refused(layout: tuple[Path, Path]) -> None:
    file = layout[1] / "notes.txt"
    file.write_text("x", encoding="utf-8")
    _refused(path=file, layout=layout, reason="not a folder")


def test_drive_root_is_refused(layout: tuple[Path, Path]) -> None:
    _refused(path=Path(layout[1].anchor), layout=layout, reason="drive root")


def test_home_folder_is_refused(layout: tuple[Path, Path]) -> None:
    _refused(path=layout[1], layout=layout, reason="home folder")


def test_a_folder_containing_the_project_is_refused(layout: tuple[Path, Path]) -> None:
    _refused(path=layout[1].parent, layout=layout, reason="contains the project")


def test_the_project_itself_is_refused(layout: tuple[Path, Path]) -> None:
    _refused(path=layout[0], layout=layout, reason="contains the project")


def test_dot_dot_segments_are_resolved_first(layout: tuple[Path, Path]) -> None:
    _refused(path=layout[0] / "src" / ".." / "..", layout=layout, reason="home folder")


@pytest.mark.parametrize("relative", ["src", "inbox", "inbox/cv", ".claude"])
def test_every_folder_inside_the_project_is_refused(layout: tuple[Path, Path], relative: str) -> None:
    (layout[0] / relative).mkdir(parents=True, exist_ok=True)
    _refused(path=layout[0] / relative, layout=layout, reason="inside the project")


def test_case_differences_do_not_slip_past(layout: tuple[Path, Path]) -> None:
    _refused(path=Path(str(layout[0] / "src").upper()), layout=layout, reason="inside the project")
    _refused(path=Path(str(layout[1]).lower()), layout=layout, reason="home folder")


def test_a_symlink_to_the_project_is_refused(layout: tuple[Path, Path]) -> None:
    project_root, home = layout
    link = home / "documents" / "link"
    try:
        link.symlink_to(project_root, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks need privilege on this machine")
    _refused(path=link, layout=layout, reason="contains the project")


@pytest.mark.parametrize("relative", [".claude", ".claude/skills", ".ssh", "AppData", "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"])
def test_folders_that_hold_settings_credentials_or_startup_programs_are_refused(layout: tuple[Path, Path], relative: str) -> None:
    folder = layout[1] / relative
    folder.mkdir(parents=True, exist_ok=True)
    _refused(path=folder, layout=layout, reason="protected")


def test_a_folder_containing_a_protected_folder_is_refused(tmp_path: Path) -> None:
    home = tmp_path / "users" / "alex"
    project_root = tmp_path / "work" / "project"
    for folder in (home / ".claude", project_root):
        folder.mkdir(parents=True)
    with pytest.raises(ValueError, match="protected"):
        validate(path=tmp_path / "users", project_root=project_root, home=home)
