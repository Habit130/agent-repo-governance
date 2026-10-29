"""The harness refusal (#44 §6, ADR 0013): the generator runs only in Claude Code or OpenCode.

The judgment reads the environment each harness sets for its shell, by variable name and,
for the two supported markers, by value. It fails closed: a run passes only when exactly one
supported harness's marker is set and no other harness's marker is, since a session started
from another harness's shell inherits that harness's variables. Every other case refuses,
the Codex harness and deepseekharness included. The markers come from each harness's own
shell, probed by name in #50's delivery (`docs/agents/build.md`, The generator's command line).
"""

import os

from govlib import GovernError


class HarnessRefusal(GovernError):
    """The run stops before any other step: this isn't Claude Code or OpenCode."""

    def __init__(self, judged):
        super(HarnessRefusal, self).__init__("harness refused: %s" % judged["detail"])
        self.judged = judged


# A supported harness's marker: the variable and the value it sets.
SUPPORTED = (
    ("Claude Code", "CLAUDECODE", "1"),
    ("OpenCode", "OPENCODE", "1"),
)

# What marks a harness the generator never runs in: variable names, or name prefixes that end
# in `_`. The homes a user may export for every shell (`CODEX_HOME`, `DSH_HOME`) don't count.
FOREIGN = (
    ("the Codex harness", ("CODEX_SANDBOX", "CODEX_THREAD_ID", "CODEX_CI", "CODEX_MANAGED_BY_NPM", "CODEX_MANAGED_BY_BUN")),
    ("deepseekharness", ("DSH_PROFILE", "DSH_PERMISSION_MODE", "DSH_SESSION_ID", "DSH_AGENTS_HOME")),
)


def _present(env, names):
    found = []
    for name in sorted(env):
        if any(name == wanted or (wanted.endswith("_") and name.startswith(wanted)) for wanted in names):
            found.append(name)
    return found


def judge(env):
    """{"passed", "harness", "detail", "markers"}: which harness this is, from the environment's names."""
    supported = [(harness, name) for harness, name, value in SUPPORTED if env.get(name) == value]
    foreign = [(harness, name) for harness, names in FOREIGN for name in _present(env, names)]
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
