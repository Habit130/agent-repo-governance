#!/usr/bin/env python3
"""This repository's checks and suites, as CI runs them (docs/agents/build.md).

  stored-form      fail on any stored path that has a dot segment or a loaded name
  release-check    compare a PR's base and head trees, one line per rule
  py39             confirm this interpreter is Python 3.9 and every script parses as 3.9
  exact-comparison render version 1 into the tally sample repository and compare it exactly
  suites           run the suites: --job linux, --job macos, --all, or suites by name
"""

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITES_DIR = os.path.join(REPO, "tests", "suites")
sys.path.insert(0, os.path.join(REPO, "generator", "govern-repository", "scripts"))
sys.path.insert(0, SUITES_DIR)

from govlib import storedform  # noqa: E402

# The four top-level areas (#44 §2). Everything stored in them is in stored form.
AREAS = ("generator", "skill-copies", "machine", "tests")

# Each suite, its module under tests/suites/, and the CI job §11 of #44 puts it in. The macOS
# job also runs every Linux suite under Python 3.9, as the 3.9 compatibility check.
SUITES = (
    ("stored-form", "test_stored_form", "linux"),
    ("store", "test_store", "linux"),
    ("render", "test_render", "linux"),
    ("compare", "test_compare", "linux"),
    ("materialized-version", "test_materialized_version", "linux"),
    ("record", "test_record", "linux"),
    ("parser-fixtures", "test_parser_fixtures", "linux"),
    ("release-check", "test_release_check", "linux"),
    ("standins", "test_standins", "macos"),
)


def tracked(repo, *pathspecs):
    out = subprocess.run(
        ["git", "-C", repo, "ls-files", "-z", "--"] + list(pathspecs),
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    return [path for path in out.decode("utf-8").split("\0") if path]


def cmd_stored_form(args):
    paths = tracked(args.repo, *AREAS)
    failures = [(path, problem) for path in paths for problem in storedform.problems(path)]
    for path, problem in failures:
        print("FAIL stored form: %s: %s" % (path, problem))
    if failures:
        print("FAIL stored form: %d of %d stored paths could load or fail to decode" % (len(failures), len(paths)))
        return 1
    print("PASS stored form: %d stored paths, none with a dot segment or a loaded name" % len(paths))
    return 0


def cmd_release_check(args):
    import release_check

    passed, lines = release_check.check(args.repo, args.base, args.head)
    for line in lines:
        print(line)
    return 0 if passed else 1


SHELL_SHEBANGS = (b"#!/bin/bash", b"#!/bin/sh", b"#!/usr/bin/env bash", b"#!/usr/bin/env sh")


def is_shell_entry(path):
    with open(path, "rb") as handle:
        first = handle.readline()
    return first.startswith(SHELL_SHEBANGS)


def cmd_py39(args):
    version = sys.version_info
    failures = []
    if version[:2] != (3, 9):
        failures.append("this interpreter is Python %d.%d, not 3.9" % (version[0], version[1]))
    sources = [p for p in tracked(args.repo, *AREAS) if not p.startswith("tests/fixtures/")]
    python_files = [p for p in sources if p.endswith(".py")]
    shell_entries = [p for p in sources if not p.endswith(".py") and is_shell_entry(os.path.join(args.repo, p))]
    for path in python_files:
        with open(os.path.join(args.repo, path), "rb") as handle:
            source = handle.read()
        try:
            ast.parse(source, filename=path, feature_version=(3, 9))
        except SyntaxError as error:
            failures.append("%s:%s does not parse as Python 3.9: %s" % (path, error.lineno, error.msg))
    for path in shell_entries:
        result = subprocess.run(
            ["/bin/bash", "-n", os.path.join(args.repo, path)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        if result.returncode != 0:
            failures.append("%s fails /bin/bash -n: %s" % (path, result.stdout.decode("utf-8", "replace").strip()))
    bash = subprocess.run(["/bin/bash", "--version"], stdout=subprocess.PIPE).stdout.decode("utf-8").splitlines()[0]
    print("python: %s at %s" % (sys.version.split()[0], sys.executable))
    print("bash: %s" % bash)
    for failure in failures:
        print("FAIL py39: %s" % failure)
    if failures:
        return 1
    print(
        "PASS py39: %d Python files parse as 3.9 and %d shell entries pass /bin/bash -n"
        % (len(python_files), len(shell_entries))
    )
    return 0


def cmd_exact_comparison(args):
    import materialized

    root = os.path.realpath(tempfile.mkdtemp(prefix="exact-comparison-"))
    try:
        worktree, rendered = materialized.render_version_one(root)
        code, facts = materialized.compare_version_one(worktree)
    finally:
        shutil.rmtree(root, True)
    facts["rendered"] = rendered["written"]
    print(json.dumps(facts, indent=2, sort_keys=True))
    return code


def cmd_suites(args):
    names = [name for name, _, _ in SUITES]
    if args.all:
        chosen = list(SUITES)
    elif args.job:
        chosen = [suite for suite in SUITES if suite[2] == args.job]
    elif args.names:
        unknown = [name for name in args.names if name not in names]
        if unknown:
            print("unknown suites: %s (known: %s)" % (", ".join(unknown), ", ".join(names)))
            return 2
        chosen = [suite for suite in SUITES if suite[0] in args.names]
    else:
        print("name suites, or pass --job linux, --job macos or --all")
        return 2
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name, module, _ in chosen:
        suite.addTests(loader.loadTestsFromName(module))
    print("suites: %s" % ", ".join(name for name, _, _ in chosen))
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    return 0 if result.wasSuccessful() else 1


def build_parser():
    parser = argparse.ArgumentParser(prog="tests/run.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True

    stored = commands.add_parser("stored-form", help="check every stored path")
    stored.add_argument("--repo", default=REPO)
    stored.set_defaults(run=cmd_stored_form)

    release = commands.add_parser("release-check", help="compare a PR's base and head trees")
    release.add_argument("--repo", default=REPO)
    release.add_argument("--base", required=True, help="the PR's base: HEAD^1 of the merge commit in CI")
    release.add_argument("--head", required=True, help="the PR's head, or its merge commit in CI")
    release.set_defaults(run=cmd_release_check)

    py39 = commands.add_parser("py39", help="check Python 3.9 and /bin/bash compatibility")
    py39.add_argument("--repo", default=REPO)
    py39.set_defaults(run=cmd_py39)

    exact = commands.add_parser("exact-comparison", help="render version 1 into tally and compare it exactly")
    exact.set_defaults(run=cmd_exact_comparison)

    suites = commands.add_parser("suites", help="run suites")
    suites.add_argument("names", nargs="*")
    group = suites.add_mutually_exclusive_group()
    group.add_argument("--job", choices=("linux", "macos"))
    group.add_argument("--all", action="store_true")
    suites.set_defaults(run=cmd_suites)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
