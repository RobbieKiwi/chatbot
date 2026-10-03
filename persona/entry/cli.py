"""The persona command line: who the assistant is, what the user is called, and where the character file is."""

import argparse
import sys

from persona.adapters.files import CHARACTER_FILE, load_names, persona_dir, save_user_name
from persona.models import PersonaError

SET_USER = '.venv/Scripts/python -m persona set-user --name "<name>"'


def _show(args: argparse.Namespace) -> None:
    names = load_names()
    user = names.user_name or f"not set; ask for it and save it with {SET_USER}"
    print(f"assistant: {names.assistant_name}\nuser: {user}\npersona: {persona_dir() / CHARACTER_FILE}")


def _set_user(args: argparse.Namespace) -> None:
    names = save_user_name(user_name=args.name)
    print(f"Saved the user name {names.user_name}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m persona", description="The assistant's persona: its name, the user's name and its character file.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show", help="Print the assistant name, the user name (or that it is unset) and the path of the PERSONA.md in use.").set_defaults(handler=_show)
    set_user = subparsers.add_parser("set-user", help="Save the user's name in persona/local/persona.json, creating persona/local/ from persona/default/ when missing.")
    set_user.add_argument("--name", required=True, help="The user's name, as they want to be called.")
    set_user.set_defaults(handler=_set_user)
    return parser


def main(*, argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except PersonaError as error:
        print(str(error).splitlines()[0], file=sys.stderr)
        return 2
    return 0
