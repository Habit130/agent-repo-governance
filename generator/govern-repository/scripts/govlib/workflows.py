"""CI facts for the inspection (#44 §6.3, #41 §7's required CI): each workflow's triggers, jobs and Actions secrets.

The standard library has no YAML reader, so `read` takes the block subset workflows use:
block mappings and sequences, plain and quoted scalars, one-line flow sequences, block scalars
(skipped) and comments. Anything else, anchors and multi-line flow collections included,
makes the workflow unreadable, and every judgment on it is flagged uncertain rather than
guessed.

A job counts as running, or reporting skipped, on every PR only when its workflow is
triggered by `pull_request` or `pull_request_target` with no path filter, no branch filter
that could leave out a PR into the default branch, and activity types that include opened,
synchronize and reopened. A job-level `if:` reports skipped, so it counts. A matrix, a
reusable workflow or a computed name changes the check's name, so it is flagged uncertain.
"""

import re

PR_EVENTS = ("pull_request", "pull_request_target")
DEFAULT_TYPES = ("opened", "synchronize", "reopened")
_SECRET = re.compile(r"secrets\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)|secrets\s*\[\s*['\"]([^'\"]+)['\"]\s*\]")
_GLOB = re.compile(r"[*?\[\]!+]")
_BLOCK_SCALAR = re.compile(r"^[|>][+-]?[0-9]?[+-]?$")


class Unreadable(Exception):
    pass


def _strip_comment(line):
    quote = None
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "#" and (index == 0 or line[index - 1] in " \t"):
            return line[:index].rstrip()
    return line.rstrip()


def _lines(text):
    """[(indent, content)] without blank lines, comments or block scalars' bodies."""
    out = []
    raw = text.replace("\r\n", "\n").split("\n")
    index = 0
    while index < len(raw):
        line = raw[index]
        index += 1
        if "\t" in line[: len(line) - len(line.lstrip())]:
            raise Unreadable("a tab in indentation")
        content = _strip_comment(line)
        if not content.strip() or content.strip() in ("---", "..."):
            continue
        indent = len(content) - len(content.lstrip(" "))
        content = content.strip()
        value = content.split(": ", 1)[1].strip() if ": " in content else content[1:].strip() if content.startswith("- ") else ""
        if _BLOCK_SCALAR.match(value):
            content = content[: len(content) - len(value)] + '"<block>"'
            while index < len(raw) and (not raw[index].strip() or len(raw[index]) - len(raw[index].lstrip(" ")) > indent):
                index += 1
        out.append((indent, content))
    return out


def _unquote(text):
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def _scalar(text):
    text = text.strip()
    if text.startswith(("&", "*", "!")):
        raise Unreadable("an anchor, alias or tag")
    if text.startswith("["):
        if not text.endswith("]"):
            raise Unreadable("a flow sequence over several lines")
        inner = text[1:-1].strip()
        if any(c in inner for c in "[]{}"):
            raise Unreadable("a nested flow collection")
        return [_unquote(part.strip()) for part in inner.split(",") if part.strip()] if inner else []
    if text.startswith("{"):
        if text == "{}":
            return {}
        raise Unreadable("a flow mapping")
    return _unquote(text)


def _key(content):
    if content.startswith(("'", '"')):
        end = content.find(content[0], 1)
        if end < 0 or content[end + 1:end + 2] != ":":
            raise Unreadable("a quoted key")
        return content[1:end], content[end + 2:].strip()
    if ":" not in content or (not content.endswith(":") and ": " not in content):
        raise Unreadable("a line that is neither a key nor an item: %r" % content)
    key, _, rest = content.partition(": ") if ": " in content else (content[:-1], "", "")
    return key.strip(), rest.strip()


def _node(lines, index, indent):
    if lines[index][1] == "-" or lines[index][1].startswith("- "):
        return _sequence(lines, index, indent)
    return _mapping(lines, index, indent)


def _child(lines, index, indent, sequence_ok):
    """The block value after a key at indent, starting at lines[index]; (value, next index)."""
    if index < len(lines):
        child_indent, content = lines[index]
        if child_indent > indent or (sequence_ok and child_indent == indent and (content == "-" or content.startswith("- "))):
            return _node(lines, index, child_indent)
    return None, index


def _mapping(lines, index, indent):
    found = {}
    while index < len(lines) and lines[index][0] == indent:
        content = lines[index][1]
        if content == "-" or content.startswith("- "):
            break
        key, rest = _key(content)
        if key in found:
            raise Unreadable("a repeated key %r" % key)
        index += 1
        if rest:
            found[key] = _scalar(rest)
        else:
            found[key], index = _child(lines, index, indent, True)
    if index < len(lines) and lines[index][0] > indent:
        raise Unreadable("uneven indentation")
    return found, index


def _sequence(lines, index, indent):
    found = []
    while index < len(lines) and lines[index][0] == indent and (lines[index][1] == "-" or lines[index][1].startswith("- ")):
        rest = lines[index][1][1:]
        stripped = rest.strip()
        if not stripped:
            value, index = _child(lines, index + 1, indent, False)
            found.append(value)
            continue
        inner = indent + 1 + len(rest) - len(rest.lstrip(" "))
        is_mapping = not stripped.startswith(("'", '"', "[", "{")) and (stripped.endswith(":") or ": " in stripped)
        if is_mapping:
            lines = lines[:index] + [(inner, stripped)] + lines[index + 1:]
            value, index = _mapping(lines, index, inner)
            found.append(value)
        else:
            found.append(_scalar(stripped))
            index += 1
    return found, index


def read(text):
    """A workflow's top-level mapping; Unreadable when it is outside the subset."""
    lines = _lines(text)
    if not lines:
        raise Unreadable("an empty file")
    value, index = _node(lines, 0, lines[0][0])
    if index != len(lines) or not isinstance(value, dict):
        raise Unreadable("content the reader can't place")
    return value


def triggers(document):
    """{event: filters or None} from a workflow's `on`."""
    on = document.get("on", document.get(True))
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return dict((event, None) for event in on)
    if isinstance(on, dict):
        return dict((event, filters if isinstance(filters, dict) else None) for event, filters in on.items())
    return {}


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def pr_coverage(events, default_branch):
    """(every PR: True, False or None, reasons) for a workflow's triggers."""
    best, reasons = False, []
    candidates = [event for event in PR_EVENTS if event in events]
    if not candidates:
        return False, ["not triggered by pull_request or pull_request_target"]
    for event in candidates:
        filters = events[event] or {}
        verdict, why = True, []
        for key in ("paths", "paths-ignore"):
            if key in filters:
                verdict = False
                why.append("%s has a %s filter, so it doesn't run when no path matches" % (event, key))
        branches = _as_list(filters.get("branches"))
        if "branches" in filters:
            if default_branch in branches or "**" in branches:
                pass
            elif any(_GLOB.search(b) for b in branches):
                verdict = None if verdict else verdict
                why.append("%s's branch filter %s may leave out %s" % (event, branches, default_branch))
            else:
                verdict = False
                why.append("%s's branch filter %s leaves out %s" % (event, branches, default_branch))
        ignored = _as_list(filters.get("branches-ignore"))
        if default_branch in ignored:
            verdict = False
            why.append("%s ignores %s" % (event, default_branch))
        elif any(_GLOB.search(b) for b in ignored):
            verdict = None if verdict else verdict
            why.append("%s's branches-ignore %s may cover %s" % (event, ignored, default_branch))
        if "types" in filters:
            missing = [t for t in DEFAULT_TYPES if t not in _as_list(filters["types"])]
            if missing:
                verdict = False
                why.append("%s's types leave out %s" % (event, ", ".join(missing)))
        if verdict is True:
            return True, ["%s, with no filter that leaves a PR out" % event]
        if verdict is None:
            best = None
        reasons.extend(why)
    return best, reasons


def secrets(text):
    """The Actions secrets a workflow references, GITHUB_TOKEN excluded, and whether it passes them all on."""
    names = set()
    for match in _SECRET.finditer(text):
        name = match.group(1) or match.group(2)
        if name.upper() != "GITHUB_TOKEN":
            names.add(name)
    inherit = bool(re.search(r"(?m)^\s*secrets:\s*inherit\s*$", text))
    return sorted(names), inherit


def inspect(path, text, default_branch):
    """One workflow's facts."""
    names, inherit = secrets(text)
    facts = {"path": path, "secrets": names, "secrets_inherit": inherit}
    try:
        document = read(text)
    except Unreadable as error:
        facts.update({"readable": False, "reason": str(error), "triggers": None, "jobs": [],
                      "uncertain": ["the generator's reader can't read this workflow: %s" % error]})
        return facts
    events = triggers(document)
    every, reasons = pr_coverage(events, default_branch)
    jobs = []
    for job_id, job in sorted((document.get("jobs") or {}).items()):
        job = job if isinstance(job, dict) else {}
        name = job.get("name") if isinstance(job.get("name"), str) else job_id
        entry = {"id": job_id, "name": name, "every_pr": every, "reasons": list(reasons), "uncertain": every is None}
        flags = []
        if "${{" in name:
            flags.append("its name is computed")
        if isinstance(job.get("strategy"), dict) and "matrix" in job["strategy"]:
            flags.append("a matrix names its checks after their values")
        if "uses" in job:
            flags.append("a reusable workflow names its checks after the called jobs")
        if flags:
            entry["uncertain"] = True
            entry["reasons"].extend("the check's name is uncertain: %s" % flag for flag in flags)
        if "if" in job and every:
            entry["reasons"].append("its `if:` reports skipped when false, which counts")
        jobs.append(entry)
    facts.update({"readable": True, "triggers": events, "jobs": jobs, "uncertain": [j["id"] for j in jobs if j["uncertain"]]})
    return facts
