"""Which folders may go on the list. Access to the project would let the assistant rewrite its own code and settings, so nothing inside it is allowed."""

from pathlib import Path

from folderaccess.domain.listing import is_within, same_path

# Claude's own settings and hooks, credentials, and AppData, which holds the Startup folder
PROTECTED_IN_HOME = (".claude", ".ssh", "AppData")


def validate(*, path: Path, project_root: Path, home: Path) -> None:
    """Raise ValueError with a one-line reason when the folder may not be listed. Checks the real filesystem, after resolving symlinks and `..`."""
    if not path.is_absolute():
        raise ValueError(f"{path} is not an absolute path")
    if not path.exists():
        raise ValueError(f"{path} does not exist")
    if not path.is_dir():
        raise ValueError(f"{path} is not a folder")
    resolved = str(path.resolve())
    root = str(project_root.resolve())
    if Path(resolved).parent == Path(resolved):
        raise ValueError(f"{path} is a drive root")
    if same_path(a=resolved, b=str(home.resolve())):
        raise ValueError(f"{path} is the home folder")
    if is_within(path=root, root=resolved):
        raise ValueError(f"{path} contains the project")
    for protected in PROTECTED_IN_HOME:
        protected_path = str(home.resolve() / protected)
        if is_within(path=resolved, root=protected_path) or is_within(path=protected_path, root=resolved):
            raise ValueError(f"{path} is or holds the protected folder {protected_path}")
    if is_within(path=resolved, root=root):
        raise ValueError(f"{path} is inside the project; list folders outside it")
