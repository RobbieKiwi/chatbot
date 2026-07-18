import sys

from memorylayers.entry.cli import main
from memorylayers.entry.common import use_utf8_streams

if __name__ == "__main__":
    use_utf8_streams()
    raise SystemExit(main(argv=sys.argv[1:]))
