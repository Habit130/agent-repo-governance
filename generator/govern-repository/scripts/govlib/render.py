"""Rendering (#44 §4): a version's templates, the repository's values and confirmed values become files.

The only placeholders are `@@version@@`, `@@repository@@` and `@@default_branch@@`; an
unknown or leftover token fails the render. Confirmed values go only into the record's
`confirmed` part. A render that refuses writes nothing.

Per class, into a temporary directory or a target worktree's top level:

- fixed and record: written whole;
- fixed part: written whole when the target is absent; otherwise its one well-formed marker
  block is replaced and the rest of the file kept, and any other target is refused;
- skeleton: written only when the target is absent, since what is there is repository-owned.
"""

import os
import re

from govlib import GovernError, storedform
from govlib.store import StoreError

TOKEN = re.compile(r"@@([A-Za-z0-9_]*)@@")
# What a malformed token leaves behind: `@@` against a name character. A bare `@@`, as in a
# diff hunk header, is text.
LEFTOVER = re.compile(r"@@[A-Za-z0-9_]|[A-Za-z0-9_]@@")
NAMES = ("version", "repository", "default_branch")
FLOORS = ("medium", "high")

BEGIN = re.compile(r"^<!-- governance:begin v[1-9][0-9]* -->$")
END = "<!-- governance:end -->"

_REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$")
_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")
_CONFIRMED_KEYS = {"sensitive_paths", "required_checks"}
_PATH_KEYS = {"pattern", "floor"}


class RenderError(GovernError):
    pass


class MarkerError(RenderError):
    pass


def select_version(store, version=None, allow_unreleased=False):
    """The version a run writes: the installed version, or one the run names.

    A version that isn't released is used only when the run passes allow_unreleased, which a
    test, scenario or live-check runner does for that run alone.
    """
    installed = store.installed_version()
    if version is None:
        if installed is None:
            raise RenderError("the template store at %s has no released version, so nothing renders" % store.root)
        return installed
    if version not in store.versions():
        raise StoreError("the template store has no version %d" % version)
    if not store.is_released(version) and not allow_unreleased:
        raise RenderError(
            "version %d is not released; only a test, scenario or live-check runner renders it, "
            "by asking with --allow-unreleased for that run" % version
        )
    return version


def check_values(version, repository, default_branch):
    if not isinstance(repository, str) or not _REPOSITORY.match(repository):
        raise RenderError("repository %r is not an owner/name pair" % (repository,))
    branch = default_branch
    if (
        not isinstance(branch, str)
        or not _BRANCH.match(branch)
        or branch.startswith(("-", "/", "."))
        or branch.endswith(("/", ".", ".lock"))
        or ".." in branch
        or "//" in branch
    ):
        raise RenderError("default branch %r is not a branch name" % (branch,))
    return {"version": str(version), "repository": repository, "default_branch": branch}


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def substitute(text, values, where):
    """Replace every known token; refuse an unknown or leftover one."""

    def replace(match):
        name = match.group(1)
        if name not in values:
            raise RenderError(
                "%s line %d has the unknown token %s; the only tokens are %s"
                % (where, _line_of(text, match.start()), match.group(0), ", ".join("@@%s@@" % n for n in NAMES))
            )
        return values[name]

    rendered = TOKEN.sub(replace, text)
    leftover = LEFTOVER.search(rendered)
    if leftover:
        raise RenderError("%s line %d has a leftover token after rendering" % (where, _line_of(rendered, leftover.start())))
    return rendered


def find_block(text, where):
    """The (start, end) offsets of a text's one well-formed marker block, end marker line included."""
    begins, ends = [], []
    offset = 0
    for line in text.splitlines(True):
        content = line.rstrip("\n")
        if BEGIN.match(content):
            begins.append((offset, offset + len(line)))
        elif content == END:
            ends.append((offset, offset + len(line)))
        offset += len(line)
    if len(begins) != 1 or len(ends) != 1:
        raise MarkerError(
            "%s has %d begin and %d end markers; a fixed part needs exactly one of each"
            % (where, len(begins), len(ends))
        )
    if begins[0][0] > ends[0][0]:
        raise MarkerError("%s has its end marker before its begin marker" % where)
    return begins[0][0], ends[0][1]


def _quoted(value):
    return '"%s"' % value.replace("\\", "\\\\").replace('"', '\\"')


def _text_value(value, what):
    if not isinstance(value, str) or not value or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise RenderError("%s %r must be non-empty text on one line" % (what, value))
    return value


def check_confirmed(confirmed):
    """Validate confirmed values: sensitive paths with floors, and required checks."""
    if not isinstance(confirmed, dict) or set(confirmed) != _CONFIRMED_KEYS:
        raise RenderError("confirmed values must hold exactly sensitive_paths and required_checks")
    paths = confirmed["sensitive_paths"]
    checks = confirmed["required_checks"]
    if not isinstance(paths, list) or not isinstance(checks, list):
        raise RenderError("confirmed sensitive_paths and required_checks must be lists")
    for entry in paths:
        if not isinstance(entry, dict) or set(entry) != _PATH_KEYS:
            raise RenderError("a confirmed sensitive path needs exactly a pattern and a floor: %r" % (entry,))
        _text_value(entry["pattern"], "sensitive path pattern")
        if entry["floor"] not in FLOORS:
            raise RenderError("sensitive path %s has floor %r; a floor is medium or high" % (entry["pattern"], entry["floor"]))
    for check in checks:
        _text_value(check, "required check")
    return confirmed


def confirmed_lines(confirmed):
    """The record's `confirmed` part below its key. An empty list is its key with no items."""
    lines = ["  sensitive_paths:"]
    for entry in confirmed["sensitive_paths"]:
        lines.append("    - pattern: %s" % _quoted(entry["pattern"]))
        lines.append("      floor: %s" % entry["floor"])
    lines.append("  required_checks:")
    for check in confirmed["required_checks"]:
        lines.append("    - %s" % _quoted(check))
    return "".join(line + "\n" for line in lines)


def record_fixed_part(text, where, template=False):
    """A record's fixed part: everything up to and including its one top-level `confirmed:` key.

    A record template ends at that key. A rendered record holds only its confirmed values
    below it: indented lines, blank lines and comments, so no top-level field after the key
    can redefine one of the fixed part's.
    """
    lines = text.splitlines(True)
    keys = [i for i, line in enumerate(lines) if line.rstrip("\n") == "confirmed:"]
    if len(keys) != 1:
        raise MarkerError("%s has %d top-level `confirmed:` keys; a record has exactly one" % (where, len(keys)))
    for number, line in enumerate(lines[keys[0] + 1:], keys[0] + 2):
        if not line.strip():
            continue
        if template:
            raise RenderError("%s must end with its one top-level `confirmed:` key" % where)
        if not line.startswith((" ", "#")):
            raise MarkerError(
                "%s line %d is top-level content after the `confirmed:` key, which holds only indented values"
                % (where, number)
            )
    return "".join(lines[: keys[0]]) + "confirmed:\n"


def fill_record(text, confirmed, where):
    """Insert confirmed values under the record template's final `confirmed:` key."""
    fixed = record_fixed_part(text, where, template=True)
    if confirmed is None:
        raise RenderError("%s is the record, and rendering it needs the record's confirmed values" % where)
    return fixed + confirmed_lines(confirmed)


def _read_template(store, version, path):
    with open(store.template_path(version, path), "rb") as handle:
        data = handle.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise RenderError("version %d's template for %s is not UTF-8" % (version, path))


def template_text(store, version, entry, values):
    """One template with its tokens substituted and its structure checked."""
    where = "version %d's template for %s" % (version, entry["path"])
    text = substitute(_read_template(store, version, entry["path"]), values, where)
    if entry["class"] == "fixed part":
        find_block(text, where)
    if entry["class"] == "record":
        record_fixed_part(text, where, template=True)
    return text


def rendered_template(store, version, entry, values, confirmed=None):
    """One template's rendered text, before it meets any target file."""
    text = template_text(store, version, entry, values)
    if entry["class"] == "record":
        text = fill_record(text, confirmed, "version %d's template for %s" % (version, entry["path"]))
    return text


def _existing(root, path):
    """A target file's bytes, or None when it is absent; refused unless it can be written safely."""
    full = storedform.check_target(root, path)
    if not os.path.exists(full):
        return None
    with open(full, "rb") as handle:
        return handle.read()


def render(store, dest, repository, default_branch, confirmed=None, version=None, allow_unreleased=False):
    """Render a version into dest; return the facts. A refusal writes nothing."""
    version = select_version(store, version, allow_unreleased)
    manifest = store.manifest(version)
    values = check_values(version, repository, default_branch)
    if confirmed is not None:
        check_confirmed(confirmed)
    root = storedform.check_destination(dest)

    plan, kept = [], []
    for entry in manifest["templates"]:
        text = rendered_template(store, version, entry, values, confirmed)
        current = _existing(root, entry["path"])
        if entry["class"] == "skeleton" and current is not None:
            kept.append(entry["path"])
            continue
        if entry["class"] == "fixed part" and current is not None:
            try:
                existing = current.decode("utf-8")
            except UnicodeDecodeError:
                raise RenderError("%s is not UTF-8, so its fixed part can't be found" % entry["path"])
            start, end = find_block(existing, entry["path"])
            block_start, block_end = find_block(text, entry["path"])
            text = existing[:start] + text[block_start:block_end] + existing[end:]
        plan.append((entry["path"], text.encode("utf-8"), entry["mode"]))

    for path, data, mode in plan:
        storedform.write_file(root, path, data, mode)
    return {
        "version": version,
        "released": store.is_released(version),
        "dest": root,
        "written": [path for path, _, _ in plan],
        "kept": kept,
        "confirmed_rendered": any(entry["class"] == "record" for entry in manifest["templates"]),
    }
