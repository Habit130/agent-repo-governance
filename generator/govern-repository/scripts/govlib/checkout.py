"""The target repository's checkout, read without changing it: its top level, `origin`, record and tracked files."""

import os
import subprocess

from govlib import GovernError, compare, record

RECORD_PATH = ".github/governance/record.yml"


def _git(root, *args):
    try:
        result = subprocess.run(
            ["git", "-C", root] + list(args), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def toplevel(worktree):
    """The checkout's top level, or None when the directory isn't inside a git checkout."""
    out = _git(worktree, "rev-parse", "--show-toplevel")
    return os.path.realpath(out.decode("utf-8").strip()) if out else None


def repository(root):
    """The owner/name `origin` names on GitHub; GovernError when it names none."""
    return compare.repository_from_origin(root)


def local_default_branch(root):
    """The branch `origin/HEAD` names in the checkout, or None."""
    try:
        return compare.default_branch_from_origin(root)
    except GovernError:
        return None


def tracked(root):
    """Every tracked path, sorted."""
    out = _git(root, "ls-files", "-z")
    return sorted(path for path in (out or b"").decode("utf-8", "replace").split("\0") if path)


def read(root, path):
    """A file's bytes in the checkout, or None when it is absent or not a regular file."""
    full = os.path.join(root, *path.split("/"))
    if os.path.islink(full) or not os.path.isfile(full):
        return None
    with open(full, "rb") as handle:
        return handle.read()


def read_record(root):
    """The record's facts: whether it is there, whether it parses, and what it holds."""
    data = read(root, RECORD_PATH)
    if data is None:
        return {"path": RECORD_PATH, "present": False}
    try:
        parsed = record.parse(data)
    except record.RecordError as error:
        return {"path": RECORD_PATH, "present": True, "parses": False, "error": str(error)}
    return {
        "path": RECORD_PATH,
        "present": True,
        "parses": True,
        "version": parsed["version"],
        "agent_account": parsed["agent_account"],
        "sensitive_paths": parsed["sensitive_paths"],
        "confirmed": parsed["confirmed"],
    }
