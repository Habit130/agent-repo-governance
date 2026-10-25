"""Replay engine behind the stand-in `gh` and `codex` entries in bin/.

    replay.py <gh|codex> <args...>

It reads the recording named by STANDIN_GH_RECORDING or STANDIN_CODEX_RECORDING, serves
the first recorded call whose arguments match exactly, and appends every call to the
JSON-lines log at STANDIN_LOG. A call outside the recording fails. It never runs, imports
or reaches the real tool.

A recording is {"tool": ..., "calls": [{"args": [...], "stdout": ..., "stderr": ...,
"exit": ..., "stdin"?: ...}]}. `${NAME}` in recorded arguments expands from the
environment, so a recording can name paths inside a throwaway home. A call with a recorded
"stdin" matches only that input. The Codex stand-in replays only `codex execpolicy check`
and `codex debug prompt-input`.
"""

import json
import os
import re
import sys

RECORDING_VARIABLES = {"gh": "STANDIN_GH_RECORDING", "codex": "STANDIN_CODEX_RECORDING"}
CODEX_COMMANDS = (["execpolicy", "check"], ["debug", "prompt-input"])
_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def fail(tool, message):
    sys.stderr.write("stand-in %s: %s\n" % (tool, message))
    return 1


def log(entry):
    path = os.environ.get("STANDIN_LOG")
    if path:
        with open(path, "a") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")


def expand(arg):
    return _VARIABLE.sub(lambda match: os.environ.get(match.group(1), ""), arg)


def load(tool):
    variable = RECORDING_VARIABLES[tool]
    path = os.environ.get(variable)
    if not path:
        raise ValueError("%s names no recording, so every call fails" % variable)
    with open(path) as handle:
        recording = json.load(handle)
    if recording.get("tool") != tool:
        raise ValueError("%s is a recording for %r, not %s" % (path, recording.get("tool"), tool))
    calls = recording.get("calls", [])
    if tool == "codex":
        for call in calls:
            if call["args"][:2] not in CODEX_COMMANDS:
                raise ValueError(
                    "the Codex stand-in replays only `codex execpolicy check` and `codex debug prompt-input`, "
                    "and %s records `codex %s`" % (path, " ".join(call["args"]))
                )
    return calls


def main(argv):
    tool, args = argv[1], argv[2:]
    if tool not in RECORDING_VARIABLES:
        return fail(tool, "unknown tool")
    try:
        calls = load(tool)
    except (OSError, ValueError, KeyError, TypeError) as error:
        log({"tool": tool, "args": args, "recorded": False, "error": str(error)})
        return fail(tool, str(error))

    candidates = [(index, call) for index, call in enumerate(calls) if [expand(a) for a in call["args"]] == args]
    stdin = None
    if any("stdin" in call for _, call in candidates):
        stdin = sys.stdin.read()
    for index, call in candidates:
        if "stdin" not in call or call["stdin"] == stdin:
            entry = {"tool": tool, "args": args, "recorded": True, "call": index}
            if stdin is not None:
                entry["stdin"] = stdin
            log(entry)
            sys.stdout.write(call.get("stdout", ""))
            sys.stderr.write(call.get("stderr", ""))
            return int(call.get("exit", 0))

    entry = {"tool": tool, "args": args, "recorded": False}
    if stdin is not None:
        entry["stdin"] = stdin
    log(entry)
    return fail(tool, "no recorded call matches `%s %s`, and the stand-in never reaches the real %s" % (tool, " ".join(args), tool))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.exit(main(sys.argv))
