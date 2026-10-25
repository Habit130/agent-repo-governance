"""Shared helpers for the suites: paths, isolated git, temporary trees and the CLI entries."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(REPO, "generator", "govern-repository", "scripts")
GOVERN = os.path.join(SCRIPTS, "govern.py")
REAL_STORE = os.path.join(REPO, "generator", "govern-repository", "store")
RUN = os.path.join(REPO, "tests", "run.py")
FIXTURES = os.path.join(REPO, "tests", "fixtures")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def isolated_env(extra=None):
    """The environment for every subprocess: no user or system git config, a fixed identity."""
    env = dict(os.environ)
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Suite",
            "GIT_AUTHOR_EMAIL": "suite@example.invalid",
            "GIT_COMMITTER_NAME": "Suite",
            "GIT_COMMITTER_EMAIL": "suite@example.invalid",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if extra:
        env.update(extra)
    return env


def git(cwd, *args, env=None):
    result = subprocess.run(
        ["git", "-C", cwd] + list(args),
        env=env or isolated_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if result.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), result.stderr))
    return result.stdout


def init_repo(path):
    os.makedirs(path, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    return path


def write_tree(root, files):
    """Write {path: content} or {path: {"content": ..., "mode": "100755"}} under root."""
    for path, spec in files.items():
        if isinstance(spec, dict):
            content, mode = spec["content"], spec.get("mode", "100644")
        else:
            content, mode = spec, "100644"
        full = os.path.join(root, *path.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(content.encode("utf-8"))
        os.chmod(full, 0o755 if mode == "100755" else 0o644)


def commit_tree(repo, files, message):
    """Replace the repository's whole tree with files and commit it; return the commit SHA."""
    for entry in os.listdir(repo):
        if entry == ".git":
            continue
        full = os.path.join(repo, entry)
        if os.path.isdir(full) and not os.path.islink(full):
            shutil.rmtree(full)
        else:
            os.remove(full)
    write_tree(repo, files)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


def run_cli(script, args, env=None, cwd=None):
    """Run a CLI entry with this interpreter; return (exit code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, script] + list(args),
        env=env or isolated_env(),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return result.returncode, result.stdout, result.stderr


def govern(args, env=None, cwd=None):
    """Run the generator's entry; return (exit code, parsed JSON)."""
    code, out, err = run_cli(GOVERN, args, env=env, cwd=cwd)
    try:
        facts = json.loads(out)
    except ValueError:
        raise AssertionError("govern.py %s printed no JSON (exit %d): %s %s" % (args, code, out, err))
    return code, facts


def file_mode(path):
    return "100755" if os.stat(path).st_mode & 0o111 else "100644"


def read_text(path):
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8")


class TempDirCase(unittest.TestCase):
    """A test case with a fresh temporary directory, removed afterwards."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="suite-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def path(self, *parts):
        return os.path.join(self.tmp, *parts)
