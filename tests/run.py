#!/usr/bin/env python3
"""This repository's checks and suites, as CI runs them (docs/agents/build.md).

  stored-form      fail on any stored path that has a dot segment or a loaded name
  release-check    compare a PR's base and head trees, one line per rule
  copies           fail unless the skill copies, their provenance and the relied-on list agree
  py39             confirm this interpreter is Python 3.9 and every script parses as 3.9
  exact-comparison render version 1 into the tally sample repository and compare it exactly
  suites           run the suites: --job linux, --job macos, --all, or suites by name;
                   --shard K/N runs only shard K's units
  shard-check      fail unless the shards' reports together ran every unit exactly once
"""

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITES_DIR = os.path.join(REPO, "tests", "suites")
sys.path.insert(0, os.path.join(REPO, "generator", "govern-repository", "scripts"))
sys.path.insert(0, SUITES_DIR)
sys.path.insert(0, os.path.join(REPO, "skill-copies", "scripts"))

from govlib import storedform  # noqa: E402

# The four top-level areas (#44 §2). Everything stored in them is in stored form.
AREAS = ("generator", "skill-copies", "machine", "tests")

# Each suite, its module under tests/suites/, and the CI job §11 of #44 puts it in. The macOS
# job also runs every Linux suite under Python 3.9, as the 3.9 compatibility check.
SUITES = (
    ("stored-form", "test_stored_form", "linux"),
    ("output-redaction", "test_output_redaction", "linux"),
    ("store", "test_store", "linux"),
    ("render", "test_render", "linux"),
    ("compare", "test_compare", "linux"),
    ("materialized-version", "test_materialized_version", "linux"),
    ("record", "test_record", "linux"),
    ("parser-fixtures", "test_parser_fixtures", "linux"),
    ("gate", "test_gate", "linux"),
    ("merge-watch", "test_merge_watch", "linux"),
    ("release-check", "test_release_check", "linux"),
    ("skill-copies", "test_skill_copies", "linux"),
    ("suite-runner", "test_suite_runner", "linux"),
    ("wait-on-pr", "test_wait_on_pr", "linux"),
    ("standins", "test_standins", "macos"),
    ("owner", "test_owner", "macos"),
    ("live-runner", "test_live_runner", "macos"),
    ("generator-core", "test_generator_core", "macos"),
    ("scenario-runner", "test_scenario_runner", "macos"),
    ("machine-install", "test_machine_install", "macos"),
    ("machine-check", "test_machine_check", "macos"),
    ("machine-list", "test_machine_list", "macos"),
    ("machine-wizard", "test_machine_wizard", "macos"),
)

# The scheduling unit is a suite module's test class, each run in its own child process.
# A class named here is split instead into that many units, its sorted test methods dealt
# round-robin; each unit's id is the class's id plus "[k/n]".
CHUNKS = {
    "test_generator_core.SeamA": 4,
    "test_owner.SeamD": 2,
    "test_owner.VersionTwoPermissions": 4,
}

# Measured seconds per unit, from the macOS shards' per-unit summaries: the shard plan's
# balance and every run's longest-first order. A sharded run fails unless its keys are
# exactly the selected units.
DURATIONS = os.path.join(REPO, "tests", "unit_durations.json")


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


def cmd_copies(args):
    """The copies check (#44 §10): names, provenance and the relied-on list agree, and each user-invoked copy is user-only.

    All at one upstream commit; user-only means Codex's key reads false (`copylib.codex_policy`).

    The role files' skill lists, the third side, join #41's materialized-version checks.
    """
    import copylib

    root = os.path.join(args.repo, "skill-copies")
    prefix = "skill-copies/%s/" % copylib.SKILLS
    on_disk = sorted(set(path[len(prefix):].split("/")[0] for path in tracked(args.repo, prefix)))
    try:
        relied_on = copylib.relied_on(os.path.join(args.repo, "generator", "govern-repository", "store"))
        provenance = copylib.load_provenance(root)
    except copylib.CopyError as error:
        print("FAIL copies: %s" % error)
        return 1
    listed = sorted(entry["name"] for entry in provenance["copies"])
    failures = []
    for label, names in (("in %s" % prefix, on_disk), ("in %s" % copylib.PROVENANCE, listed)):
        extra = sorted(set(names) - set(relied_on))
        missing = sorted(set(relied_on) - set(names))
        if extra:
            failures.append("%s but not on the relied-on list: %s" % (label, ", ".join(extra)))
        if missing:
            failures.append("on the relied-on list but not %s: %s" % (label, ", ".join(missing)))
    for name in on_disk:
        try:
            files = copylib.copy_files(os.path.join(root, copylib.SKILLS, name))
        except copylib.CopyError as error:
            failures.append("%s can't be read: %s" % (name, error))
            continue
        if not copylib.user_invoked(files.get("SKILL.md", ("", b""))[1]):
            continue
        codex = files.get(copylib.CODEX_FILE)
        reading = copylib.codex_policy(codex[1]) if codex else "absent"
        if reading != "false":
            failures.append("%s is user-invoked, but its %s reads as %s, not user-only" % (name, copylib.CODEX_FILE, reading))
    commits = sorted(set(entry["commit"] for entry in [provenance["license"]] + provenance["copies"]))
    if len(commits) > 1:
        failures.append("the copies and the license must come from one upstream commit, not %s" % ", ".join(commits))
    for failure in failures:
        print("FAIL copies: %s" % failure)
    if failures:
        return 1
    print(
        "PASS copies: %d copies at %s match the relied-on list and %s, the license not counted,"
        " and every user-invoked copy is user-only in Codex"
        % (len(on_disk), commits[0][:12], copylib.PROVENANCE)
    )
    return 0


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


def cmd_suite_child(args):
    """Internal worker: report counts separately from arbitrary unittest output."""
    suite = unittest.TestLoader().loadTestsFromNames(args.names)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    with open(args.result, "w") as handle:
        json.dump({"tests": result.testsRun, "passed": result.wasSuccessful()}, handle)
    return 0 if result.wasSuccessful() else 1


def flatten(tests):
    for test in tests:
        if isinstance(test, unittest.TestSuite):
            for inner in flatten(test):
                yield inner
        else:
            yield test


def cmd_list_child(args):
    """Internal worker: a suite module's test classes by attribute name, with their test methods.

    The classes must cover the module's own loading exactly once, an imported class included.
    """
    import importlib

    loader = unittest.TestLoader()
    module = importlib.import_module(args.module)
    classes = {}
    for attribute in sorted(dir(module)):
        value = getattr(module, attribute)
        if isinstance(value, type) and issubclass(value, unittest.TestCase):
            methods = list(loader.getTestCaseNames(value))
            if methods:
                classes[attribute] = methods
    whole = sorted(test.id() for test in flatten(loader.loadTestsFromModule(module)))
    covered = sorted(test.id() for attribute in classes
                     for test in flatten(loader.loadTestsFromTestCase(getattr(module, attribute))))
    if whole != covered:
        print("%s: its test classes do not cover its tests exactly once" % args.module)
        return 1
    with open(args.result, "w") as handle:
        json.dump(classes, handle)
    return 0


def child(arguments):
    """Run this file as an internal worker; return its exit code, output and JSON result."""
    output, result = b"", None
    try:
        with tempfile.TemporaryDirectory(prefix="suite-result-") as directory:
            result_path = os.path.join(directory, "result.json")
            process = subprocess.run(
                [sys.executable, "-u", os.path.abspath(__file__), arguments[0], result_path] + arguments[1:],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            output = process.stdout
            if process.returncode:
                output += ("\nworker exit code: %d\n" % process.returncode).encode()
            with open(result_path) as handle:
                result = json.load(handle)
        return process.returncode, output, result
    except (OSError, ValueError) as error:
        return None, output + ("\nworker failed: %s\n" % error).encode("utf-8", "replace"), result


def discover(suite):
    """A suite's units as (unit id, suite name, test names), or the whole module when listing fails."""
    name, module, _ = suite
    code, output, classes = child(["_list", module])
    if code != 0 or not isinstance(classes, dict):
        return [(module, name, [module])], output
    units = []
    for attribute, methods in sorted(classes.items()):
        unit = "%s.%s" % (module, attribute)
        count = CHUNKS.get(unit, 1)
        if count == 1:
            units.append((unit, name, [unit]))
            continue
        ordered = sorted(methods)
        for index in range(count):
            units.append(("%s[%d/%d]" % (unit, index + 1, count), name,
                          ["%s.%s" % (unit, method) for method in ordered[index::count]]))
    return units, b""


def run_unit(unit):
    unit_id, name, tests = unit
    started = time.monotonic()
    code, output, result = child(["_suite"] + tests)
    passed, count = False, None
    try:
        count = result["tests"]
        passed = result["passed"] and code == 0
    except (TypeError, KeyError) as error:
        output += ("\nworker failed: %s\n" % error).encode("utf-8", "replace")
    return unit_id, passed, count, time.monotonic() - started, output


def load_durations(path=DURATIONS):
    try:
        with open(path) as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}


def plan_shards(units, durations, count):
    """Deal units, longest measured first, each to the lightest shard; ties by id and index."""
    loads = [0.0] * count
    shards = [[] for _ in range(count)]
    for unit in sorted(units, key=lambda unit: (-durations[unit], unit)):
        index = loads.index(min(loads))
        shards[index].append(unit)
        loads[index] += durations[unit]
    return shards


def plan_problems(units, durations, shards):
    """Every way a shard plan fails to run each selected unit exactly once."""
    problems = ["%s has no measured duration in tests/unit_durations.json" % unit
                for unit in sorted(units) if unit not in durations]
    problems += ["%s is measured but no longer a unit" % unit
                 for unit in sorted(durations) if unit not in units]
    owners = {}
    for index, shard in enumerate(shards):
        for unit in shard:
            owners.setdefault(unit, []).append(index + 1)
    problems += ["%s is planned for no shard" % unit for unit in sorted(units) if unit not in owners]
    problems += ["%s is planned for shards %s" % (unit, ", ".join(str(i) for i in owner))
                 for unit, owner in sorted(owners.items()) if len(owner) > 1]
    return problems


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
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        listed = list(pool.map(discover, chosen))
    units = [unit for found, _ in listed for unit in found]
    by_id = dict((unit[0], unit) for unit in units)
    durations = load_durations()
    selected = set(by_id)
    shard_note = ""
    if args.shard:
        index, count = args.shard
        modules = set(module for _, module, _ in chosen)
        measured = dict((unit, seconds) for unit, seconds in durations.items()
                        if unit.split(".", 1)[0] in modules)
        known = dict((unit, measured.get(unit, 0.0)) for unit in by_id)
        shards = plan_shards(list(by_id), known, count)
        problems = plan_problems(selected, measured, shards)
        for _, output in listed:
            if output:
                print(output.decode("utf-8", "replace"), end="")
        if problems:
            for problem in problems:
                print("FAIL shard plan: %s" % problem)
            return 1
        selected = set(shards[index - 1])
        shard_note = ", shard %d/%d" % (index, count)
    # Longest measured first; an unmeasured unit is estimated as the longest.
    order = sorted(selected, key=lambda unit: (-durations.get(unit, float("inf")), unit))
    print("suites: %s (workers: %d, units: %d of %d%s)" % (
        ", ".join(name for name, _, _ in chosen), args.workers, len(order), len(by_id), shard_note), flush=True)
    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_unit, by_id[unit]) for unit in order]
        for future in as_completed(futures):
            unit, passed, count, duration, output = future.result()
            print("=== %s ===" % unit)
            print(output.decode("utf-8", "replace"), end="", flush=True)
            results[unit] = passed, count, duration
    for unit in order:
        passed, count, duration = results[unit]
        print("unit %s %s: %s tests, %.3fs" % (
            "PASS" if passed else "FAIL", unit, count if count is not None else "unknown", duration))
    for name, _, _ in chosen:
        mine = [results[unit] for unit in order if by_id[unit][1] == name]
        if not mine:
            continue
        counts = [result[1] for result in mine]
        print("%s %s: %s tests, %.3fs" % (
            "PASS" if all(result[0] for result in mine) else "FAIL", name,
            sum(counts) if None not in counts else "unknown", sum(result[2] for result in mine)))
    passed = all(result[0] for result in results.values())
    incomplete = any(result[1] is None for result in results.values())
    print("%s total: %d tests%s, %.3fs wall" % (
        "PASS" if passed else "FAIL", sum(result[1] or 0 for result in results.values()),
        " (incomplete)" if incomplete else "", time.monotonic() - started))
    if args.report:
        with open(args.report, "w") as handle:
            json.dump({
                "shard": list(args.shard) if args.shard else [1, 1],
                "units": sorted(by_id),
                "ran": sorted(results),
                "passed": passed,
                "durations": dict((unit, round(results[unit][2], 1)) for unit in sorted(results)),
            }, handle, sort_keys=True)
    return 0 if passed else 1


def cmd_shard_check(args):
    """Fail unless the shards' reports agree on the units and together run each exactly once."""
    failures = []
    reports = []
    for text in args.reports:
        try:
            report = json.loads(text)
            index, count = report["shard"]
            reports.append((int(index), int(count), list(report["units"]), list(report["ran"]),
                            report["passed"] is True))
        except (ValueError, KeyError, TypeError) as error:
            failures.append("a report does not read: %s" % error)
    counts = sorted(set(report[1] for report in reports))
    if len(counts) > 1:
        failures.append("the reports disagree on the shard count: %s" % ", ".join(str(c) for c in counts))
    count = counts[-1] if counts else 0
    label = dict((report[0], "%d/%d" % (report[0], report[1])) for report in reports)
    seen = [report[0] for report in reports]
    for index in range(1, count + 1):
        if seen.count(index) == 0:
            failures.append("shard %d/%d reported nothing" % (index, count))
        elif seen.count(index) > 1:
            failures.append("shard %d/%d reported more than once" % (index, count))
    units = reports[0][2] if reports else []
    owners = {}
    for index, _, planned, ran, passed in reports:
        if planned != units:
            failures.append("shard %s planned different units from shard %s" % (label[index], label[reports[0][0]]))
        if not passed:
            failures.append("shard %s did not pass" % label[index])
        for unit in ran:
            owners.setdefault(unit, []).append(label[index])
    for unit in units:
        owner = owners.get(unit, [])
        if not owner:
            failures.append("%s is run by no shard" % unit)
        elif len(owner) > 1:
            failures.append("%s is run by shards %s" % (unit, " and ".join(owner)))
    failures += ["%s is run but planned by no shard" % unit for unit in sorted(owners) if unit not in units]
    for failure in failures:
        print("FAIL shard-check: %s" % failure)
    if failures or not reports:
        if not reports:
            print("FAIL shard-check: no reports")
        return 1
    print("PASS shard-check: %d units, each run by exactly one of %d shards" % (len(units), count))
    return 0


def shard(value):
    try:
        index, count = (int(part) for part in value.split("/"))
    except ValueError:
        raise argparse.ArgumentTypeError("shard must be K/N")
    if not 1 <= index <= count:
        raise argparse.ArgumentTypeError("shard must be K/N with 1 <= K <= N")
    return index, count


def positive_workers(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("workers must be at least 1")
    return number


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

    copies = commands.add_parser("copies", help="check the skill copies against the relied-on list")
    copies.add_argument("--repo", default=REPO)
    copies.set_defaults(run=cmd_copies)

    py39 = commands.add_parser("py39", help="check Python 3.9 and /bin/bash compatibility")
    py39.add_argument("--repo", default=REPO)
    py39.set_defaults(run=cmd_py39)

    exact = commands.add_parser("exact-comparison", help="render version 1 into tally and compare it exactly")
    exact.set_defaults(run=cmd_exact_comparison)

    suites = commands.add_parser("suites", help="run suites")
    suites.add_argument("names", nargs="*")
    suites.add_argument("--workers", type=positive_workers, default=os.cpu_count() or 1,
                        help="concurrent suites (default: CPU count); 1 runs serially")
    group = suites.add_mutually_exclusive_group()
    group.add_argument("--job", choices=("linux", "macos"))
    group.add_argument("--all", action="store_true")
    suites.add_argument("--shard", type=shard, help="run only shard K of N, planned by measured duration")
    suites.add_argument("--report", help="write the units planned and run, as JSON, for shard-check")
    suites.set_defaults(run=cmd_suites)
    check = commands.add_parser("shard-check", help="check the shards' reports ran each unit exactly once")
    check.add_argument("reports", nargs="*", help="each shard's report, as JSON text")
    check.set_defaults(run=cmd_shard_check)
    worker = commands.add_parser("_suite", help=argparse.SUPPRESS)
    worker.add_argument("result")
    worker.add_argument("names", nargs="+")
    worker.set_defaults(run=cmd_suite_child)
    lister = commands.add_parser("_list", help=argparse.SUPPRESS)
    lister.add_argument("result")
    lister.add_argument("module")
    lister.set_defaults(run=cmd_list_child)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
