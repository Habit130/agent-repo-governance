"""Synthetic examples for the generator and machine non-disclosure checks."""

from urllib.parse import quote, quote_plus

# The fixture name is part of the on-disk generator case format. Assemble the
# nonfunctional values here so a fixture never needs to store a token literal.
_SHAPES = {
    "GitHub token": ("github-token", "gh" + "p_" + "Z" * 36),
    "AWS access key ID": ("aws-key", "AK" + "IA" + "Z" * 16),
    "Slack token": ("slack-token", "xo" + "xb-" + "Z" * 24),
    "private key": ("private-key", "-----BEGIN " + "RSA PRIVATE KEY-----"),
    "Anthropic API key": ("anthropic-key", "sk-" + "ant-" + "Z" * 24),
    "OpenAI API key": ("openai-key", "sk-" + "proj-" + "Z" * 24),
    "Google API key": ("google-key", "AI" + "za" + "Z" * 35),
}
SHAPE_PLANTS = {kind: name for kind, (name, value) in _SHAPES.items()}
PLANTED = {name: value for name, value in _SHAPES.values()}
PLANTED.update({
    "private-key-body": "MIIE" + "Q" * 60,
    "private-key-end": "-----END " + "RSA PRIVATE KEY-----",
})

# These markers have no recognizable token shape. Their position in a URL is
# what makes them private. Search for the marker itself even if its URL changes.
_URL_FIELDS = {
    "password": ("URL userinfo", "synthetic-" + "userinfo", "https://fixture:%s@example.invalid/project"),
    "query": ("URL query", "synthetic-" + "query", "https://example.invalid/project?ref=%s"),
    "fragment": ("URL fragment", "synthetic-" + "fragment", "https://example.invalid/project#%s"),
}
URL_PARTS = {name: marker for name, (kind, marker, url) in _URL_FIELDS.items()}
SAMPLES = {kind: value for kind, (name, value) in _SHAPES.items()}
# Shell helpers and Git identity fields need a single line. Closing the key
# also prevents it from swallowing any samples that follow it during redaction.
SAMPLES["private key"] = " ".join(PLANTED[name] for name in ("private-key", "private-key-body", "private-key-end"))
SAMPLES.update({kind: url % marker for kind, marker, url in _URL_FIELDS.values()})
FIELD = " ".join(SAMPLES.values())
_MARKERS = {**PLANTED, **URL_PARTS}
_LOG_MARKERS = {spelling: "<planted:%s>" % name
                for name, marker in _MARKERS.items()
                for spelling in (marker, quote(marker, safe=""), quote_plus(marker, safe=""))}


def mask_log_value(value):
    """Replace only fixture markers in a copy of a stand-in audit entry."""
    if isinstance(value, dict):
        return {key: mask_log_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_log_value(item) for item in value]
    if isinstance(value, str):
        for marker, placeholder in _LOG_MARKERS.items():
            value = value.replace(marker, placeholder)
    return value


def assert_absent(test, text, location):
    for name, marker in _MARKERS.items():
        if marker in text:
            test.fail("plant disclosed: %s in %s" % (name, location))


def assert_no_values(test, out, err):
    assert_absent(test, out, "stdout")
    assert_absent(test, err, "stderr")
