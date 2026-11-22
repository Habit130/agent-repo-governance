"""The shared parser fixtures (#44 §5): each parser against its applicable fixtures.

`tests/fixtures/parsers/` holds the record fixtures under `record/`, the PR-body fixtures
under `pr-body/`, and `expected.json`. That file maps each fixture file to its expected
result, and adds the cases `git diff --check` would flag as inline texts. There is one test
per parser and fixture, named for both, so the verbose output lists each parser and each
fixture's result.

`record-v3/` and `expected-v3.json` hold the fixtures for confirmed review bots (#148),
which the machine parser and governed parsers from version 3 read.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

import parsers
import support
from govlib import store

FIXTURES = os.path.join(support.FIXTURES, "parsers")
DIRECTORIES = {"record": "record", "pr_body": "pr-body"}
V3_DIRECTORY = "record-v3"


def load_expected():
    with open(os.path.join(FIXTURES, "expected.json"), encoding="utf-8") as handle:
        return json.load(handle)


def cases(parser):
    """Every fixture as (kind, name, bytes, expected): the files, then the inline texts."""
    expected = load_expected()
    for kind, directory in sorted(DIRECTORIES.items()):
        for name, result in sorted(expected[kind].items()):
            with open(os.path.join(FIXTURES, directory, name), "rb") as handle:
                yield kind, name, handle.read(), result
        for name, case in sorted(expected[kind + "_texts"].items()):
            result = case["expected"]
            if not parser.supports(5):
                result = case.get("expected_before_v5", result)
            yield kind, name, case["text"].encode("utf-8"), result


def load_expected_v3():
    with open(os.path.join(FIXTURES, "expected-v3.json"), encoding="utf-8") as handle:
        return json.load(handle)


def v3_cases():
    """Every version 3 record fixture as (name, bytes, expected)."""
    for name, result in sorted(load_expected_v3()["record_v3"].items()):
        with open(os.path.join(FIXTURES, V3_DIRECTORY, name), "rb") as handle:
            yield name, handle.read(), result


def run(parser, kind, data):
    if kind in ("record", "record_v3"):
        return parser.record(data)
    return parser.pr_body(data.decode("utf-8"))


def describe(kind, expected):
    if kind in ("record", "record_v3"):
        return "parses" if isinstance(expected, dict) else expected
    risk = expected["risk"]
    reverts = expected["reverts"]
    return "risk %s, reverts %s" % (
        risk["tier"] if isinstance(risk, dict) else risk,
        "none" if reverts is None else "valid" if isinstance(reverts, dict) else reverts,
    )


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


class SharedParserFixtures(unittest.TestCase):
    """Filled below: one test per registered parser and fixture."""


def _add_test(parser, kind, name, data, expected):
    def test(self):
        self.assertEqual(run(parser, kind, data), expected)

    test.__doc__ = "%s parser, %s %s: %s" % (parser.name, kind.replace("_", "-"), name, describe(kind, expected))
    test_name = "test_%s_%s_%s" % (slug(parser.name), kind, slug(name))
    if hasattr(SharedParserFixtures, test_name):
        raise AssertionError("two fixtures make the test name %s" % test_name)
    setattr(SharedParserFixtures, test_name, test)


for _parser in parsers.PARSERS:
    for _kind, _name, _data, _expected in cases(_parser):
        _add_test(_parser, _kind, _name, _data, _expected)
    if _parser.supports(3):
        for _name, _data, _expected in v3_cases():
            _add_test(_parser, "record_v3", _name, _data, _expected)


class FixtureSet(unittest.TestCase):
    def test_every_fixture_file_has_an_expected_result_and_every_result_a_file(self):
        expected = load_expected()
        for kind, directory in DIRECTORIES.items():
            on_disk = set(os.listdir(os.path.join(FIXTURES, directory)))
            self.assertEqual(on_disk, set(expected[kind]), kind)
        on_disk = set(os.listdir(os.path.join(FIXTURES, V3_DIRECTORY)))
        self.assertEqual(on_disk, set(load_expected_v3()["record_v3"]), V3_DIRECTORY)

    def test_every_parser_is_registered_once_with_both_adapters(self):
        names = [parser.name for parser in parsers.PARSERS]
        self.assertEqual(len(names), len(set(names)))
        for parser in parsers.PARSERS:
            self.assertTrue(callable(parser.record) and callable(parser.pr_body), parser.name)


class ParserCoverage(support.TempDirCase):
    def add_draft(self):
        root = Path(shutil.copytree(support.REAL_STORE, self.path("store")))
        previous = max(int(entry.name) for entry in root.iterdir() if entry.name.isdecimal())
        source = root / str(previous)
        draft = root / str(previous + 1)
        shutil.copytree(source, draft, ignore=shutil.ignore_patterns("change-note.md"))
        if not (source / "change-note.md").exists():
            (source / "change-note.md").write_text(
                "urgency: when convenient\nmust-act: no\n\n测试版本。\n", encoding="utf-8"
            )
        manifest = draft / "manifest.json"
        contents = json.loads(manifest.read_text(encoding="utf-8"))
        contents["version"] = previous + 1
        manifest.write_text(json.dumps(contents), encoding="utf-8")
        return draft

    def run_fixtures(self, root):
        # Use the ordinary unittest collection and result reporting with a fresh store.
        return subprocess.run(
            [sys.executable, "-c",
             "import sys, support, unittest\n"
             "support.REAL_STORE = sys.argv.pop(1)\n"
             "unittest.main(module='test_parser_fixtures')",
             str(root), "-v", "SharedParserFixtures"],
            cwd=os.path.dirname(__file__), env=support.isolated_env(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

    def assert_store_coverage(self, root):
        result = self.run_fixtures(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        passed = {}
        for line in result.stdout.splitlines():
            if line.endswith(" ... ok"):
                parser, fixture = line.split(" parser, ", 1)
                passed.setdefault(parser, []).append(fixture.rsplit(": ", 1)[0])

        catalog = load_expected()
        common = set()
        for kind in ("record", "pr_body"):
            names = list(catalog[kind]) + list(catalog[kind + "_texts"])
            common.update(kind.replace("_", "-") + " " + name for name in names)
        with_bots = common | {"record-v3 " + name for name in load_expected_v3()["record_v3"]}
        expected = {"machine": with_bots}
        for entry in root.iterdir():
            if entry.is_dir() and entry.name.isdecimal():
                expected["governed-v" + entry.name] = with_bots if int(entry.name) >= 3 else common
        self.assertEqual(set(passed), set(expected))
        for parser, fixtures in expected.items():
            with self.subTest(parser=parser):
                self.assertCountEqual(passed[parser], fixtures)

    def test_every_stored_version_and_the_machine_run_their_applicable_fixtures(self):
        self.assert_store_coverage(Path(support.REAL_STORE))

    def test_a_new_draft_runs_each_applicable_fixture(self):
        self.assert_store_coverage(self.add_draft().parent)

    def test_an_unloadable_draft_fails_the_suite_and_names_the_version(self):
        draft = self.add_draft()
        gate = Path(store.Store(draft.parent).template_path(int(draft.name), parsers.GATE_PATH))
        for source, cause in [
            ("raise RuntimeError('broken draft parser')", "RuntimeError: broken draft parser"),
            ("raise SystemExit(0)", "SystemExit: 0"),
        ]:
            with self.subTest(cause=cause):
                gate.write_text(source + "\n", encoding="utf-8")
                result = self.run_fixtures(draft.parent)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("governed-v" + draft.name, result.stdout)
                self.assertIn(cause, result.stdout)


if __name__ == "__main__":
    unittest.main()
