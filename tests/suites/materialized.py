"""Materialized version 1: the real store's version 1 rendered into the tally sample repository.

The materialized-version suite and `tests/run.py exact-comparison` both start here, and
#41's template tickets add their seam-3 checks against the worktree it builds.
"""

import json
import os

import support

TALLY = os.path.join(support.FIXTURES, "repositories", "tally")


def tally_fixture():
    with open(os.path.join(TALLY, "fixture.json")) as handle:
        return json.load(handle)


def tally_worktree(root):
    """A git worktree of tally before Initialize, with origin and its default branch known offline."""
    fixture = tally_fixture()
    worktree = support.init_repo(os.path.join(root, "tally"))
    code, facts = support.govern(["materialize", "--source", os.path.join(TALLY, "repo"), "--dest", worktree])
    if code != 0:
        raise AssertionError("materializing tally failed: %s" % facts)
    support.git(worktree, "add", "-A")
    support.git(worktree, "commit", "-q", "-m", "tally before Initialize")
    support.git(worktree, "remote", "add", "origin", "https://github.com/%s.git" % fixture["repository"])
    branch = fixture["default_branch"]
    support.git(worktree, "update-ref", "refs/remotes/origin/%s" % branch, "HEAD")
    support.git(worktree, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/%s" % branch)
    return worktree


def render_version_one(root):
    """Render version 1 from the real store into a fresh tally worktree; return (worktree, render facts)."""
    fixture = tally_fixture()
    worktree = tally_worktree(root)
    confirmed = os.path.join(root, "tally-confirmed.json")
    with open(confirmed, "w") as handle:
        json.dump(fixture["confirmed"], handle)
    code, facts = support.govern(
        [
            "render",
            "--store", support.REAL_STORE,
            "--version", "1",
            "--allow-unreleased",
            "--dest", worktree,
            "--repository", fixture["repository"],
            "--default-branch", fixture["default_branch"],
            "--confirmed", confirmed,
        ]
    )
    if code != 0:
        raise AssertionError("rendering version 1 into tally failed: %s" % facts)
    return worktree, facts


def compare_version_one(worktree):
    """Exact comparison of the worktree with version 1, as one command reading values from origin."""
    return support.govern(
        ["compare", "--store", support.REAL_STORE, "--version", "1", "--allow-unreleased", "--worktree", worktree]
    )
