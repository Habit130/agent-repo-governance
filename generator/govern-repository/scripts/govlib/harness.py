"""The harness refusal (#44 §6, ADR 0013): the generator runs only in Claude Code or OpenCode.

The judgment reads which variables each harness sets for its shell, and only that a
supported marker isn't empty. It fails closed: a run passes only when exactly one supported
harness's marker is set and no other harness's marker is, since a session started from
another harness's shell inherits that harness's variables. Every other case refuses, the
Codex harness and deepseekharness included. The markers come from each harness's own shell,
probed by name on 2026-10-29 (`tests/fixtures/generator/harness-probes.json`).
"""

import os

from govlib import GovernError


class HarnessRefusal(GovernError):
    """The run stops before any other step: this isn't Claude Code or OpenCode."""

    def __init__(self, judged):
        super(HarnessRefusal, self).__init__("harness refused: %s" % judged["detail"])
        self.judged = judged


# A supported harness's marker: a variable it sets, non-empty.
SUPPORTED = (
    ("Claude Code", "CLAUDECODE"),
    ("OpenCode", "OPENCODE"),
)

# What marks a harness the generator never runs in: every variable with the harness's prefix,
# except the homes a user may export for every shell.
FOREIGN = (
    ("the Codex harness", "CODEX_", ("CODEX_HOME",)),
    ("deepseekharness", "DSH_", ("DSH_HOME", "DSH_AGENTS_HOME")),
)


def judge(env):
    """{"passed", "harness", "detail", "markers"}: which harness this is, from the environment's names."""
    supported = [(harness, name) for harness, name in SUPPORTED if env.get(name)]
    foreign = [
        (harness, name)
        for harness, prefix, homes in FOREIGN
        for name in sorted(env)
        if name.startswith(prefix) and name not in homes
    ]
    markers = sorted(name for _, name in supported + foreign)
    if foreign:
        harnesses = sorted(set(harness for harness, _ in foreign))
        return {
            "passed": False,
            "harness": harnesses[0] if len(harnesses) == 1 and not supported else None,
            "detail": "%s set %s; the generator runs only in Claude Code or OpenCode"
            % (" and ".join(harnesses), ", ".join(name for _, name in foreign)),
            "markers": markers,
        }
    if len(supported) != 1:
        return {
            "passed": False,
            "harness": None,
            "detail": "no harness the generator runs in is recognized"
            if not supported
            else "both Claude Code's and OpenCode's markers are set, so the harness can't be told",
            "markers": markers,
        }
    return {"passed": True, "harness": supported[0][0], "detail": "%s sets %s" % supported[0], "markers": markers}


def require(env=None):
    """The judgment when the harness passes; HarnessRefusal otherwise."""
    judged = judge(os.environ if env is None else env)
    if not judged["passed"]:
        raise HarnessRefusal(judged)
    return judged
