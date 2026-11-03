"""Replay engine behind the stand-in `gh` and `codex` entries in bin/.

    replay.py <gh|codex> <args...>

It reads the recording named by STANDIN_GH_RECORDING or STANDIN_CODEX_RECORDING, serves
the first recorded call whose arguments match exactly, and appends every call to the
JSON-lines log at STANDIN_LOG. A call outside the recording fails. It never runs, imports
or reaches the real tool.

A recording is {"tool": ..., "calls": [{"args": [...], "stdout": ..., "stderr": ...,
"exit": ..., "stdin"?: ..., "once"?: true}]}. `${NAME}` in recorded arguments expands from
the environment, so a recording can name paths inside a throwaway home. A call with a
recorded "stdin" matches only that input. A "once" call answers one time, by the log, then
the next match answers. An entry with "accepts" instead of "args" answers any call starting
with those arguments, for calls that hold text a run wrote: a body the call names by
`--body-file` or `-F`, or sends on stdin with `-`, goes into the log under "body". The Codex stand-in replays only `codex execpolicy check`
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
            if call.get("args", [])[:2] not in CODEX_COMMANDS:
                raise ValueError(
                    "the Codex stand-in replays only `codex execpolicy check` and `codex debug prompt-input`, "
                    "and %s records `codex %s`" % (path, " ".join(call.get("args", [])))
                )
    return calls


def body_of(args):
    """The text a call hands over by file or stdin, or None."""
    for flag in ("--body-file", "-F"):
        if flag in args[:-1]:
            name = args[args.index(flag) + 1]
            if name == "-":
                return sys.stdin.read()
            try:
                with open(name, encoding="utf-8") as handle:
                    return handle.read()
            except (OSError, ValueError) as error:
                return "unreadable: %s" % error
    return None


def served():
    """Which recorded calls the log shows as already answered."""
    path = os.environ.get("STANDIN_LOG")
    if not path or not os.path.exists(path):
        return set()
    with open(path) as handle:
        return set(json.loads(line).get("call") for line in handle if line.strip())


def main(argv):
    tool, args = argv[1], argv[2:]
    if tool not in RECORDING_VARIABLES:
        return fail(tool, "unknown tool")
    try:
        calls = load(tool)
    except (OSError, ValueError, KeyError, TypeError) as error:
        log({"tool": tool, "args": args, "recorded": False, "error": str(error)})
        return fail(tool, str(error))

    for index, call in enumerate(calls):
        if "accepts" in call and args[: len(call["accepts"])] == call["accepts"]:
            entry = {"tool": tool, "args": args, "recorded": True, "call": index}
            body = body_of(args)
            if body is not None:
                entry["body"] = body
            log(entry)
            sys.stdout.write(call.get("stdout", ""))
            return int(call.get("exit", 0))

    candidates = [(index, call) for index, call in enumerate(calls)
                  if "args" in call and [expand(a) for a in call["args"]] == args]
    if any(call.get("once") for _, call in candidates):
        answered = served()
        candidates = [(index, call) for index, call in candidates if not (call.get("once") and index in answered)]
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
