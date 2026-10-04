"""Set or change the chat page's passphrase; changing it logs every device out. Run: uv run python -m webchat.scripts.set_passphrase"""

import sys
from getpass import getpass

from webchat.adapters.files import read_config, webchat_paths, write_config
from webchat.domain.auth import new_passphrase_record

MINIMUM_LENGTH = 8


def set_passphrase() -> None:
    paths = webchat_paths()
    passphrase = getpass(prompt="New passphrase: ")
    if len(passphrase) < MINIMUM_LENGTH:
        sys.exit(f"Use at least {MINIMUM_LENGTH} characters; nothing changed.")
    if getpass(prompt="Again: ") != passphrase:
        sys.exit("The two entries differ; nothing changed.")
    config = read_config(paths=paths)
    write_config(paths=paths, config=config.model_copy(update={"passphrase": new_passphrase_record(passphrase=passphrase)}))
    print("Passphrase set. Every device has to enter it again.")


if __name__ == "__main__":
    set_passphrase()
