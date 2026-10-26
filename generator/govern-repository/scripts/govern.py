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

from govlib import GovernError, compare, render, store, storedform  # noqa: E402

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


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        raise GovernError("%s can't be read as JSON: %s" % (path, error))


def cmd_render(args):
    confirmed = read_json(args.confirmed) if args.confirmed else None
    facts = render.render(
        store.Store(args.store),
        args.dest,
        args.repository,
        args.default_branch,
        confirmed=confirmed,
        version=args.version,
        allow_unreleased=args.allow_unreleased,
    )
    facts["ok"] = True
    return emit(facts)


def cmd_compare(args):
    repository = args.repository or compare.repository_from_origin(args.worktree)
    default_branch = args.default_branch or compare.default_branch_from_origin(args.worktree)
    facts = compare.compare(
        store.Store(args.store),
        args.worktree,
        repository,
        default_branch,
        version=args.version,
        allow_unreleased=args.allow_unreleased,
    )
    facts["ok"] = not facts["differences"]
    return emit(facts, 0 if facts["ok"] else 1)


def add_version_arguments(parser):
    parser.add_argument("--store", default=DEFAULT_STORE)
    parser.add_argument("--version", type=int, help="default: the installed version")
    parser.add_argument(
        "--allow-unreleased",
        action="store_true",
        help="for test, scenario and live-check runners only: allow a version that isn't released, for this run",
    )


def cmd_materialize(args):
    written = storedform.materialize(args.source, args.dest)
    return emit({"ok": True, "dest": os.path.realpath(args.dest), "written": written})


def build_parser():
    parser = argparse.ArgumentParser(prog="govern.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True

    listing = commands.add_parser("store", help="list the store's versions, released versions and installed version")
    listing.add_argument("--store", default=DEFAULT_STORE)
    listing.set_defaults(run=cmd_store)

    note = commands.add_parser("change-note", help="read a change note's urgency and must-act fields")
    note.add_argument("file")
    note.set_defaults(run=cmd_change_note)

    rendering = commands.add_parser("render", help="render a version into a temporary directory or a worktree")
    add_version_arguments(rendering)
    rendering.add_argument("--dest", required=True, help="a temporary directory or a worktree's top level")
    rendering.add_argument("--repository", required=True, help="owner/name")
    rendering.add_argument("--default-branch", required=True)
    rendering.add_argument("--confirmed", help="a JSON file of the record's confirmed values")
    rendering.set_defaults(run=cmd_render)

    comparing = commands.add_parser("compare", help="exact comparison of a worktree's fixed content with a version")
    add_version_arguments(comparing)
    comparing.add_argument("--worktree", default=".", help="default: the current directory")
    comparing.add_argument("--repository", help="owner/name; default: from the worktree's origin")
    comparing.add_argument("--default-branch", help="default: origin's HEAD in the worktree")
    comparing.set_defaults(run=cmd_compare)

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
    except OSError as error:
        return emit({"ok": False, "error": "%s: %s" % (error.filename or "a file", error.strerror or error)}, 2)


if __name__ == "__main__":
    sys.exit(main())
