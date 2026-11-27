"""Credential shapes (#41 §10): a credential is named by its type and location, never by its value.

The inspection reports where a shape is found (`kinds`), and the entry passes every fact it
prints through `redact`, so no value read from a repository or from GitHub, a command's
text, a title or an error included, reaches the session's output.
"""

import json
import re

# Each shape, by the type habit hears.
SHAPES = (
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})")),
    ("AWS access key ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    # From the header to its end marker, or to the end of the text when there is none.
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----|[\s\S]*)")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
)


KEY_BEGIN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
KEY_END = re.compile(r"-----END [A-Z ]*PRIVATE KEY-----")


def kinds(text):
    """The types of the credential shapes in text, in SHAPES order."""
    return [kind for kind, pattern in SHAPES if pattern.search(text)]


# The same line boundaries as str.splitlines(), including CR-only files.
_LINE_BREAK = re.compile(r"\r\n|[\r\n\v\f\x1c-\x1e\x85\u2028\u2029]")


def _redact_text(text, path):
    # Match on the original input: replacing one shape first can hide the start of another.
    spans = sorted((m.start(), m.end(), kind) for kind, pattern in SHAPES for m in pattern.finditer(text))
    if not spans:
        return text
    if path is not None:
        # JSON escapes control characters. Escape the other Unicode line separators too
        # so placing a filename inside a marker never inserts another source line.
        location = json.dumps(redact(path), ensure_ascii=False)[1:-1]
        location = location.translate({0x85: r"\u0085", 0x2028: r"\u2028", 0x2029: r"\u2029"})
    output = []
    covered_end = previous_start = 0
    line = 1
    for start, end, kind in spans:
        if end <= covered_end:
            continue  # Already fully hidden, e.g. inside a multiline private key.
        output.append(text[covered_end:start])
        if path is None:
            output.append("<redacted %s>" % kind)
        else:
            line += sum(1 for _ in _LINE_BREAK.finditer(text, previous_start, start))
            output.append("<redacted %s at %s:%d>" % (kind, location, line))
            output.extend(_LINE_BREAK.findall(text, max(covered_end, start), end))
        covered_end = end
        previous_start = start
    output.append(text[covered_end:])
    return "".join(output)


def redact(value, path=None):
    """Replace credential values in strings and mapping keys, optionally recording locations."""
    if isinstance(value, str):
        return _redact_text(value, path)
    if isinstance(value, dict):
        return dict((redact(key), redact(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value
