"""Exact comparison (#44 §4, ADR 0015): a worktree's fixed content against a version's templates.

It checks the content and mode of every fixed file, of every fixed part between its markers,
and of the record up to its `confirmed:` key, and names each difference. The record's
confirmed values are the repository's own, and skeletons become repository-owned content, so
neither is compared.
"""

import os
import re
import subprocess

from govlib import GovernError, render, storedform

NOT_COMPARED = {"skeleton": "skeleton: repository-owned content"}

_GITHUB_REMOTE = re.compile(r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?/?$")


def _git(worktree, *args):
    try:
        result = subprocess.run(
            ["git", "-C", worktree] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def repository_from_origin(worktree):
    """The owner/name a worktree's `origin` names on GitHub."""
    url = _git(worktree, "remote", "get-url", "origin")
    match = _GITHUB_REMOTE.match(url or "")
    if not match:
        raise GovernError("the worktree's origin %r isn't a GitHub repository; pass --repository" % (url,))
    return match.group(1)


def default_branch_from_origin(worktree):
    """The branch `origin/HEAD` points at in a worktree."""
    head = _git(worktree, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    prefix = "refs/remotes/origin/"
    if not head or not head.startswith(prefix):
        raise GovernError("the worktree doesn't know origin's default branch; pass --default-branch")
    return head[len(prefix):]


def _first_difference(expected, found):
    """The 1-based line, counted in found, where found first departs from expected."""
    limit = min(len(expected), len(found))
    index = 0
    while index < limit and expected[index] == found[index]:
        index += 1
    return found.count(b"\n", 0, index) + 1


def compare(store, worktree, repository, default_branch, version=None, allow_unreleased=False):
    """Compare a worktree with a version; return the facts, differences sorted by path."""
    version = render.select_version(store, version, allow_unreleased)
    manifest = store.manifest(version)
    values = render.check_values(version, repository, default_branch)
    root = os.path.realpath(worktree)
    if not os.path.isdir(root):
        raise GovernError("worktree %r is not a directory" % worktree)

    differences, checked, not_compared = [], [], {}
    for entry in manifest["templates"]:
        path, kind = entry["path"], entry["class"]
        if kind in NOT_COMPARED:
            not_compared[path] = NOT_COMPARED[kind]
            continue
        checked.append(path)
        expected_text = render.template_text(store, version, entry, values)
        expected = expected_text.encode("utf-8")
        found_path = os.path.join(root, *path.split("/"))

        def differ(what, detail=None):
            difference = {"path": path, "class": kind, "kind": what}
            if detail:
                difference["detail"] = detail
            differences.append(difference)

        if os.path.islink(found_path) or (os.path.lexists(found_path) and not os.path.isfile(found_path)):
            differ("not a file", "a fixed file must be a regular file")
            continue
        if not os.path.exists(found_path):
            differ("missing")
            continue
        with open(found_path, "rb") as handle:
            found = handle.read()
        if kind == "record":
            expected = render.record_fixed_part(expected_text, path).encode("utf-8")
            try:
                found_fixed = render.record_fixed_part(found.decode("utf-8"), path).encode("utf-8")
            except UnicodeDecodeError:
                differ("structure", "the record is not UTF-8")
                continue
            except render.MarkerError as error:
                differ("structure", str(error))
                continue
            if found_fixed != expected:
                differ("content", "first difference at line %d" % _first_difference(expected, found_fixed))
        elif kind == "fixed part":
            start, end = render.find_block(expected_text, path)
            expected = expected_text[start:end].encode("utf-8")
            try:
                found_text = found.decode("utf-8")
                found_start, found_end = render.find_block(found_text, path)
            except UnicodeDecodeError:
                differ("markers", "the file is not UTF-8, so its markers can't be read")
                continue
            except render.MarkerError as error:
                differ("markers", str(error))
                continue
            offset = len(found_text[:found_start].encode("utf-8"))
            found_block = found_text[found_start:found_end].encode("utf-8")
            if found_block != expected:
                line = found[:offset].count(b"\n") + _first_difference(expected, found_block)
                differ("content", "first difference at line %d" % line)
        elif found != expected:
            differ("content", "first difference at line %d" % _first_difference(expected, found))
        actual_mode = storedform.mode_of(found_path)
        if actual_mode != entry["mode"]:
            differ("mode", "expected %s, found %s" % (entry["mode"], actual_mode))

    differences.sort(key=lambda difference: difference["path"])
    return {
        "version": version,
        "released": store.is_released(version),
        "worktree": root,
        "repository": repository,
        "default_branch": default_branch,
        "checked": checked,
        "not_compared": not_compared,
        "differences": differences,
    }
