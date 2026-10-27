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
CODEX_KEY = b"policy:\n  allow_implicit_invocation: false\n"
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


def _uncommented(line):
    """A YAML line without its comment; quotes are rare here, so a quoted `#` makes the line unclear."""
    if line.lstrip().startswith("#"):
        return ""
    if "#" in line and ("'" in line or '"' in line):
        return None
    return re.split(r"\s#", line, maxsplit=1)[0].rstrip()


def codex_policy(codex_yaml):
    """The effective `policy.allow_implicit_invocation` in agents/openai.yaml.

    FALSE when the key is set to false, OTHER when it holds anything else or no key sits in
    the block, ABSENT when there is no top-level `policy` key, and UNCLEAR when the file
    uses a shape this reader won't guess at: flow collections, quoted comments, repeats.
    Comments never count, so `# allow_implicit_invocation: false` is no key.
    """
    lines = codex_yaml.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
    policies = []
    for index, raw in enumerate(lines):
        line = _uncommented(raw)
        if line is None:
            return UNCLEAR
        if line.startswith("policy:"):
            policies.append(index)
    if not policies:
        return ABSENT
    if len(policies) > 1:
        return UNCLEAR
    start = policies[0]
    if _uncommented(lines[start])[len("policy:"):].strip():
        return UNCLEAR
    children = []
    for raw in lines[start + 1:]:
        line = _uncommented(raw)
        if line is None:
            return UNCLEAR
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            break
        children.append(line)
    if not children:
        return OTHER
    indent = min(len(line) - len(line.lstrip()) for line in children)
    values = []
    for line in children:
        if len(line) - len(line.lstrip()) != indent:
            continue
        match = _KEY.match(line.strip())
        if not match:
            return UNCLEAR
        if match.group(1) == "allow_implicit_invocation":
            values.append(match.group(2).strip())
    if len(values) > 1:
        return UNCLEAR
    if values and values[0] in ("false", "False", "FALSE"):
        return FALSE
    return OTHER


def with_codex_key(codex_yaml):
    """The file with the key appended as a new `policy:` block; only for a file without one."""
    if codex_yaml and not codex_yaml.endswith(b"\n"):
        codex_yaml += b"\n"
    return codex_yaml + CODEX_KEY


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
        self.codex_file = codex
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
        """Whether Codex lists the skill for the model: unless its policy sets the key to false."""
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
