"""Skills on a machine: the machine skill set, content hashes, front matter and Codex's user-only key.

The machine skill set (#26) is the generator's skill directory, copied whole and kept in
stored form (ADR 0023), plus every skill copy under `skill-copies/skills/`, decoded from
stored form. A skill's content hash covers each file's path, mode and bytes, and leaves out
what a run leaves behind without changing the skill: `__pycache__`, `*.pyc` and `.DS_Store`.
"""

import hashlib
import os
import re
import subprocess

from machinelib import GENERATOR, MachineError

GENERATOR_SOURCE = "generator/govern-repository"
COPIES_SOURCE = "skill-copies/skills"
MACHINE_SOURCE = "machine"
SKILL_FILE = "SKILL.md"
CODEX_FILE = "agents/openai.yaml"
LEFT_BEHIND_DIRS = frozenset(["__pycache__"])
LEFT_BEHIND_FILES = frozenset([".DS_Store"])


def left_behind(name, is_dir):
    if is_dir:
        return name in LEFT_BEHIND_DIRS
    return name in LEFT_BEHIND_FILES or name.endswith(".pyc")


def content_hash(files):
    """The hash of a skill given as {relative path: (mode, bytes)}."""
    digest = hashlib.sha256()
    for rel in sorted(files):
        mode, data = files[rel]
        digest.update(("%s\0%s\0%s\n" % (rel, mode, hashlib.sha256(data).hexdigest())).encode("utf-8"))
    return digest.hexdigest()


def read_dir(path):
    """A skill directory on disk as {relative path: (mode, bytes)}; a symlink inside it is kept as its target."""
    found = {}
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if not left_behind(d, True))
        for name in list(dirs):
            full = os.path.join(root, name)
            if os.path.islink(full):
                dirs.remove(name)
                found[os.path.relpath(full, path).replace(os.sep, "/")] = ("120000", os.readlink(full).encode("utf-8"))
        for name in sorted(files):
            if left_behind(name, False):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, path).replace(os.sep, "/")
            if os.path.islink(full):
                found[rel] = ("120000", os.readlink(full).encode("utf-8"))
                continue
            with open(full, "rb") as handle:
                data = handle.read()
            found[rel] = ("100755" if os.stat(full).st_mode & 0o111 else "100644", data)
    return found


def disk_hash(path):
    """The content hash of a skill directory, or None when nothing is there."""
    if not os.path.isdir(path):
        return None
    return content_hash(read_dir(path))


def write_dir(path, files):
    """Write a skill given as {relative path: (mode, bytes)} into a new directory at path."""
    os.makedirs(path)
    for rel in sorted(files):
        mode, data = files[rel]
        full = os.path.join(path, *rel.split("/"))
        parent = os.path.dirname(full)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        with open(full, "wb") as handle:
            handle.write(data)
        os.chmod(full, 0o755 if mode == "100755" else 0o644)


def _git(source, *args):
    result = subprocess.run(["git", "-C", source] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise MachineError("源码树 %s 不是可读的 git checkout：git %s 失败：%s"
                           % (source, " ".join(args), result.stderr.decode("utf-8", "replace").strip()))
    return result.stdout


def tracked(source, prefix):
    """{path below prefix: (mode, bytes)} for every file git tracks under prefix in the source tree."""
    out = _git(source, "ls-files", "-z", "--", prefix).decode("utf-8")
    found = {}
    for path in out.split("\0"):
        if not path:
            continue
        full = os.path.join(source, *path.split("/"))
        with open(full, "rb") as handle:
            data = handle.read()
        found[path[len(prefix) + 1:]] = ("100755" if os.stat(full).st_mode & 0o111 else "100644", data)
    return found


def machine_skill_set(source):
    """{name: {relative path: (mode, bytes)}}: the generator whole, and each copy decoded from stored form."""
    from govlib import storedform

    skill_set = {GENERATOR: tracked(source, GENERATOR_SOURCE)}
    if not skill_set[GENERATOR]:
        raise MachineError("源码树里没有 %s" % GENERATOR_SOURCE)
    copies = {}
    for rel, entry in tracked(source, COPIES_SOURCE).items():
        name, _, inner = rel.partition("/")
        try:
            copies.setdefault(name, {})[storedform.decode(inner)] = entry
        except storedform.StoredFormError as error:
            raise MachineError("skill copy %s 无法解码：%s" % (name, error))
    if GENERATOR in copies:
        raise MachineError("skill copy 不能叫 %s" % GENERATOR)
    skill_set.update(copies)
    return skill_set


def source_commit(source):
    return _git(source, "rev-parse", "HEAD").decode("utf-8").strip()


def is_ancestor(source, older, newer):
    return subprocess.run(
        ["git", "-C", source, "merge-base", "--is-ancestor", older, newer],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


# Front matter -----------------------------------------------------------------------------

_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")


def front_matter(skill_md):
    """SKILL.md's top-level front-matter values as text, enough for name, description and invocation.

    Plain and double- or single-quoted values, and `>` or `|` blocks joined by spaces, as
    Codex renders them. A value this reader can't follow is left out.
    """
    lines = skill_md.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    else:
        return {}
    values = {}
    index = 0
    while index < len(body):
        match = _KEY.match(body[index])
        index += 1
        if not match:
            continue
        key, rest = match.group(1), match.group(2).strip()
        if rest in (">", "|", ">-", "|-", ">+", "|+") or rest == "":
            block = []
            while index < len(body) and (body[index].startswith((" ", "\t")) or not body[index].strip()):
                block.append(body[index].strip())
                index += 1
            if rest:
                values[key] = " ".join(part for part in block if part)
            continue
        if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in "\"'":
            values[key] = rest[1:-1]
        elif rest[0] not in "\"'[{":
            values[key] = rest.split(" #")[0].strip()
    return values


def user_invoked(meta):
    return meta.get("disable-model-invocation") == "true"


# Codex's user-only key ---------------------------------------------------------------------

FALSE, OTHER, ABSENT, UNCLEAR = "false", "other", "absent", "unclear"

# What the reader records for each key path: its value's kind.
EMPTY, PLAIN, QUOTED, BLOCK, MULTILINE, MAPPING, SEQUENCE = (
    "empty", "plain", "quoted", "block", "multi-line", "mapping", "sequence")
SCALARS = (EMPTY, PLAIN, QUOTED, BLOCK, MULTILINE)
ITEM = "[]"

# A block mapping key: plain, double-quoted without escapes, or single-quoted; then the value.
_MAP_KEY = re.compile(
    r"""^(?:"([^"\\]*)"|'((?:[^']|'')*)'|([^\s?:,\[\]{}#&*!|>'"%@`-][^#]*?|-\S[^#]*?))[ \t]*:(?:[ \t]+(.*))?$"""
)
_BLOCK = re.compile(r"^[|>][-+]?$")
# What a plain scalar can't hold: a leading `-` or `?`, or a `:` anywhere, then a blank (a tab
# too) or the end, which YAML reads as an indicator.
_NOT_PLAIN = re.compile(r"^[-?](?:[ \t]|$)|:(?:[ \t]|$)")
# Characters YAML refuses in a stream (C0 controls other than tab and newline, DEL, C1 and
# non-characters), and the line breaks other than newline, which this reader doesn't split on.
_REFUSED = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029\ufffe\uffff]")
_FALSE_VALUES = ("false", "False", "FALSE")
_BLANKS = " \t"


class _Unclear(Exception):
    pass


def _scan(line):
    """A line without its comment, or _Unclear for an open quote or flow collection, text after a
    closing quote, or an anchor, alias, tag or reserved indicator where a scalar starts."""
    index, depth, at_start = 0, 0, True
    while index < len(line):
        char = line[index]
        if at_start and char in "\"'":
            index = _close_quote(line, index)
            rest = line[index:].lstrip(_BLANKS)
            if rest and not (rest[0] == "#" or (rest[0] == ":" and rest[1:2] in ("", " ", "\t")) or (depth and rest[0] in ",]}")):
                raise _Unclear()
            at_start = False
            continue
        if char == "#" and (index == 0 or line[index - 1] in _BLANKS):
            line = line[:index]
            break
        if at_start and char in "&*!%@`":
            raise _Unclear()
        if char in "[{" and (at_start or depth):
            depth += 1
            at_start = True
        elif char in "]}" and depth:
            depth -= 1
            at_start = False
        elif char == "," and depth:
            at_start = True
        elif char in ":-" and line[index + 1:index + 2] in ("", " ", "\t") and (char == ":" or at_start):
            at_start = True
        elif at_start and char in "]},":
            raise _Unclear()
        elif char not in _BLANKS:
            at_start = False
        index += 1
    if depth:
        raise _Unclear()
    return line.rstrip(_BLANKS)


def _close_quote(line, index):
    """The index just past the quoted scalar opening at index; an escape is unclear, since a bad
    one makes real YAML refuse the file."""
    quote, index = line[index], index + 1
    while index < len(line):
        if quote == '"' and line[index] == "\\":
            raise _Unclear()
        if line[index] == quote:
            if quote == "'" and line[index + 1:index + 2] == "'":
                index += 2
                continue
            return index + 1
        index += 1
    raise _Unclear()


def _kind(value):
    if not value:
        return EMPTY
    if _BLOCK.match(value):
        return BLOCK
    if value[0] in "\"'":
        return QUOTED
    if value[0] in "[{|>" or _NOT_PLAIN.search(value):
        raise _Unclear()
    return PLAIN


class _Mapping(object):
    def __init__(self, indent, path):
        self.indent, self.path, self.keys = indent, path, set()
        self.last = None


def _read_mappings(text):
    """{key path: (kind, value)} for every key and sequence item, raising _Unclear on a shape it won't guess at.

    Not a YAML parser: enough of block YAML for agents/openai.yaml, where anything real YAML
    would refuse must not pass, since Codex then ignores the whole file. Tabs in indentation,
    refused characters, open quotes, escapes, flow collections, repeated keys, keys near
    YAML's 1024-character limit, anchors, aliases, tags, merge keys, complex keys, nested
    sequences, a second document, a tab in a block scalar or a misaligned line, block scalar
    lines included, are unclear. So is a value's next line, which may only continue a plain
    scalar, or start one under an empty key: one that isn't plain text, holds `: `, or follows
    a comment that ended the scalar. A sequence item's path ends with ITEM and its index; block
    scalars are skipped.
    """
    text = text.replace("\r\n", "\n")
    if text.startswith("\ufeff") or "\r" in text or _REFUSED.search(text):
        raise _Unclear()
    found, stack, sequences = {}, [], {}
    block = None  # A block scalar being skipped: [its key's indent, its content's indent, longest blank line before it].
    started = False
    ended = False  # Whether a comment has ended the last value's plain scalar, so no line may continue it.

    def add_key(indent, body, top, popped):
        match = _MAP_KEY.match(body)
        if top is None or top.indent < indent:
            if popped or (top is not None and (top.last is None or found[top.last][0] != EMPTY)):
                raise _Unclear()
            path = top.last if top else ()
            if top:
                found[path] = (MAPPING, None)
            top = _Mapping(indent, path)
            stack.append(top)
        double, single, plain, value = match.groups()
        key = double if double is not None else single.replace("''", "'") if single is not None else plain.strip(_BLANKS)
        if key in top.keys or key == "<<" or len(key) > 1000:
            raise _Unclear()
        top.keys.add(key)
        value = (value or "").strip(_BLANKS)
        top.last = top.path + (key,)
        found[top.last] = (_kind(value), value)
        return found[top.last][0]

    for raw in text.split("\n"):
        if block is not None:
            spaces = len(raw) - len(raw.lstrip(" "))
            if "\t" in raw and (spaces > block[0] or not raw.strip(_BLANKS)):
                raise _Unclear()
            if not raw.strip(_BLANKS):
                if block[1] is None:
                    block[2] = max(block[2], len(raw))
                continue
            if spaces > block[0]:
                if block[1] is None and block[2] > spaces or block[1] is not None and spaces < block[1]:
                    raise _Unclear()
                block[1] = spaces
                continue
            block = None
        if "\t" in raw[:len(raw) - len(raw.lstrip(_BLANKS))]:
            raise _Unclear()
        line = _scan(raw)
        commented = line != raw.rstrip(_BLANKS)
        body = line.lstrip(" ")
        if not body:
            ended = ended or commented
            continue
        indent = len(line) - len(body)
        if indent == 0 and body.startswith(("---", "...")):
            if body != "---" or started:
                raise _Unclear()
            started = True
            continue
        started = True
        popped = False
        while stack and stack[-1].indent > indent:
            stack.pop()
            popped = True
        top = stack[-1] if stack else None
        if _MAP_KEY.match(body):
            if add_key(indent, body, top, popped) == BLOCK:
                block = [indent, None, 0]
            ended = commented
            continue
        if top is None or top.last is None:
            raise _Unclear()
        owner, (kind, _) = top.last, found[top.last]
        if body[:1] == "-" and body[1:2] in ("", " "):
            if kind == EMPTY and indent >= top.indent and not popped:
                found[owner] = (SEQUENCE, None)
                sequences[owner] = [indent, 0]
            elif kind != SEQUENCE or sequences[owner][0] != indent:
                raise _Unclear()
            item = owner + (ITEM, sequences[owner][1])
            sequences[owner][1] += 1
            rest = body[1:].lstrip(" ")
            column = indent + len(body) - len(rest)
            if not rest or rest[:1] == "-" and rest[1:2] in ("", " "):
                raise _Unclear()
            if _MAP_KEY.match(rest):
                found[item] = (MAPPING, None)
                frame = _Mapping(column, item)
                stack.append(frame)
                if add_key(column, rest, frame, False) == BLOCK:
                    block = [column, None, 0]
            else:
                found[item] = (_kind(rest), rest)
            ended = commented
            continue
        # A value's next line. YAML reads it as plain text, quotes and brackets included, but this
        # reader follows only a line that is plain text at the start of a value too.
        continues = kind == EMPTY or kind in (PLAIN, MULTILINE) and not ended
        if indent > top.indent and not popped and continues and _kind(body) == PLAIN:
            found[owner] = (MULTILINE, None)
            ended = commented
        else:
            raise _Unclear()
    return found


def _typed(found):
    """Whether the keys Codex reads into typed fields hold what it accepts, as recorded from the real CLI.

    Codex ignores unknown keys, but drops the whole file when a field it knows has the wrong
    type: `interface` and `dependencies` must be mappings, `interface`'s values scalars, and
    `dependencies.tools` a sequence of mappings with scalar values. `policy` may hold only
    `allow_implicit_invocation`, since another of its fields with the wrong type drops the file.
    """
    for path, (kind, _) in found.items():
        if len(path) == 1 and path[0] in ("interface", "dependencies", "policy") and kind not in (EMPTY, MAPPING):
            return False
        if path[:1] == ("interface",) and len(path) == 2 and kind not in SCALARS:
            return False
        if path[:2] == ("dependencies", "tools"):
            if len(path) == 2 and kind not in (EMPTY, SEQUENCE):
                return False
            if len(path) == 4 and kind != MAPPING:
                return False
            if len(path) == 5 and kind not in SCALARS:
                return False
        if path[:1] == ("policy",) and len(path) == 2 and path[1] != "allow_implicit_invocation":
            return False
    return True


def codex_policy(codex_yaml):
    """The effective `policy.allow_implicit_invocation` in agents/openai.yaml, as Codex reads it.

    FALSE when the key is set to false, which alone makes a skill user-only; OTHER when the
    policy holds anything else, an empty policy or a missing key included; ABSENT when the file
    has no top-level `policy` key, in any spelling; and UNCLEAR when the file takes a shape
    this reader won't guess at (`_read_mappings`, `_typed`). Comments never count. Codex
    ignores a file real YAML refuses, or whose known fields have the wrong type, so a reading
    of FALSE needs the whole file readable. Every shape in
    tests/fixtures/machine/codex-policy-shapes.json is checked against the real CLI's listing.
    """
    try:
        found = _read_mappings(codex_yaml.decode("utf-8"))
    except (_Unclear, UnicodeDecodeError):
        return UNCLEAR
    if not _typed(found):
        return UNCLEAR
    policy = found.get(("policy",))
    if policy is None:
        return ABSENT
    if policy[0] == EMPTY:
        return OTHER
    key = found.get(("policy", "allow_implicit_invocation"))
    if key is None or key[0] in (EMPTY, QUOTED):
        return OTHER
    if key[0] != PLAIN:
        return UNCLEAR
    return FALSE if key[1] in _FALSE_VALUES else OTHER


# Skills on disk ----------------------------------------------------------------------------


class Skill(object):
    """A skill directory in a skill root: its directory name, front matter and Codex policy."""

    def __init__(self, root, name):
        self.root = root
        self.dir_name = name
        self.path = os.path.join(root, name)
        self.linked = os.path.islink(self.path)
        with open(os.path.join(self.path, SKILL_FILE), "rb") as handle:
            self.meta = front_matter(handle.read())
        self.name = self.meta.get("name") or name
        codex = os.path.join(self.path, *CODEX_FILE.split("/"))
        if os.path.isfile(codex):
            with open(codex, "rb") as handle:
                self.codex_yaml = handle.read()
        else:
            self.codex_yaml = None
        self.policy = ABSENT if self.codex_yaml is None else codex_policy(self.codex_yaml)

    @property
    def user_invoked(self):
        return user_invoked(self.meta)

    @property
    def listed_by_codex(self):
        """Whether Codex may list the skill for the model: unless its policy reads as user-only, so an unclear one may."""
        return self.policy != FALSE


def skills_in(root):
    """Every skill directly under a skill root, skipping dot directories and directories without SKILL.md."""
    if not os.path.isdir(root):
        return []
    found = []
    for name in sorted(os.listdir(root)):
        if name.startswith("."):
            continue
        if os.path.isfile(os.path.join(root, name, SKILL_FILE)):
            found.append(Skill(root, name))
    return found
