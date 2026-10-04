"""The memorylayers command line: the agents' only way into memory."""

import argparse
import sys

from memorylayers.entry import gap_commands, read_commands, resume_command, summary_commands, worker_commands, write_commands
from memorylayers.entry.common import CliError
from persona.models import PersonaError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m memorylayers", description="Layered long-term memory for a parent skill.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for module in (read_commands, write_commands, summary_commands, gap_commands, worker_commands, resume_command):
        module.register(subparsers=subparsers)
    return parser


def main(*, argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except (CliError, PersonaError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0
