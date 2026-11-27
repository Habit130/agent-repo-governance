"""The target repository's checkout, read without changing it: its top level, `origin`, record and tracked files."""

import os
import stat
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
    return os.path.realpath(os.fsdecode(out).removesuffix("\n")) if out else None


def repository(root):
    """The owner/name `origin` names on GitHub; GovernError when it names none."""
    return compare.repository_from_origin(root)


def local_default_branch(root):
    """The branch `origin/HEAD` names in the checkout, or None."""
    try:
        return compare.default_branch_from_origin(root)
    except GovernError:
        return None


def _entries(data):
    for row in (data or b"").split(b"\0"):
        if row:
            fields, path = row.split(b"\t", 1)
            yield os.fsdecode(path), fields.split()


class CommittedFiles:
    """Pin one HEAD and index inventory. Only return bytes from a matching raw Git blob."""

    def __init__(self, root):
        self.root = root
        head = _git(root, "--no-replace-objects", "rev-parse", "--verify", "HEAD^{commit}")
        self.head = head.strip().decode("ascii") if head else None
        index = _git(root, "ls-files", "--stage", "-z")
        if index is None:
            raise GovernError("the tracked file list could not be read")
        self.index = {path: mode in (b"100644", b"100755") and stage == b"0"
                      for path, (mode, _, stage) in _entries(index)}
        tree = _git(root, "--no-replace-objects", "ls-tree", "-rz", self.head) if self.head else None
        if self.head and tree is None:
            raise GovernError("the committed file list could not be read")
        self.blobs = {path: oid if mode in (b"100644", b"100755") and kind == b"blob" else None
                      for path, (mode, kind, oid) in _entries(tree)}

    def present(self, path):
        return path in self.index or path in self.blobs or os.path.lexists(os.path.join(self.root, path))

    def read(self, path):
        if not self.index.get(path) or not self.blobs.get(path):
            return None
        parts = path.split("/")
        if any(part in ("", ".", "..") for part in parts):
            return None
        # Hold directory descriptors until the next component is open. A renamed or
        # substituted parent cannot redirect the read through a link.
        directory_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY
        try:
            directory = os.open(self.root, directory_flags)
            try:
                for part in parts[:-1]:
                    child = os.open(part, directory_flags, dir_fd=directory)
                    os.close(directory)
                    directory = child
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            finally:
                os.close(directory)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    return None
                blob = _git(self.root, "--no-replace-objects", "cat-file", "blob", self.blobs[path])
                if blob is None:
                    return None
                offset = 0
                while True:
                    chunk = os.read(fd, 65536)
                    if not chunk:
                        return blob if offset == len(blob) else None
                    if not blob.startswith(chunk, offset):
                        return None
                    offset += len(chunk)
            finally:
                os.close(fd)
        except OSError:
            return None


def record_facts(data):
    """The record's facts: whether it is there, whether it parses, and what it holds."""
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


def read_record(files):
    data = files.read(RECORD_PATH)
    if data is None and files.present(RECORD_PATH):
        raise GovernError(RECORD_PATH)
    return record_facts(data)
