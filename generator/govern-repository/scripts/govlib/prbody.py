"""The PR body's `Risk:` and `Reverts:` lines (#41 §8): the machine side's parser.

Only lines that start with `Risk:` or `Reverts:` count, wherever they sit: inside an HTML
comment or a code fence too, which is why no template comment line starts that way. Lines
end at LF, and a CR before it is dropped, since bodies edited on GitHub arrive with CRLF.

- The body holds exactly one `Risk: <low|medium|high> — <reason>` line, the separator an em
  dash with one space each side, and a reason that isn't empty once spaces and tabs around
  it are dropped.
- A `Reverts:` line is optional, and there is at most one: `Reverts: <full commit SHA>`, the
  SHA as 40 lowercase hexadecimal digits, then nothing but spaces or tabs.
"""

import re

TIERS = ("low", "medium", "high")

# The separator is U+2014, the em dash; a hyphen or an en dash is malformed.
_RISK = re.compile("Risk: (%s) \u2014 (.*)" % "|".join(TIERS))
_REVERTS = re.compile(r"Reverts: ([0-9a-f]{40})[ \t]*")


def _risk(lines):
    if not lines:
        return "missing"
    if len(lines) > 1:
        return "more than one"
    match = _RISK.fullmatch(lines[0])
    reason = match.group(2).strip(" \t") if match else ""
    if not reason:
        return "malformed"
    return {"tier": match.group(1), "reason": reason}


def _reverts(lines):
    if not lines:
        return None
    if len(lines) > 1:
        return "more than one"
    match = _REVERTS.fullmatch(lines[0])
    return {"sha": match.group(1)} if match else "malformed"


def parse(body):
    """The body's risk and reverts.

    `risk` is {"tier", "reason"}, or "missing", "more than one" or "malformed". `reverts` is
    None when no line names one, {"sha"}, or "more than one" or "malformed".
    """
    lines = [line[:-1] if line.endswith("\r") else line for line in body.split("\n")]
    return {
        "risk": _risk([line for line in lines if line.startswith("Risk:")]),
        "reverts": _reverts([line for line in lines if line.startswith("Reverts:")]),
    }
