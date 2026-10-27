"""The machine area (#44 §8, §9, #26): the install, the machine check and the governed-repository list.

Python 3's standard library at the 3.9 level only (ADR 0026). The library finds the
generator's `govlib` beside it: in this repository at `generator/govern-repository/scripts`,
and on a machine, where the install copies `machine/` to `~/.agents/governance/machine`, at
the installed generator's `~/.agents/skills/govern-repository/scripts`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# machine/scripts/machinelib -> the directory that holds machine/.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

GOVLIB_CANDIDATES = (
    os.path.join(ROOT, "generator", "govern-repository", "scripts"),
    os.path.join(os.path.dirname(ROOT), "skills", "govern-repository", "scripts"),
)


def find_govlib():
    for candidate in GOVLIB_CANDIDATES:
        if os.path.isfile(os.path.join(candidate, "govlib", "__init__.py")):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
            return candidate
    raise MachineError("找不到 generator 的 govlib：%s" % "、".join(GOVLIB_CANDIDATES))


class MachineError(Exception):
    """A refusal: the program stops before writing, and the message says why, in Chinese."""


# Fixed facts (#44 §1): the maintainer and agent accounts, and the sandbox names (§12).
MAINTAINER = "Habit130"
AGENT = "Habit098"
SANDBOXES = ("Habit130/governance-sandbox", "Habit130/governance-sandbox-private")
RECORD_PATH = ".github/governance/record.yml"
GENERATOR = "govern-repository"
# The ChatGPT app's bundled Codex CLI, which the machine check uses (#44 §9).
CODEX_APP = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
