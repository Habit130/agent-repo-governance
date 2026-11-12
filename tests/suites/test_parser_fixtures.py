"""The shared parser fixtures (#44 §5): every registered parser against every fixture.

`tests/fixtures/parsers/` holds the record fixtures under `record/`, the PR-body fixtures
under `pr-body/`, and `expected.json`. That file maps each fixture file to its expected
result, and adds the cases `git diff --check` would flag as inline texts. There is one test
per parser and fixture, named for both, so the verbose output lists each parser and each
fixture's result.

`record-v3/` and `expected-v3.json` hold the version 3 record fixtures (#148), run only
against `parsers.V3_PARSERS`: a version 1 or 2 governed parser never reads a version 3 record.
"""

import json
import os
import re
import unittest

import parsers
import support

FIXTURES = os.path.join(support.FIXTURES, "parsers")
DIRECTORIES = {"record": "record", "pr_body": "pr-body"}
V3_DIRECTORY = "record-v3"


def load_expected():
    with open(os.path.join(FIXTURES, "expected.json"), encoding="utf-8") as handle:
        return json.load(handle)


def cases():
    """Every fixture as (kind, name, bytes, expected): the files, then the inline texts."""
    expected = load_expected()
    for kind, directory in sorted(DIRECTORIES.items()):
        for name, result in sorted(expected[kind].items()):
            with open(os.path.join(FIXTURES, directory, name), "rb") as handle:
                yield kind, name, handle.read(), result
        for name, case in sorted(expected[kind + "_texts"].items()):
            yield kind, name, case["text"].encode("utf-8"), case["expected"]


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
    for _kind, _name, _data, _expected in cases():
        _add_test(_parser, _kind, _name, _data, _expected)
    if _parser.name in parsers.V3_PARSERS:
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

    def test_the_version_3_fixtures_run_against_the_machine_and_version_3_parsers_only(self):
        registered = [parser.name for parser in parsers.PARSERS]
        self.assertEqual([name for name in parsers.V3_PARSERS if name in registered], list(parsers.V3_PARSERS))
        names = [name for name in dir(SharedParserFixtures) if "_record_v3_" in name]
        self.assertEqual(sorted(set(name.split("_record_v3_")[0] for name in names)),
                         sorted("test_" + slug(name) for name in parsers.V3_PARSERS))

    def test_every_parser_is_registered_once_with_both_adapters(self):
        names = [parser.name for parser in parsers.PARSERS]
        self.assertEqual(len(names), len(set(names)))
        for parser in parsers.PARSERS:
            self.assertTrue(callable(parser.record) and callable(parser.pr_body), parser.name)


if __name__ == "__main__":
    unittest.main()
