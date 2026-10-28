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

# A block mapping key: plain, double-quoted without escapes, or single-quoted; then the value.
_MAP_KEY = re.compile(
    r"""^(?:"([^"\\]*)"|'((?:[^']|'')*)'|([^\s?:,\[\]{}#&*!|>'"%@`-][^#]*?|-\S[^#]*?))[ \t]*:(?:[ \t]+(.*))?$"""
)
_BLOCK = re.compile(r"^[|>][-+0-9]*$")
_FALSE_VALUES = ("false", "False", "FALSE")


class _Unclear(Exception):
    pass


def _scan(line):
    """A line without its comment. A quote opens only where a scalar starts; one left open is unclear."""
    index, depth, at_start = 0, 0, True
    while index < len(line):
        char = line[index]
        if at_start and char in "\"'":
            index = _close_quote(line, index)
            at_start = False
            continue
        if char == "#" and (index == 0 or line[index - 1] in " \t"):
            line = line[:index]
            break
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
        elif char not in " \t":
            at_start = False
        index += 1
    if depth:
        raise _Unclear()
    return line.rstrip()


def _close_quote(line, index):
    """The index just past the quoted scalar opening at index."""
    quote, index = line[index], index + 1
    while index < len(line):
        if quote == '"' and line[index] == "\\":
            index += 2
            continue
        if line[index] == quote:
            if quote == "'" and line[index + 1:index + 2] == "'":
                index += 2
                continue
            return index + 1
        index += 1
    raise _Unclear()


def _kind(value):
    if not value:
        return "empty"
    if _BLOCK.match(value):
        return "block"
    if value[0] in "\"'":
        return "quoted"
    if value[0] in "[{":
        return "flow"
    if value[0] in "&*!%@`|>" or ": " in value or value.endswith(":"):
        raise _Unclear()
    return "plain"


class _Mapping(object):
    def __init__(self, indent, path):
        self.indent, self.path, self.keys = indent, path, set()
        self.last = None


def _read_mappings(text):
    """{key path: (kind, value)} for every block mapping key, raising _Unclear on a shape it won't guess at.

    Not a YAML parser: enough of block YAML for agents/openai.yaml, where anything real YAML
    would refuse must not pass, since Codex then ignores the whole file. Tabs in indentation,
    open quotes or flow collections, repeated keys, anchors, aliases, tags, merge keys, a
    second document or a misaligned line are unclear. Block scalars and sequences are
    skipped whole, and their keys never count.
    """
    text = text.replace("\r\n", "\n")
    if text.startswith("\ufeff") or "\r" in text:
        raise _Unclear()
    found, stack = {}, []
    skip_deeper, skip_dashes = None, None
    started = False
    for raw in text.split("\n"):
        if skip_deeper is not None:
            body = raw.lstrip(" ")
            indent = len(raw) - len(body)
            if not raw.strip() or indent > skip_deeper or (
                indent == skip_dashes and body[:1] == "-" and body[1:2] in ("", " ")
            ):
                continue
            skip_deeper = skip_dashes = None
        if "\t" in raw[:len(raw) - len(raw.lstrip(" \t"))]:
            raise _Unclear()
        line = _scan(raw)
        body = line.lstrip(" ")
        if not body:
            continue
        indent = len(line) - len(body)
        if indent == 0 and body.startswith(("---", "...", "%")):
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
        match = _MAP_KEY.match(body)
        if match:
            if top is None or top.indent < indent:
                if popped or (top is not None and (top.last is None or found[top.last][0] != "empty")):
                    raise _Unclear()
                path = top.last if top else ()
                if top:
                    found[path] = ("mapping", None)
                top = _Mapping(indent, path)
                stack.append(top)
            double, single, plain, value = match.groups()
            key = double if double is not None else single.replace("''", "'") if single is not None else plain.strip()
            if key in top.keys or key == "<<":
                raise _Unclear()
            top.keys.add(key)
            value = (value or "").strip()
            kind = _kind(value)
            top.last = top.path + (key,)
            found[top.last] = (kind, value)
            if kind == "block":
                skip_deeper = indent
            continue
        if top is None or top.last is None:
            raise _Unclear()
        kind = found[top.last][0]
        if body[:1] == "-" and body[1:2] in ("", " ") and kind == "empty" and indent >= top.indent and not popped:
            found[top.last] = ("sequence", None)
            skip_deeper, skip_dashes = indent, indent
        elif indent > top.indent and not popped and kind in ("empty", "plain", "next-line"):
            if kind == "empty":
                found[top.last] = ("next-line", None)
        else:
            raise _Unclear()
    return found


def codex_policy(codex_yaml):
    """The effective `policy.allow_implicit_invocation` in agents/openai.yaml, as Codex reads it.

    FALSE when the key is set to false, which alone makes a skill user-only; OTHER when the
    policy holds anything else, an empty policy or a missing key included; ABSENT when the file
    has no top-level `policy` key, in any spelling; and UNCLEAR when the file takes a shape
    this reader won't guess at (`_read_mappings`). Comments never count. Codex ignores a file
    real YAML refuses, so a reading of FALSE needs the whole file readable, and a FALSE
    reading is one the real CLI was recorded hiding (tests/fixtures/machine/codex-policy-shapes.json).
    """
    try:
        found = _read_mappings(codex_yaml.decode("utf-8"))
    except (_Unclear, UnicodeDecodeError):
        return UNCLEAR
    policy = found.get(("policy",))
    if policy is None:
        return ABSENT
    if policy[0] == "empty":
        return OTHER
    if policy[0] != "mapping":
        return UNCLEAR
    key = found.get(("policy", "allow_implicit_invocation"))
    if key is None or key[0] in ("empty", "quoted"):
        return OTHER
    if key[0] != "plain":
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
        """Whether Codex surely lists the skill for the model: its policy is readable and not user-only."""
        return self.policy in (ABSENT, OTHER)


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
