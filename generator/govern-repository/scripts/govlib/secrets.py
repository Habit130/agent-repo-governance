"""Credential shapes (#41 §10): a credential is named by its type and location, never by its value.

The inspection reports where a shape is found (`kinds`), and the entry passes every fact it
prints through `redact`, so no value read from a repository or from GitHub, a command's
text, a title or an error included, reaches the session's output.
"""

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


def redact(value):
    """value with every credential shape in its strings, keys included, replaced by its type."""
    if isinstance(value, str):
        for kind, pattern in SHAPES:
            value = pattern.sub("<redacted %s>" % kind, value)
        return value
    if isinstance(value, dict):
        return dict((redact(key), redact(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value
