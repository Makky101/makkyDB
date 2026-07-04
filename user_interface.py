import sys
from connector import connect


OK = 0
BAD_ARGS = 1
BAD_VERBS = 2
BAD_KEY = 3


def usage():
    """Print command-line usage information to stderr."""
    print("Usage:", file=sys.stderr)
    print("\tpython tool.py get KEY", file=sys.stderr)
    print("\tpython tool.py set KEY VALUE", file=sys.stderr)
    print("\tpython tool.py delete KEY", file=sys.stderr)


def main(args):
    """Parse CLI arguments, execute the database command, and return a code."""
    if not (3 <= len(args) <= 4):
        usage()
        return BAD_ARGS

    concat = args[1:] + [None]

    cmd, key, value = concat[:3]
    if cmd not in {"select", "assign", "remove"}:
        usage()
        return BAD_VERBS

    db_kit = connect.plug()
    try:
        if cmd == "select":
            sys.stdout.write(db_kit[key])
        elif cmd == "assign":
            db_kit[key] = value
            db_kit.stamp()
        elif cmd == "remove":
            del db_kit[key]
            db_kit.stamp()
    except KeyError:
        print("key not found", file=sys.stderr)
        return BAD_ARGS
    return OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
