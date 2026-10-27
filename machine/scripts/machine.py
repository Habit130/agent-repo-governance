#!/usr/bin/env python3
"""The machine area's one command-line entry (#44 §8, §9): install, check and list.

  install --source <tree> --home <dir>   the internal entry the ready command calls
  check [--home <dir>]                   the read-only machine check
  list [--home <dir>]                    the read-only governed-repository list

Each prints its report in Chinese. Exit codes: 0 when nothing failed, 1 when a check item
or a list line failed, 2 when the program refuses before writing, with the reason.
`--codex` names the Codex CLI. By default it is `MACHINE_CODEX` when set, which suites set so no
run reaches a real Codex, and otherwise the one bundled in the ChatGPT app.
"""

import argparse
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import machinelib  # noqa: E402

try:
    machinelib.find_govlib()
except machinelib.MachineError as error:
    sys.stdout.write("拒绝：%s\n" % error)
    sys.exit(2)

from machinelib import MachineError, check, governed, home as homes, install  # noqa: E402


def emit(reports):
    for report in reports:
        sys.stdout.write(report.render())
    return 1 if any(report.failed() for report in reports) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="machine.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True
    for name in ("install", "check", "list"):
        command = commands.add_parser(name)
        command.add_argument("--home", default=os.path.expanduser("~"), required=name == "install")
        if name == "install":
            command.add_argument("--source", required=True, help="a git checkout of this repository")
        if name != "list":
            command.add_argument("--codex", help="the Codex CLI (default: the ChatGPT app's)")
    args = parser.parse_args(argv)
    home = homes.Home(args.home)
    codex = getattr(args, "codex", None) or os.environ.get("MACHINE_CODEX") or None
    try:
        if args.command == "install":
            return emit(install.run(args.source, home, codex))
        if args.command == "check":
            return emit([check.run(home, codex)])
        return emit([governed.run(home)])
    except MachineError as error:
        sys.stdout.write("拒绝：%s\n" % error)
        return 2


if __name__ == "__main__":
    sys.exit(main())
