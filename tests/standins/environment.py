"""The environment that puts the stand-ins first on the path for a suite or a scenario.

The real `gh` runs without credentials behind them: every token variable is removed and
GH_CONFIG_DIR points at an empty directory, so a call that somehow passed the stand-in would
fail instead of reaching GitHub.
"""

import json
import os
import sys

BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
LOG = "standin-calls.jsonl"
TOKEN_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")


def environment(scratch, gh_recording=None, codex_recording=None, base=None):
    """An environment whose gh and codex are the stand-ins, logging into scratch."""
    env = dict(os.environ if base is None else base)
    for name in TOKEN_VARIABLES:
        env.pop(name, None)
    config = os.path.join(scratch, "gh-config")
    os.makedirs(config)
    env.update(
        {
            "PATH": BIN + os.pathsep + env.get("PATH", ""),
            "STANDIN_PYTHON": sys.executable,
            "STANDIN_LOG": os.path.join(scratch, LOG),
            "GH_CONFIG_DIR": config,
            "GH_PROMPT_DISABLED": "1",
            "GH_NO_UPDATE_NOTIFIER": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    for name, recording in (("STANDIN_GH_RECORDING", gh_recording), ("STANDIN_CODEX_RECORDING", codex_recording)):
        if recording:
            env[name] = recording
        else:
            env.pop(name, None)
    return env


def read_log(scratch):
    """Every call the stand-ins saw, in order."""
    path = os.path.join(scratch, LOG)
    if not os.path.exists(path):
        return []
    with open(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]
