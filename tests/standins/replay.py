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
`--body-file` or `-F`, or sends on stdin with `-`, goes into the log under "body". An
accepting `issue view` entry with "created_issue": true serves the issues the log shows the
run creating, numbered from 1 in order, with their later `issue edit` title and body: plain,
as `--json` fields, or one field by `--jq .<field>`; a number the run never created fails.
An accepting `label list` or `api repos/<repo>/labels` entry with "labels" serves those
labels and then the ones the log shows the run creating: plain, as `--json` fields or the API's
objects, or by `--jq` `length` or `.[].<field>`; an `api` call that writes fails. The Codex stand-in replays only `codex execpolicy check`
and `codex debug prompt-input`.

An "args" entry may also carry "when" and "effects", for state a run changes, such as a
login. It matches only when every condition under "when" holds: {"path": ..., "absent": true}
or {"path": ..., "contains": <text>}, the path expanded as above, so `${GH_CONFIG_DIR}` tells
two gh configurations apart. When it answers, each of its "effects" writes or appends text,
{"path": ..., "write" | "append": <text>}, creating the parent directories. Keep such state in
files real gh never reads, such as `standin-account`, so a stray call can't become a login.
An "args" entry's optional "delay" waits that many seconds after logging and effects but
before output, to exercise the caller's real timeout handling.
"""

import json
import os
import re
import sys
import time

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
            with open(name, encoding="utf-8") as handle:
                return handle.read()
    return None


def _flag(args, *flags):
    for flag in flags:
        if flag in args[:-1]:
            return args[args.index(flag) + 1]
    return None


def holds(call):
    """Whether every condition under the entry's "when" holds."""
    for condition in call.get("when", ()):
        path = expand(condition["path"])
        if "contains" not in condition and not condition.get("absent"):
            raise ValueError("a `when` condition needs `absent` or `contains`: %r" % (condition,))
        if condition.get("absent"):
            if os.path.exists(path):
                return False
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            return False
        if condition["contains"] not in text:
            return False
    return True


def apply_effects(call):
    for effect in call.get("effects", ()):
        path = expand(effect["path"])
        parent = os.path.dirname(path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(path, "a" if "append" in effect else "w", encoding="utf-8") as handle:
            handle.write(effect["append"] if "append" in effect else effect["write"])


def created_issues():
    """{number: {"title", "body"}} for the issues the log shows the run creating and editing."""
    path = os.environ.get("STANDIN_LOG")
    issues = {}
    if not path or not os.path.exists(path):
        return issues
    with open(path) as handle:
        for line in handle:
            entry = json.loads(line) if line.strip() else {}
            args = entry.get("args") or []
            if not entry.get("recorded") or args[:1] != ["issue"]:
                continue
            text = entry.get("body", _flag(args, "--body", "-b"))
            if args[1:2] == ["create"]:
                issues[str(len(issues) + 1)] = {"title": _flag(args, "--title", "-t") or "", "body": text or ""}
            elif args[1:2] == ["edit"] and len(args) > 2 and _number(args[2]) in issues:
                issue = issues[_number(args[2])]
                issue["title"] = _flag(args, "--title", "-t") or issue["title"]
                issue["body"] = issue["body"] if text is None else text
    return issues


def _number(reference):
    return reference.rstrip("/").rsplit("/", 1)[-1].lstrip("#")


def view_issue(args):
    """(stdout, exit) for `issue view <number>` against the issues the run created."""
    issue = created_issues().get(_number(args[2])) if len(args) > 2 else None
    if issue is None:
        return "", 1
    fields = _flag(args, "--json")
    if fields is None:
        return "title:\t%s\nstate:\tOPEN\nnumber:\t%s\n--\n%s\n" % (issue["title"], _number(args[2]), issue["body"]), 0
    answer = dict((name, issue.get(name, "OPEN" if name == "state" else "")) for name in fields.split(","))
    query = _flag(args, "--jq", "-q")
    if query and query.startswith(".") and query[1:] in answer:
        return "%s\n" % answer[query[1:]], 0
    return json.dumps(answer) + "\n", 0


WRITE_FLAGS = ("--method", "-X", "--input", "-f", "-F", "--field", "--raw-field")


def list_labels(call, args):
    """(stdout, exit) for a label read: the recorded labels, then the ones the run created."""
    if args[:1] == ["api"] and any(flag in args for flag in WRITE_FLAGS):
        return "", 1
    labels = [dict(label) for label in call["labels"]]
    path = os.environ.get("STANDIN_LOG")
    if path and os.path.exists(path):
        with open(path) as handle:
            for line in handle:
                entry = json.loads(line) if line.strip() else {}
                made = entry.get("args") or []
                if entry.get("recorded") and made[:2] == ["label", "create"] and len(made) > 2 and \
                        made[2] not in [label["name"] for label in labels]:
                    labels.append({"name": made[2], "color": _flag(made, "--color", "-c") or "",
                                   "description": _flag(made, "--description", "-d") or ""})
    fields, query = _flag(args, "--json"), _flag(args, "--jq", "-q")
    if args[:1] == ["label"] and fields is None:
        return "".join("%s\t%s\t#%s\n" % (l["name"], l["description"], l["color"]) for l in labels), 0
    if fields is not None:
        labels = [dict((name, label.get(name, "")) for name in fields.split(",")) for label in labels]
    if query == "length":
        return "%d\n" % len(labels), 0
    if query and query.startswith(".[]."):
        return "".join("%s\n" % label.get(query[4:], "") for label in labels), 0
    return json.dumps(labels) + "\n", 0


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

    body = None
    # API -F is a field, not a body file. Leave stdin to the matching entry below.
    body_file = _flag(args, "--body-file", *(() if args[:1] == ["api"] else ("-F",)))
    if tool == "gh" and body_file is not None and body_file != "-":
        try:
            body = body_of(args)
        except (OSError, ValueError) as error:
            message = "cannot read body file: %s" % error
            log({"tool": tool, "args": args, "recorded": False, "error": message})
            return fail(tool, message)

    for index, call in enumerate(calls):
        if "accepts" in call and args[: len(call["accepts"])] == call["accepts"]:
            entry = {"tool": tool, "args": args, "recorded": True, "call": index}
            body = body_of(args) if body_file == "-" else body
            if body is not None:
                entry["body"] = body
            if call.get("created_issue") or "labels" in call:
                out, code = view_issue(args) if call.get("created_issue") else list_labels(call, args)
                log(entry)
                sys.stdout.write(out)
                return code
            log(entry)
            sys.stdout.write(call.get("stdout", ""))
            return int(call.get("exit", 0))

    candidates = [(index, call) for index, call in enumerate(calls)
                  if "args" in call and [expand(a) for a in call["args"]] == args and holds(call)]
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
            if body is not None:
                entry["body"] = body
            log(entry)
            apply_effects(call)
            if call.get("delay"):
                time.sleep(call["delay"])
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
