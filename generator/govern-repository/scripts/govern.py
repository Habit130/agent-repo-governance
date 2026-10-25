#!/usr/bin/env python3
"""The generator's one command-line entry. Every subcommand prints JSON facts.

Exit codes: 0 when the facts are good, 1 when exact comparison finds differences,
2 when the command refuses, with the reason under "error".
"""

import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from govlib import GovernError, store, storedform  # noqa: E402

DEFAULT_STORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "store")


def emit(facts, code=0):
    sys.stdout.write(json.dumps(facts, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return code


def cmd_store(args):
    facts = store.Store(args.store).facts()
    facts["ok"] = True
    return emit(facts)


def cmd_change_note(args):
    with open(args.file, "rb") as handle:
        fields = store.parse_change_note(handle.read())
    fields["ok"] = True
    return emit(fields)


def cmd_materialize(args):
    written = storedform.materialize(args.source, args.dest)
    return emit({"ok": True, "dest": os.path.realpath(args.dest), "written": written})


def build_parser():
    parser = argparse.ArgumentParser(prog="govern.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True

    facts = commands.add_parser("store", help="list the store's versions, released versions and installed version")
    facts.add_argument("--store", default=DEFAULT_STORE)
    facts.set_defaults(run=cmd_store)

    note = commands.add_parser("change-note", help="read a change note's urgency and must-act fields")
    note.add_argument("file")
    note.set_defaults(run=cmd_change_note)

    materialize = commands.add_parser(
        "materialize", help="decode a stored tree into a temporary directory or a worktree"
    )
    materialize.add_argument("--source", required=True, help="the stored tree")
    materialize.add_argument("--dest", required=True, help="a temporary directory or a worktree's top level")
    materialize.set_defaults(run=cmd_materialize)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.run(args)
    except GovernError as error:
        return emit({"ok": False, "error": str(error)}, 2)


if __name__ == "__main__":
    sys.exit(main())
