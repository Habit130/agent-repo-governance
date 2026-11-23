#!/usr/bin/env python3
"""The machine area's one command-line entry (#44 §8, §9): install, check, list and the account wizard.

  install --source <tree> --home <dir>   the internal entry the ready command calls
  check [--home <dir>]                   the read-only machine check
  list [--home <dir>]                    the read-only governed-repository list
  wizard [--home <dir>]                  the account wizard, which habit runs in a terminal

Each prints its report in Chinese. Exit codes: 0 when nothing failed, 1 when a check item
or a list line failed or the wizard stopped at a step, 2 when the program refuses before
writing, with the reason.
`--codex` names the Codex CLI. By default it is `MACHINE_CODEX` when set, which suites set so no
run reaches a real Codex, and otherwise the one bundled in the ChatGPT app.
"""

import argparse
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import machinelib  # noqa: E402

# Match an explicit URI embedded in diagnostic prose. A redacted credential may
# sit inside its authority, so its complete type marker belongs to the same URI.
# Producers with a known field boundary withhold the field before joining it to
# Chinese prose. For unstructured text, punctuation can be part of a URL secret.
_SCHEME = r"[A-Za-z][A-Za-z0-9+.-]*:"
_URI = re.compile(
    # An opaque scheme starts a separate token. An ordinary local basename can contain a colon.
    rf"(?:(?<![A-Za-z0-9+.-]){_SCHEME}(?=/)|(?<![A-Za-z0-9+./-]){_SCHEME}|"
    # The colon in :// still introduces an authority when the scheme is attached to other text.
    r"""(?P<before>(?:^|[\s(（:：，；])['"]?)//)"""
    r'(?:<redacted [^>\n]+>|[^\s"<>])+'
)


def _hide_private_uri(match):
    uri = match[0]
    if any(part in uri for part in "@?#"):
        markers = [marker for marker in _TYPE_MARKERS if marker in uri]
        return (match["before"] or "") + ("、".join(markers) or "（已隐藏）")
    return uri


def write_line(line, stream):
    """Redact one logical diagnostic, including any continuation lines it owns."""
    # If bootstrap failed, even govlib's search paths are unsafe to repeat.
    safe = _URI.sub(_hide_private_uri, redact(line)) if redact is not None else "拒绝：找不到 generator 的 govlib"
    stream.write(safe + "\n")


try:
    machinelib.find_govlib()
    from govlib.secrets import SHAPES, redact
    _TYPE_MARKERS = tuple("<redacted %s>" % kind for kind, _ in SHAPES)
except (machinelib.MachineError, ImportError) as error:
    redact = None
    write_line(str(error), sys.stdout)
    sys.exit(2)

from machinelib import MachineError, check, governed, home as homes, install, wizard  # noqa: E402


class MachineArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # Argparse includes raw argv here, even inside brackets or after an equals sign.
        if re.search(r'//[^\s"<>]*[@?#]', message):
            shown = homes.withheld_value(message)
        else:
            shown = homes.withhold_url(message)
        super().error(message if shown == message else "参数解析失败：%s" % shown)

    def _print_message(self, message, file=None):
        if message:
            write_line(message.removesuffix("\n"), file if file is not None else sys.stderr)


def emit(reports):
    for report in reports:
        for line in report.render_lines():
            write_line(line, sys.stdout)
    return 1 if any(report.failed() for report in reports) else 0


def main(argv=None):
    parser = MachineArgumentParser(prog="machine.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True
    for name in ("install", "check", "list", "wizard"):
        command = commands.add_parser(name)
        command.add_argument("--home", default=os.path.expanduser("~"), required=name == "install")
        if name == "install":
            command.add_argument("--source", required=True, help="a git checkout of this repository")
        if name in ("install", "check"):
            command.add_argument("--codex", help="the Codex CLI (default: the ChatGPT app's)")
    args = parser.parse_args(argv)
    home = homes.Home(args.home)
    codex = getattr(args, "codex", None) or os.environ.get("MACHINE_CODEX") or None
    try:
        if args.command == "install":
            return emit(install.run(args.source, home, codex))
        if args.command == "wizard":
            return wizard.run(home)
        if args.command == "check":
            return emit([check.run(home, codex)])
        return emit([governed.run(home)])
    except MachineError as error:
        write_line("拒绝：%s" % error, sys.stdout)
        return 2


if __name__ == "__main__":
    sys.exit(main())
