"""Skill copies (#44 §10, ADR 0020): what a copy is, where upstream keeps it, and the one allowed change.

`skill-copies/` holds `LICENSE` (upstream's, byte-identical), `provenance.json`, and one
copy per relied-on skill under `skills/<name>/`: the skill's whole upstream directory at one
recorded commit, in stored form (#44 §3). The one allowed change appends the Codex user-only
key to `agents/openai.yaml` of a user-invoked skill (`disable-model-invocation: true`) that
lacks it. The scripts here sit outside every copy.

The manifest, `provenance.json`:

    {"license": {"repository": ..., "path": "LICENSE", "commit": ...},
     "copies": [{"name": ..., "repository": ..., "path": ..., "commit": ..., "codex_key_added": ...}]}
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
COPIES = os.path.dirname(HERE)
REPO = os.path.dirname(COPIES)
STORE = os.path.join(REPO, "generator", "govern-repository", "store")
sys.path.insert(0, os.path.join(REPO, "generator", "govern-repository", "scripts"))

from govlib import storedform  # noqa: E402
from govlib import store as template_store  # noqa: E402

PROVENANCE = "provenance.json"
LICENSE = "LICENSE"
SKILLS = "skills"
REPOSITORY = "mattpocock/skills"
CODEX_FILE = "agents/openai.yaml"
CODEX_KEY = b"policy:\n  allow_implicit_invocation: false\n"
# On the relied-on list, but this repository's own skill rather than a copy.
NOT_COPIED = frozenset(["govern-repository"])
MODES = ("100644", "100755")

_SHA = re.compile(r"^[0-9a-f]{40}$")
_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_COPY_KEYS = {"name", "repository", "path", "commit", "codex_key_added"}
_LICENSE_KEYS = {"repository", "path", "commit"}


class CopyError(Exception):
    """A refusal: the facts needed to refresh or verify aren't there."""


def relied_on(store_root=STORE):
    """The highest version's relied-on skills that are copies, sorted."""
    try:
        source = template_store.Store(store_root)
        versions = source.versions()
        if not versions:
            raise CopyError("the template store %r has no version" % store_root)
        skills = source.manifest(versions[-1])["relied_on_skills"]
    except template_store.StoreError as error:
        raise CopyError(str(error))
    return sorted(set(skills) - NOT_COPIED)


def front_matter(skill_md):
    """SKILL.md's front-matter lines, without line endings; empty when it has none."""
    lines = [line.rstrip("\r") for line in skill_md.decode("utf-8", "replace").split("\n")]
    if not lines or lines[0] != "---":
        return []
    found = []
    for line in lines[1:]:
        if line == "---":
            return found
        found.append(line)
    return []


def user_invoked(skill_md):
    """Whether SKILL.md's front matter sets `disable-model-invocation: true`."""
    return any(line.strip() == "disable-model-invocation: true" for line in front_matter(skill_md))


def _policy_block(codex_yaml):
    """The values under a top-level `policy` key, inline or indented, or None when there is no such key."""
    lines = codex_yaml.decode("utf-8", "replace").split("\n")
    for index, line in enumerate(lines):
        if line.startswith("policy:"):
            block = [line[len("policy:"):].strip()]
            for following in lines[index + 1:]:
                if following[:1] not in (" ", "\t") and following.strip():
                    break
                block.append(following.strip())
            return block
    return None


def has_codex_key(codex_yaml):
    block = _policy_block(codex_yaml)
    return block is not None and any("allow_implicit_invocation: false" in value for value in block)


def add_codex_key(codex_yaml):
    """Upstream's bytes with the key appended as a new `policy:` block, the one allowed change."""
    if _policy_block(codex_yaml) is not None:
        raise CopyError("its %s has a policy block without the key, so appending one would repeat it" % CODEX_FILE)
    if codex_yaml and not codex_yaml.endswith(b"\n"):
        codex_yaml += b"\n"
    return codex_yaml + CODEX_KEY


def _git_env():
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


class Upstream(object):
    """Upstream commits fetched read-only into a temporary bare repository."""

    def __init__(self, source, commits):
        self.source = source
        self.root = tempfile.mkdtemp(prefix="skill-copies-upstream-")
        try:
            self._git("init", "--quiet", "--bare")
            self._git("fetch", "--quiet", "--no-tags", source, *sorted(set(commits)))
        except (CopyError, OSError) as error:
            self.close()
            raise CopyError("fetching %s from %s failed: %s" % (", ".join(sorted(set(commits))), source, error))

    def close(self):
        shutil.rmtree(self.root, True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _git(self, *args):
        result = subprocess.run(
            ["git", "-C", self.root] + list(args), env=_git_env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            raise CopyError("git %s failed: %s" % (" ".join(args), result.stderr.decode("utf-8", "replace").strip()))
        return result.stdout

    def entries(self, commit, path):
        """{path below `path`: (mode, blob)} for every entry under path at commit."""
        out = self._git("ls-tree", "-r", "-z", "--full-tree", commit, "--", path).decode("utf-8")
        found = {}
        for record in out.split("\0"):
            if not record:
                continue
            meta, full = record.split("\t", 1)
            mode, _, sha = meta.split(" ")
            if full == path:
                found[""] = (mode, sha)
            elif full.startswith(path + "/"):
                found[full[len(path) + 1:]] = (mode, sha)
        return found

    def blob(self, sha):
        return self._git("cat-file", "blob", sha)

    def files(self, commit, path):
        """{path below `path`: (mode, bytes)}, refusing anything that isn't a regular file."""
        found = {}
        for rel, (mode, sha) in sorted(self.entries(commit, path).items()):
            if mode not in MODES:
                raise CopyError("%s/%s has mode %s at %s, which a copy can't hold" % (path, rel, mode, commit[:12]))
            found[rel] = (mode, self.blob(sha))
        return found

    def tree_files(self, commit, path):
        """files(), refused when nothing is at path: a copy's recorded path must exist."""
        found = self.files(commit, path)
        if not found:
            raise CopyError("%s holds nothing at %s" % (path, commit[:12]))
        return found

    def file(self, commit, path):
        entry = self.entries(commit, path).get("")
        if entry is None:
            raise CopyError("%s isn't a file at %s" % (path, commit[:12]))
        if entry[0] not in MODES:
            raise CopyError("%s has mode %s at %s, which a copy can't hold" % (path, entry[0], commit[:12]))
        return entry[0], self.blob(entry[1])

    def locate(self, commit, name):
        """The one `skills/<group>/<name>` directory holding a SKILL.md at commit, or None."""
        out = self._git("ls-tree", "-r", "-z", "--name-only", "--full-tree", commit, "--", SKILLS).decode("utf-8")
        pattern = re.compile(r"^skills/[^/]+/%s/SKILL\.md$" % re.escape(name))
        found = sorted(path[: -len("/SKILL.md")] for path in out.split("\0") if pattern.match(path))
        if len(found) > 1:
            raise CopyError("%s sits at more than one path at %s: %s" % (name, commit[:12], ", ".join(found)))
        return found[0] if found else None

    def is_ancestor(self, older, newer):
        return subprocess.run(
            ["git", "-C", self.root, "merge-base", "--is-ancestor", older, newer], env=_git_env()
        ).returncode == 0


def expected_copy(upstream, commit, path):
    """(the copy's files as {real path: (mode, bytes)}, whether the Codex key is added)."""
    files = upstream.files(commit, path)
    if "SKILL.md" not in files:
        raise CopyError("%s has no SKILL.md at %s" % (path, commit[:12]))
    for rel in files:
        try:
            storedform.encode(rel)
        except storedform.StoredFormError as error:
            raise CopyError("%s: %s" % (path, error))
    if not user_invoked(files["SKILL.md"][1]):
        return files, False
    if CODEX_FILE not in files:
        raise CopyError("%s is user-invoked but has no %s at %s" % (path, CODEX_FILE, commit[:12]))
    mode, data = files[CODEX_FILE]
    if has_codex_key(data):
        return files, False
    try:
        files[CODEX_FILE] = (mode, add_codex_key(data))
    except CopyError as error:
        raise CopyError("%s: %s" % (path, error))
    return files, True


def copy_files(copy_dir):
    """A copy on disk as {real path: (mode, bytes)}."""
    found = {}
    try:
        for rel, full in storedform.stored_files(copy_dir):
            with open(full, "rb") as handle:
                found[storedform.decode(rel)] = (storedform.mode_of(full), handle.read())
    except storedform.StoredFormError as error:
        raise CopyError(str(error))
    return found


def differences(expected, actual):
    """What separates a copy on disk from what it should hold, one line per file."""
    found = []
    for rel in sorted(set(expected) | set(actual)):
        if rel not in actual:
            found.append("%s is missing" % rel)
        elif rel not in expected:
            found.append("%s isn't upstream" % rel)
        else:
            (want_mode, want), (mode, data) = expected[rel], actual[rel]
            if data != want:
                offset = next((i for i, (a, b) in enumerate(zip(want, data)) if a != b), min(len(want), len(data)))
                found.append("%s differs from byte %d" % (rel, offset))
            if mode != want_mode:
                found.append("%s has mode %s, upstream %s" % (rel, mode, want_mode))
    return found


def copies_on_disk(copies_root):
    skills = os.path.join(copies_root, SKILLS)
    if not os.path.isdir(skills):
        return []
    return sorted(name for name in os.listdir(skills) if name not in storedform.IGNORED_NAMES)


def load_provenance(copies_root):
    path = os.path.join(copies_root, PROVENANCE)
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise CopyError("%s can't be read: %s" % (PROVENANCE, error))
    if not isinstance(data, dict) or set(data) != {"license", "copies"}:
        raise CopyError("%s must hold exactly license and copies" % PROVENANCE)
    license_entry = data["license"]
    if not isinstance(license_entry, dict) or set(license_entry) != _LICENSE_KEYS:
        raise CopyError("%s's license must hold exactly %s" % (PROVENANCE, ", ".join(sorted(_LICENSE_KEYS))))
    _check_source(license_entry, "the license")
    if not isinstance(data["copies"], list):
        raise CopyError("%s's copies must be a list" % PROVENANCE)
    names = set()
    for entry in data["copies"]:
        if not isinstance(entry, dict) or set(entry) != _COPY_KEYS:
            raise CopyError("%s has a copy without exactly %s: %r" % (PROVENANCE, ", ".join(sorted(_COPY_KEYS)), entry))
        name = entry["name"]
        if not isinstance(name, str) or not _NAME.match(name) or name in names:
            raise CopyError("%s names copy %r twice or not as a skill name" % (PROVENANCE, name))
        names.add(name)
        _check_source(entry, name)
        if not isinstance(entry["codex_key_added"], bool):
            raise CopyError("%s's codex_key_added must be true or false" % name)
    return data


def is_sha(text):
    return isinstance(text, str) and bool(_SHA.match(text))


def _check_source(entry, what):
    for key in ("repository", "path"):
        if not isinstance(entry[key], str) or not entry[key]:
            raise CopyError("%s's %s must be text" % (what, key))
    if not is_sha(entry["commit"]):
        raise CopyError("%s's commit %r isn't a full lowercase SHA" % (what, entry["commit"]))


def source_of(repository, upstream=None):
    """Where to fetch a repository from: the --upstream override, or GitHub."""
    return upstream or "https://github.com/%s" % repository


def add_arguments(parser):
    parser.add_argument("--copies", default=COPIES, help="the skill-copies directory (default: this one)")
    parser.add_argument(
        "--upstream", help="a local repository or URL standing in for upstream (default: GitHub); suites pass one"
    )
