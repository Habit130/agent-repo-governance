"""Stored form (#44 §3, ADR 0023): the reversible encoding that keeps stored files from loading.

A path segment starting with `.` is stored with `dot-` in its place, and a file whose name a
harness loads wherever it appears gets a `.stored` suffix. Materializing reverses both, and
only into a temporary directory or a target worktree's top level. Executable bits are kept
in storage and restored.
"""

import os
import subprocess
import tempfile

from govlib import GovernError

DOT = "dot-"
SUFFIX = ".stored"

# Names a harness loads wherever they appear. A harness that starts loading a new name is a
# miss, fixed by adding the name here. Matching ignores case, because macOS's default file
# system opens `claude.md` for `CLAUDE.md`.
LOADED_NAMES = (
    "AGENTS.md",
    "AGENTS.override.md",
    "CLAUDE.md",
    "CLAUDE.local.md",
    "opencode.json",
    "opencode.jsonc",
)
_LOADED = frozenset(name.lower() for name in LOADED_NAMES)

# Left by macOS's Finder in any directory; never stored content.
IGNORED_NAMES = frozenset([".DS_Store"])


class StoredFormError(GovernError):
    pass


def is_loaded_name(name):
    return name.lower() in _LOADED


def _segments(path, kind):
    if not path or path.startswith("/") or path.endswith("/"):
        raise StoredFormError("%s path %r is not a plain relative path" % (kind, path))
    segments = path.split("/")
    for segment in segments:
        if segment in ("", ".", ".."):
            raise StoredFormError("%s path %r is not a plain relative path" % (kind, path))
    return segments


def encode(real_path):
    """Return the stored form of a real, root-relative path, or refuse one that would decode wrongly."""
    segments = _segments(real_path, "real")
    stored = []
    for index, segment in enumerate(segments):
        if segment.startswith(DOT):
            raise StoredFormError(
                "real path %r has a segment starting with %r, which would decode as a dot segment"
                % (real_path, DOT)
            )
        if segment.endswith(SUFFIX):
            raise StoredFormError(
                "real path %r has a segment ending in %r, which would decode wrongly" % (real_path, SUFFIX)
            )
        last = index == len(segments) - 1
        if last and is_loaded_name(segment):
            segment += SUFFIX
        if segment.startswith("."):
            segment = DOT + segment[1:]
        stored.append(segment)
    return "/".join(stored)


def decode(stored_path):
    """Return the real path a stored path stands for, or refuse one that encode never produces."""
    segments = _segments(stored_path, "stored")
    real = []
    for index, segment in enumerate(segments):
        last = index == len(segments) - 1
        if segment.startswith("."):
            raise StoredFormError("stored path %r has a dot segment %r" % (stored_path, segment))
        if segment.endswith(SUFFIX):
            base = segment[: -len(SUFFIX)]
            if not last or not is_loaded_name(base):
                raise StoredFormError(
                    "stored path %r has %r, but only a loaded file name carries %r"
                    % (stored_path, segment, SUFFIX)
                )
            segment = base
        elif last and is_loaded_name(segment):
            raise StoredFormError("stored path %r has the loaded name %r" % (stored_path, segment))
        if segment.startswith(DOT):
            segment = "." + segment[len(DOT):]
            if segment in (".", ".."):
                raise StoredFormError("stored path %r decodes to %r" % (stored_path, segment))
        real.append(segment)
    return "/".join(real)


def problems(stored_path):
    """Why a stored path could load or fails to decode; empty when it is sound."""
    try:
        decode(stored_path)
    except StoredFormError as error:
        return [str(error)]
    return []


def mode_of(path):
    """Git's mode for a regular file: executable or not."""
    return "100755" if os.stat(path).st_mode & 0o111 else "100644"


def write_file(dest_root, real_path, data, mode):
    """Write one materialized file under dest_root with the given git mode."""
    full = os.path.join(dest_root, *real_path.split("/"))
    parent = os.path.dirname(full)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    if os.path.islink(full):
        os.remove(full)
    with open(full, "wb") as handle:
        handle.write(data)
    os.chmod(full, 0o755 if mode == "100755" else 0o644)
    return full


def stored_files(source_dir):
    """Every stored file under source_dir as (stored path, absolute path), sorted."""
    if not os.path.isdir(source_dir):
        raise StoredFormError("stored tree %r is not a directory" % source_dir)
    found = []
    for root, dirs, files in os.walk(source_dir):
        dirs.sort()
        for name in sorted(files):
            if name in IGNORED_NAMES:
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, source_dir).replace(os.sep, "/")
            if os.path.islink(full) or not os.path.isfile(full):
                raise StoredFormError("stored tree holds %r, which is not a regular file" % rel)
            found.append((rel, full))
    return found


def _git_toplevel(path):
    try:
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return os.path.realpath(result.stdout.strip())


def check_destination(dest):
    """Refuse any destination other than a temporary directory or a worktree's top level."""
    real = os.path.realpath(dest)
    temp = os.path.realpath(tempfile.gettempdir())
    if real == temp or real.startswith(temp + os.sep):
        return real
    if os.path.isdir(real) and _git_toplevel(real) == real:
        return real
    raise StoredFormError(
        "materializing writes only into a temporary directory or a target worktree's top level, "
        "and %r is neither" % dest
    )


def materialize(source_dir, dest):
    """Decode every stored file under source_dir into dest, restoring executable bits.

    Every path is decoded before anything is written, so a bad stored tree writes nothing.
    """
    root = check_destination(dest)
    plan = [(decode(rel), full) for rel, full in stored_files(source_dir)]
    written = []
    for real_path, full in plan:
        with open(full, "rb") as handle:
            data = handle.read()
        write_file(root, real_path, data, mode_of(full))
        written.append(real_path)
    return written
