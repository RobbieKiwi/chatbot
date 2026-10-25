"""Serve the chat page on the local network. Run: uv run python -m webchat"""

import logging
import socket
import sys
import webbrowser

import uvicorn

from persona.adapters.files import load_names
from persona.models import PersonaError
from webchat.adapters.assistant import AssistantDriver
from webchat.adapters.files import PROJECT_ROOT, read_config, webchat_paths
from webchat.entry.app import create_app
from webchat.entry.turns import TurnRunner


def serve() -> None:
    paths = webchat_paths()
    config = read_config(paths=paths)
    if config.passphrase is None:
        sys.exit("No passphrase set. Run: uv run python -m webchat.scripts.set_passphrase")
    try:
        assistant_name = load_names().assistant_name
    except PersonaError as error:
        sys.exit(str(error))
    paths.logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=paths.logs / "server.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", encoding="utf-8")
    turns = TurnRunner(driver=AssistantDriver(paths=paths, project_root=PROJECT_ROOT, assistant_name=assistant_name), paths=paths)
    url = f"http://{socket.gethostname()}:{config.port}"
    print(f"{assistant_name} is at {url} (Ctrl+C to stop)")
    # No reload or workers: they switch Windows to a selector event loop, which cannot start the Claude Code subprocess.
    webbrowser.open(url=url)
    uvicorn.run(app=create_app(paths=paths, turns=turns, assistant_name=assistant_name), host="0.0.0.0", port=config.port, log_config=None)


if __name__ == "__main__":
    serve()
