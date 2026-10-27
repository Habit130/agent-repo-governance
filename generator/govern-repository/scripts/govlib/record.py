"""The governance record (#44 §4, #41 §1): the machine side's parser.

A record is a strict YAML subset: block mappings and sequences, plain or double-quoted
scalars, and `#` comments. Anything else doesn't parse. In detail:

- The file is UTF-8 with LF line endings. It holds no byte order mark, no tab, no other
  control character, none of U+2028 and U+2029, which some YAML readers take as line
  breaks, and neither U+FFFE nor U+FFFF. A final newline, trailing spaces and blank lines
  are optional.
- Indentation is spaces. A nested block is indented more than its key, and a sequence may
  also sit at its key's own indentation.
- A double-quoted scalar closes on its line, and its only escapes are `\\"` and `\\\\`.
- A plain scalar is one line, and it doesn't start with an indicator. Where text is
  expected, a plain scalar doesn't parse when YAML 1.1 or 1.2 could read it as null or a
  boolean, or when it starts like a number: with a digit, or with `+`, `-` or `.` and then
  a digit, or as an infinity or not-a-number form. `2fa/**` is double-quoted, then.
- There are no anchors, aliases, tags, flow collections, block scalars, single-quoted
  scalars, directives, document markers or duplicate keys.

The keys come in this order: `version`, a positive integer written plain; `agent_account`;
`sensitive_paths`; then `confirmed`, holding `sensitive_paths` and `required_checks`. Each
sensitive path is a `pattern`, kept as written, with a `floor` of `medium` or `high`. A list
key with no items is an empty list: in YAML its value is null, and the record reads null
there as no items. `parse` returns the record as plain dicts, lists, strings and an int.
"""

import re

from govlib import GovernError

FLOORS = ("medium", "high")

# What a record never holds: every control character but LF, the line and paragraph
# separators, a byte order mark, the two noncharacters outside YAML's printable set, and
# surrogates. Text holds no LF either.
_NEVER = "\x00-\x09\x0b-\x1f\x7f-\x9f\u2028\u2029\ufeff\ufffe\uffff\ud800-\udfff"
_FORBIDDEN = re.compile("[%s]" % _NEVER)
_FORBIDDEN_IN_TEXT = re.compile("[\n%s]" % _NEVER)
_INDICATORS = ",[]{}#&*!|>'%@`"
# Plain scalars that aren't text: the YAML 1.1 and 1.2 null and boolean words, and anything
# starting like a number (a date included), which also refuses some text, such as `2fa/**`,
# that YAML would read as a string. Such text is double-quoted.
_NOT_TEXT = re.compile(
    r"(?:~|null|Null|NULL|true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO|on|On|ON|off|Off|OFF|y|Y|n|N"
    r"|[-+]?\.?[0-9].*|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))"
)
_VERSION = re.compile(r"[1-9][0-9]*")

RECORD_KEYS = ("version", "agent_account", "sensitive_paths", "confirmed")
CONFIRMED_KEYS = ("sensitive_paths", "required_checks")
PATH_KEYS = ("pattern", "floor")


class RecordError(GovernError):
    """The record doesn't parse; the message names the line and what is wrong."""


def is_text(value):
    """Whether value can be a record's text: a non-empty string on one line, with no control character."""
    return isinstance(value, str) and bool(value) and not _FORBIDDEN_IN_TEXT.search(value)


class _Scalar(object):
    def __init__(self, text, quoted, line):
        self.text, self.quoted, self.line = text, quoted, line


class _Mapping(object):
    def __init__(self, line):
        self.line, self.entries = line, []


class _Sequence(object):
    def __init__(self, line):
        self.line, self.items = line, []


def _fail(line, message):
    raise RecordError("line %d %s" % (line, message))


def _quoted(content, line):
    """A double-quoted scalar at the start of content: (its text, the rest of content)."""
    out, index = [], 1
    while index < len(content):
        char = content[index]
        if char == '"':
            return "".join(out), content[index + 1:]
        if char == "\\":
            escaped = content[index + 1:index + 2]
            if escaped not in ('"', "\\"):
                _fail(line, 'has the escape \\%s; a double-quoted scalar escapes only \\" and \\\\' % escaped)
            out.append(escaped)
            index += 2
            continue
        out.append(char)
        index += 1
    _fail(line, "has a double-quoted scalar that doesn't close on its line")


def _plain(text, line):
    """Check a plain scalar's text."""
    if not text:
        _fail(line, "has an empty plain scalar")
    first, second = text[0], text[1:2]
    if first in _INDICATORS or first == '"' or (first in "-?:" and second in ("", " ")):
        _fail(line, "has a plain scalar starting with the indicator %r, which the record's subset doesn't allow" % first)
    if text.endswith(":"):
        _fail(line, "has a plain scalar ending with `:`")
    return _Scalar(text, False, line)


def _after_scalar(rest, line):
    """What may follow a scalar on its line: nothing, or a comment after a space."""
    stripped = rest.lstrip(" ")
    if stripped and not (stripped.startswith("#") and stripped != rest):
        _fail(line, "has %r after a scalar" % rest)


def _value(text, line):
    """A scalar value on a key's or an item's line."""
    if text.startswith('"'):
        value, rest = _quoted(text, line)
        _after_scalar(rest, line)
        return _Scalar(value, True, line)
    comment = text.find(" #")
    if comment >= 0:
        text = text[:comment]
    text = text.rstrip(" ")
    if ": " in text:
        _fail(line, "has a mapping inside a value, which the record's subset doesn't allow")
    return _plain(text, line)


def _split(content, line):
    """A line's content as ("item", rest), ("entry", key, value text) or ("scalar", scalar)."""
    if content == "-" or content.startswith("- "):
        return ("item", content[1:])
    if content.startswith('"'):
        key, rest = _quoted(content, line)
        stripped = rest.lstrip(" ")
        if stripped == ":" or stripped.startswith(": "):
            return ("entry", _Scalar(key, True, line), stripped[1:])
        _after_scalar(rest, line)
        return ("scalar", _Scalar(key, True, line))
    index = 0
    while index < len(content):
        if content[index] == ":" and content[index + 1:index + 2] in ("", " "):
            return ("entry", _plain(content[:index].rstrip(" "), line), content[index + 1:])
        if content[index] == "#" and index > 0 and content[index - 1] == " ":
            break
        index += 1
    return ("scalar", _value(content, line))


def _node_lines(text):
    """[line number, indentation, content] for every line that isn't blank or a comment."""
    nodes = []
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip(" ")
        content = line.lstrip(" ")
        if content and not content.startswith("#"):
            nodes.append([number, len(line) - len(content), content])
    return nodes


def _node(nodes, index):
    """The node starting at nodes[index], at that line's indentation: (node, next index)."""
    number, indent, content = nodes[index]
    form = _split(content, number)
    if form[0] == "item":
        return _sequence(nodes, index, indent)
    if form[0] == "entry":
        return _mapping(nodes, index, indent)
    return form[1], index + 1


def _nested(nodes, index, indent, compact):
    """The block a key or an item with no inline value holds, or None when it holds nothing.

    A key's block may also be a sequence at the key's own indentation (compact).
    """
    if index < len(nodes) and nodes[index][1] > indent:
        return _node(nodes, index)
    if compact and index < len(nodes) and nodes[index][1] == indent:
        if _split(nodes[index][2], nodes[index][0])[0] == "item":
            return _sequence(nodes, index, indent)
    return None, index


def _mapping(nodes, index, indent):
    mapping = _Mapping(nodes[index][0])
    while index < len(nodes) and nodes[index][1] >= indent:
        number, here, content = nodes[index]
        if here > indent:
            _fail(number, "is indented more than the mapping it sits in")
        form = _split(content, number)
        if form[0] != "entry":
            _fail(number, "is not a `key: value` entry of the mapping it sits in")
        key, rest = form[1], form[2].lstrip(" ")
        if any(existing.text == key.text for existing, _ in mapping.entries):
            _fail(number, "repeats the key %s" % key.text)
        if rest and not rest.startswith("#"):
            value, index = _value(rest, number), index + 1
        else:
            value, index = _nested(nodes, index + 1, indent, compact=True)
        mapping.entries.append((key, value))
    return mapping, index


def _sequence(nodes, index, indent):
    sequence = _Sequence(nodes[index][0])
    while index < len(nodes) and nodes[index][1] >= indent:
        number, here, content = nodes[index]
        if here > indent:
            _fail(number, "is indented more than the sequence it sits in")
        form = _split(content, number)
        if form[0] != "item":
            break
        rest = form[1]
        inline = rest.lstrip(" ")
        if not inline or inline.startswith("#"):
            item, index = _nested(nodes, index + 1, indent, compact=False)
        else:
            nodes[index] = [number, here + len(rest) - len(inline) + 1, inline]
            item, index = _node(nodes, index)
        sequence.items.append(item)
    return sequence, index


def _tree(text):
    nodes = _node_lines(text)
    if not nodes:
        raise RecordError("the record is empty")
    root, index = _node(nodes, 0)
    if index < len(nodes):
        _fail(nodes[index][0], "is outside the record's top-level mapping")
    return root


def _keys(node, keys, what, line):
    """A mapping's values by key, as (value, line), once its keys are exactly keys in order."""
    if not isinstance(node, _Mapping):
        _fail(getattr(node, "line", line), "must hold %s as a mapping of %s" % (what, ", ".join(keys)))
    found = tuple(key.text for key, _ in node.entries)
    if found != keys:
        unknown = [key for key in found if key not in keys]
        missing = [key for key in keys if key not in found]
        if unknown:
            problem = "the unknown key %s" % ", ".join(unknown)
        elif missing:
            problem = "no key %s" % ", ".join(missing)
        else:
            problem = "its keys out of order"
        _fail(node.line, "starts %s, which has %s; it holds %s, in that order" % (what, problem, ", ".join(keys)))
    return dict((key.text, (value, key.line)) for key, value in node.entries)


def _text(value, line, what):
    if not isinstance(value, _Scalar):
        _fail(line, "must give %s as text" % what)
    if not value.quoted and _NOT_TEXT.fullmatch(value.text):
        _fail(value.line, "gives %s as %r, which YAML can read as other than text; double-quote it" % (what, value.text))
    if not is_text(value.text):
        _fail(value.line, "gives %s as empty text or text with a control character" % what)
    return value.text


def _list(value, line, what, item):
    if value is None:
        return []
    if not isinstance(value, _Sequence):
        _fail(line, "must give %s as a block sequence" % what)
    return [item(element, line) for element in value.items]


def _sensitive_path(node, line):
    entries = _keys(node, PATH_KEYS, "a sensitive path", line)
    pattern = _text(*entries["pattern"], what="a pattern")
    floor = _text(*entries["floor"], what="a floor")
    if floor not in FLOORS:
        _fail(entries["floor"][1], "gives the floor %r; a floor is medium or high" % floor)
    return {"pattern": pattern, "floor": floor}


def _required_check(node, line):
    return _text(node, getattr(node, "line", line), "a required check")


def parse(data):
    """The record in data's bytes, or RecordError when it doesn't parse."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise RecordError("the record is not UTF-8")
    forbidden = _FORBIDDEN.search(text)
    if forbidden:
        _fail(text.count("\n", 0, forbidden.start()) + 1, "holds the character U+%04X" % ord(forbidden.group()))

    entries = _keys(_tree(text), RECORD_KEYS, "the record", 1)
    version, line = entries["version"]
    if not isinstance(version, _Scalar) or version.quoted or not _VERSION.fullmatch(version.text):
        _fail(line, "must give version as a positive integer, written plain")
    confirmed = _keys(entries["confirmed"][0], CONFIRMED_KEYS, "confirmed", entries["confirmed"][1])
    return {
        "version": int(version.text),
        "agent_account": _text(*entries["agent_account"], what="agent_account"),
        "sensitive_paths": _list(*entries["sensitive_paths"], what="sensitive_paths", item=_sensitive_path),
        "confirmed": {
            "sensitive_paths": _list(*confirmed["sensitive_paths"], what="confirmed sensitive_paths", item=_sensitive_path),
            "required_checks": _list(*confirmed["required_checks"], what="required_checks", item=_required_check),
        },
    }
