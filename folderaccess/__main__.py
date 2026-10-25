import io
import sys

from folderaccess.entry.cli import main

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")  # Windows pipes default to the ANSI code page
    raise SystemExit(main(argv=sys.argv[1:]))
