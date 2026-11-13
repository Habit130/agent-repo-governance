"""Merge watch (#41 §9): Seam 2, Merge watch's records, plus its workflow and its entry.

Seam 2's input is a recorded `push` or `workflow_run` event, the merged PR, the head's checks,
statuses and comments, the open miss records, and the record; its output is the records to
open. Each case under `tests/fixtures/merge-watch/cases/` holds:

- `event_name` and `event`, the payload trimmed to what Merge watch reads;
- `github`, GitHub's answer for each REST path the script reads, every page joined. A path
  the case doesn't hold can't be read, as when GitHub answers with an error;
- `expected`, each record's title and body, written from `issue-tracker.md`'s format.

The record is `tests/fixtures/merge-watch/record.yml`. The script loads from version 1's
store, beside the gate script it imports. Version 3 cases under `v3/` load its handler
separately and check its records against the version 3 tracker format. A version 3 case may
also hold `not_found`, the paths GitHub answers with its own 404 `Not Found`, which version
3's reader raises as `NotFound` rather than as a read that failed.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest
from unittest import mock

import materialized
import support
from standins import environment
from target_state import target_ruleset

GOVERNANCE = os.path.join(support.REAL_STORE, "1", "templates", "dot-github", "governance")
sys.path.insert(0, GOVERNANCE)
import merge_watch  # noqa: E402

FIXTURES = os.path.join(support.FIXTURES, "merge-watch")
CASES = os.path.join(FIXTURES, "cases")
V3_CASES = os.path.join(FIXTURES, "v3")
GOVERNANCE_V3 = os.path.join(support.REAL_STORE, "3", "templates", "dot-github", "governance")


def _load_v3(name):
    spec = importlib.util.spec_from_file_location("%s_v3" % name, os.path.join(GOVERNANCE_V3, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Version 3's script imports the gate beside it as `gate`: give it version 3's while it loads.
gate_v3 = _load_v3("gate")
_gate_v1 = sys.modules["gate"]
sys.modules["gate"] = gate_v3
try:
    watch_v3 = _load_v3("merge_watch")
finally:
    sys.modules["gate"] = _gate_v1
WORKFLOW = ".github/workflows/merge-watch.yml"
SCRIPT = ".github/governance/merge_watch.py"
ISSUE_TRACKER = os.path.join(support.REAL_STORE, "1", "templates", "docs", "agents", "issue-tracker.md")
# The categories Merge watch records (issue-tracker.md, Miss records).
CATEGORIES = ("red-default-branch", "revert", "missing-review", "push-without-pr")


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def case_names():
    return sorted(name[: -len(".json")] for name in os.listdir(CASES))


def agent_account():
    with open(os.path.join(FIXTURES, "record.yml"), "rb") as handle:
        return merge_watch.gate.parse_record(handle.read())["agent_account"]


def recorded(github):
    def read(path):
        if path not in github:
            raise merge_watch.ReadError(path)
        return github[path]

    return read


def recorded_v3(github, not_found=()):
    """Version 3's reader: a path in not_found raises NotFound, and any other path the case doesn't hold ReadError."""
    def read(path):
        if path in not_found:
            raise watch_v3.NotFound(path)
        if path not in github:
            raise watch_v3.ReadError(path)
        return github[path]

    return read


def decide(case):
    return merge_watch.decide(case["event_name"], case["event"], agent_account(), recorded(case["github"]))


class SeamTwo(unittest.TestCase):
    """Filled below: one test per case file."""


def _add_case(name):
    def test(self):
        case = load(os.path.join(CASES, name + ".json"))
        records = decide(case)
        self.assertEqual([{"title": r["title"], "body": r["body"]} for r in records], case["expected"])
        for rec in records:
            self.assertEqual(rec["labels"], ["miss"])

    test.__doc__ = "merge watch case %s" % name
    setattr(SeamTwo, "test_" + re.sub(r"[^A-Za-z0-9]+", "_", name), test)


for _name in case_names():
    _add_case(_name)


def record_format(version="1"):
    """issue-tracker.md's miss record format: (the six field names in order, kind by category)."""
    text = support.read_text(os.path.join(support.REAL_STORE, version, "templates", "docs", "agents", "issue-tracker.md"))
    section = text.split("\n### Format\n", 1)[1].split("\n### Examples\n", 1)[0]
    block = section.split("```text\n", 1)[1].split("```", 1)[0]
    fields = [line.split(":", 1)[0] for line in block.strip("\n").split("\n")]
    kinds = dict(re.findall(r"(?m)^\| `([a-z-]+)` \| ([a-z ]+) \|", section))
    return fields, kinds


class RecordFormat(unittest.TestCase):
    """CRIT-6: every record Seam 2 expects, and every one the script gives, field by field against issue-tracker.md."""

    def assert_record(self, rec, where, version="1"):
        fields, kinds = record_format(version)
        lines = rec["body"].split("\n")
        self.assertEqual(rec["body"][-1], "\n", where)
        self.assertEqual([line.split(": ", 1)[0] for line in lines[:6]], fields, where)
        self.assertEqual(lines[6:], [""], where)
        values = dict(line.split(": ", 1) for line in lines[:6])
        category, kind = values["Category"], values["Kind"]
        self.assertIn(category, CATEGORIES, where)
        self.assertEqual(kinds[category], kind, where)
        merged = values["Merged PR"]
        self.assertRegex(merged, r"^(#[1-9][0-9]*|none)$", where)
        self.assertEqual(rec["title"], "Miss: %s, %s%s" % (kind, category, "" if merged == "none" else " in " + merged), where)
        self.assertEqual(values["Found by"], "Merge watch", where)
        self.assertEqual(values["Bug issue"], "none", where)
        self.assertNotIn("\n", values["Observed"])
        # Numeric GitHub run IDs in URLs are not commit SHAs.
        prose = re.sub(r"https?://\S+", "", values["Observed"])
        for sha in re.findall(r"\b[0-9a-f]{7,}\b", prose):
            self.assertEqual(len(sha), 40, (where, "Observed names full commit SHAs"))

    def test_the_format_is_read_from_the_template(self):
        fields, kinds = record_format()
        self.assertEqual(fields, ["Merged PR", "Kind", "Category", "Observed", "Found by", "Bug issue"])
        self.assertEqual({category: kinds[category] for category in CATEGORIES}, {
            "red-default-branch": "escape", "revert": "escape",
            "missing-review": "process miss", "push-without-pr": "process miss",
        })

    def test_every_expected_and_given_record_follows_the_format(self):
        count = 0
        for name in case_names():
            case = load(os.path.join(CASES, name + ".json"))
            for rec in case["expected"] + decide(case):
                self.assert_record(rec, name)
                count += 1
        self.assertGreater(count, 40)

    def test_every_category_merge_watch_records_has_a_case(self):
        seen = set()
        for name in case_names():
            for rec in load(os.path.join(CASES, name + ".json"))["expected"]:
                seen.add(rec["body"].split("\nCategory: ", 1)[1].split("\n", 1)[0])
        self.assertEqual(sorted(seen), sorted(CATEGORIES))

    def test_a_missing_review_lists_the_kinds_in_the_merge_summarys_order(self):
        case = load(os.path.join(CASES, "high-missing-everything.json"))
        (rec,) = decide(case)
        self.assertIn(", lacks: bugbot, codex, reviewer, merge-summary.\n", rec["body"])


class Parser(unittest.TestCase):
    """CRIT-2: the script reads the `Risk:` and `Reverts:` lines with the gate script's parser, imported from beside it."""

    def test_the_script_imports_the_gate_beside_it_and_holds_no_parser_of_its_own(self):
        self.assertEqual(os.path.dirname(os.path.abspath(merge_watch.gate.__file__)), GOVERNANCE)
        source = support.read_text(os.path.join(GOVERNANCE, "merge_watch.py"))
        self.assertIn("\nsys.dont_write_bytecode = True\n\nimport gate", source)
        self.assertNotIn("Risk: (", source)
        self.assertNotIn("Reverts: (", source)

    def test_the_gate_parser_decides_the_tier_and_the_revert(self):
        calls = []
        real = merge_watch.gate.parse_body

        def spy(body):
            calls.append(body)
            return real(body)

        case = load(os.path.join(CASES, "merged-reverts-pr.json"))
        with mock.patch.object(merge_watch.gate, "parse_body", spy):
            self.assertEqual(len(decide(case)), 1)
        self.assertEqual(calls, [case["github"]["repos/Habit130/tally/commits/%s/pulls" % case["event"]["after"]][0]["body"]])


class Rendered(support.TempDirCase):
    """The workflow and the script as version 1 renders them into tally."""

    def setUp(self):
        super(Rendered, self).setUp()
        self.worktree, _ = materialized.render_version_one(self.tmp)

    def text(self, path):
        return support.read_text(os.path.join(self.worktree, *path.split("/")))


class Workflow(Rendered):
    """CRIT-1: the triggers, the branch filters, the `workflows` glob and the six permissions."""

    def test_it_runs_on_pushes_and_completed_runs_on_the_default_branch_of_every_workflow_but_itself(self):
        workflow = self.text(WORKFLOW)
        self.assertIn(
            "\non:\n"
            "  push:\n    branches:\n      - \"main\"\n"
            "  workflow_run:\n    types: [completed]\n    branches:\n      - \"main\"\n"
            "    workflows:\n      - \"**\"\n      - \"!merge-watch\"\n\n",
            workflow,
        )
        self.assertEqual(re.findall(r"(?m)^  ([a-z_]+):$", workflow.split("\npermissions:")[0]), ["push", "workflow_run"])
        self.assertIn("\nname: merge-watch\n", workflow)

    def test_its_permissions_are_exactly_the_six(self):
        workflow = self.text(WORKFLOW)
        self.assertIn(
            "\npermissions:\n  contents: read\n  pull-requests: read\n  issues: write\n"
            "  checks: read\n  statuses: read\n  actions: read\n\n",
            workflow,
        )
        self.assertEqual(workflow.count("permissions:"), 1)

    def test_it_names_no_per_repository_workflow_and_cancels_no_run(self):
        workflow = self.text(WORKFLOW)
        self.assertEqual(re.findall(r"(?m)^ +- \"(.*)\"$", workflow), ["main", "main", "**", "!merge-watch"])
        self.assertNotIn("concurrency", workflow)

    def test_its_one_step_runs_the_script_from_the_default_branchs_checkout(self):
        workflow = self.text(WORKFLOW)
        steps = workflow.split("\n    steps:\n")[1]
        uses = re.findall(r"(?m)^ +(?:- )?uses: (\S+)", steps)
        self.assertEqual(len(uses), 1)
        self.assertRegex(uses[0], r"^actions/checkout@[0-9a-f]{40}$")
        self.assertIsNone(re.search(r"(?m)^ +(ref|repository|path):", steps))
        self.assertIn("persist-credentials: false", steps)
        self.assertEqual(re.findall(r"(?m)^ +(?:- )?run:(.*)$", steps), [" python3 .github/governance/merge_watch.py --post"])
        self.assertEqual(sorted(set(re.findall(r"\$\{\{(.*?)\}\}", workflow))), [" github.token "])
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, *SCRIPT.split("/"))))

    def test_it_is_not_a_required_check(self):
        with open(os.path.join(self.worktree, ".github", "governance", "record.yml"), "rb") as handle:
            checks = merge_watch.gate.parse_record(handle.read())["confirmed"]["required_checks"]
        rules = target_ruleset("Gate", checks)["rules"]
        contexts = [check["context"] for rule in rules if rule["type"] == "required_status_checks"
                    for check in rule["parameters"]["required_status_checks"]]
        self.assertNotIn("merge-watch", contexts)
        self.assertIn("governance-gate", contexts)


class Entry(Rendered):
    """The rendered script's entry, as the workflow runs it: the event, `gh api` reads through the stand-in, and each record posted."""

    def setUp(self):
        super(Entry, self).setUp()
        patcher = mock.patch.dict(os.environ, support.isolated_env())
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_entry(self, name, drop=(), post_exit=0):
        case = load(os.path.join(CASES, name + ".json"))
        event = self.path("event.json")
        with open(event, "w") as handle:
            json.dump(case["event"], handle)
        calls = []
        for path, answer in sorted(case["github"].items()):
            if path in drop:
                continue
            if path.split("?")[0].endswith("/check-runs"):
                answer = {"total_count": len(answer), "check_runs": answer}
            calls.append({
                "args": ["api", "%s%sper_page=100&page=1" % (path, "&" if "?" in path else "?")],
                "stdout": json.dumps(answer) + "\n",
                "exit": 0,
            })
        for rec in case["expected"]:
            calls.append({
                "args": ["api", "--method", "POST", "repos/Habit130/tally/issues", "--input", "-"],
                "stdin": json.dumps(dict(rec, labels=["miss"]), sort_keys=True),
                "stdout": "{}\n",
                "exit": post_exit,
            })
        recording = self.path("gh.json")
        with open(recording, "w") as handle:
            json.dump({"tool": "gh", "calls": calls}, handle)
        scratch = self.path("scratch")
        os.makedirs(scratch)
        env = environment.environment(scratch, gh_recording=recording, base=support.isolated_env())
        env.update({"GITHUB_EVENT_PATH": event, "GITHUB_EVENT_NAME": case["event_name"], "GITHUB_REPOSITORY": "Habit130/tally"})
        before = support.git(self.worktree, "status", "--porcelain", "--untracked-files=all")
        result = subprocess.run(
            [sys.executable, os.path.join(self.worktree, ".github", "governance", "merge_watch.py"), "--post"],
            cwd=self.worktree, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
        )
        self.assertEqual(support.git(self.worktree, "status", "--porcelain", "--untracked-files=all"), before)
        return case, result, environment.read_log(scratch)

    def test_it_reads_through_gh_and_opens_each_record_labelled_miss(self):
        case, result, calls = self.run_entry("merged-reverts-pr")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(all(call["recorded"] for call in calls), calls)
        posts = [json.loads(call["stdin"]) for call in calls if "--method" in call["args"]]
        self.assertEqual(posts, [dict(rec, labels=["miss"]) for rec in case["expected"]])
        self.assertIn("MISS Miss: escape, revert in #37. ", result.stdout)

    def test_no_miss_opens_nothing_and_says_so(self):
        _, result, calls = self.run_entry("high-complete")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([call for call in calls if "--method" in call["args"]], [])
        self.assertTrue(all(call["recorded"] for call in calls), calls)
        self.assertEqual(result.stdout, "No miss in this push event.\n")

    def test_a_read_that_fails_still_opens_the_false_record_and_exits_one(self):
        case, result, calls = self.run_entry("checks-unreadable")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("UNREADABLE repos/Habit130/tally/commits/", result.stdout)
        posts = [json.loads(call["stdin"]) for call in calls if "--method" in call["args"]]
        self.assertEqual(posts, [dict(rec, labels=["miss"]) for rec in case["expected"]])

    def test_a_record_github_refuses_fails_the_run(self):
        _, result, _ = self.run_entry("push-without-pr", post_exit=1)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL opening the record Miss: process miss, push-without-pr", result.stdout)

    def test_a_full_page_reads_the_next(self):
        reads = []
        pages = {1: [{"n": i} for i in range(100)], 2: [{"n": 100}]}

        def fake(args, stdout, stderr):
            page = int(args[2].rsplit("page=", 1)[1])
            reads.append(args[2])
            return subprocess.CompletedProcess(args, 0, json.dumps(pages[page]).encode("utf-8"), b"")

        with mock.patch.object(merge_watch.subprocess, "run", fake):
            items = merge_watch.GitHub()("repos/o/r/issues/1/comments")
        self.assertEqual(len(items), 101)
        self.assertEqual(reads, ["repos/o/r/issues/1/comments?per_page=100&page=1", "repos/o/r/issues/1/comments?per_page=100&page=2"])


class VersionThree(unittest.TestCase):
    assert_record = RecordFormat.assert_record

    def test_recorded_events(self):
        for path in sorted(os.listdir(V3_CASES)):
            with self.subTest(case=path):
                case = load(os.path.join(V3_CASES, path))
                records = watch_v3.decide(case["event_name"], case["event"], agent_account(),
                                          recorded_v3(case["github"], case.get("not_found", ())))
                self.assertEqual(records, [dict(item, labels=["miss"]) for item in case["expected"]])
                for item in records:
                    self.assert_record(item, path, "3")

    def decide_v3(self, name, notes=None, read=None):
        case = load(os.path.join(V3_CASES, name + ".json"))
        return watch_v3.decide(case["event_name"], case["event"], agent_account(),
                               read or recorded_v3(case["github"], case.get("not_found", ())), notes)

    def test_a_base_below_version_three_is_not_judged_and_says_so(self):
        notes = []
        self.assertEqual(self.decide_v3("review-base-at-version-two", notes), [])
        self.assertEqual(notes, ["#42 merged onto a base whose record is at version 2; its review bots follow that "
                                 "version's rules, which this script doesn't judge."])
        (rec,) = self.decide_v3("review-base-at-version-two-unreviewed")
        self.assertIn("lacks: reviewer, merge-summary.", rec["body"])

    def test_low_reads_no_bot(self):
        for name in ("review-low-no-bot", "review-low-missing-summary"):
            case = load(os.path.join(V3_CASES, name + ".json"))
            reads = []
            inner = recorded_v3(case["github"])

            def spy(path):
                reads.append(path)
                return inner(path)

            self.decide_v3(name, read=spy)
            self.assertEqual([path for path in reads if "/reviews" in path or "/check-runs" in path], [], name)

    def test_a_disabled_bot_is_never_read_or_reported(self):
        def never(pull):
            raise AssertionError("the disabled Codex review bot was read")

        with mock.patch.dict(watch_v3.PROVIDERS, {"codex": never}):
            notes = []
            self.assertEqual(self.decide_v3("review-disabled-bot-never-read", notes), [])
            self.assertEqual(notes, [])
            (rec,) = self.decide_v3("review-disabled-bot-fills-nothing")
            self.assertIn("lacks: bot-1.", rec["body"])

    def test_the_base_record_is_read_at_the_commit_before_the_squash(self):
        case = load(os.path.join(V3_CASES, "review-shortened-list-judged-by-base.json"))
        reads = []
        inner = recorded_v3(case["github"])

        def spy(path):
            reads.append(path)
            return inner(path)

        self.assertEqual(self.decide_v3("review-shortened-list-judged-by-base", read=spy), [])
        contents = [path for path in reads if "/contents/" in path]
        self.assertEqual(contents, ["repos/Habit130/tally/contents/.github/governance/record.yml?ref=%s" % case["event"]["before"]])

    def test_a_base_without_a_record_is_judged_by_the_record_the_merge_adds_and_says_so(self):
        case = load(os.path.join(V3_CASES, "review-base-without-record-initialize.json"))
        reads, notes = [], []
        inner = recorded_v3(case["github"], case["not_found"])

        def spy(path):
            reads.append(path)
            return inner(path)

        self.assertEqual(self.decide_v3("review-base-without-record-initialize", notes, read=spy), [])
        record_at = "repos/Habit130/tally/contents/.github/governance/record.yml?ref=%s"
        self.assertEqual([path for path in reads if "/contents/" in path],
                         [record_at % case["event"]["before"], record_at % case["event"]["after"]])
        self.assertEqual(notes, ["#42 merged onto a base with no governance record, so the record it adds names "
                                 "the enabled review bots."])

    def test_a_base_record_that_fails_to_read_never_reads_the_merged_tree(self):
        case = load(os.path.join(V3_CASES, "review-base-record-unreadable.json"))
        github = dict(case["github"], **{"repos/Habit130/tally/contents/.github/governance/record.yml?ref=%s"
                                         % case["event"]["after"]: "version: 3\n"})
        reads = []
        inner = recorded_v3(github)

        def spy(path):
            reads.append(path)
            return inner(path)

        notes = []
        (rec,) = self.decide_v3("review-base-record-unreadable", notes, read=spy)
        self.assertIn("lacks: bot-1, bot-2.", rec["body"])
        self.assertEqual([path for path in reads if "/contents/" in path],
                         ["repos/Habit130/tally/contents/.github/governance/record.yml?ref=%s" % case["event"]["before"]])
        self.assertEqual(notes, [])

    def test_each_later_commit_in_a_push_takes_the_one_before_it_as_its_base(self):
        case = load(os.path.join(V3_CASES, "review-low-no-bot.json"))
        first = "2" * 40
        event = dict(case["event"], commits=[{"id": first}, case["event"]["commits"][0]])
        github = dict(case["github"], **{"repos/Habit130/tally/commits/%s/pulls" % first: []})
        reads = []
        inner = recorded_v3(github)

        def spy(path):
            reads.append(path)
            return inner(path)

        watch_v3.decide("push", event, agent_account(), spy)
        self.assertIn("repos/Habit130/tally/contents/.github/governance/record.yml?ref=%s" % first, reads)

    def test_a_contents_path_is_read_raw_and_once(self):
        calls = []

        def fake(args, stdout, stderr):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, b"version: 3\n", b"")

        with mock.patch.object(watch_v3.subprocess, "run", fake):
            text = watch_v3.GitHub()("repos/o/r/contents/.github/governance/record.yml?ref=abc")
        self.assertEqual(text, "version: 3\n")
        self.assertEqual(calls, [["gh", "api", "-H", "Accept: application/vnd.github.raw",
                                  "repos/o/r/contents/.github/governance/record.yml?ref=abc"]])

    def test_a_contents_read_that_fails_is_unreadable(self):
        def fake(args, stdout, stderr):
            return subprocess.CompletedProcess(args, 1, b"", b"HTTP 404: Not Found")

        github = watch_v3.GitHub()
        with mock.patch.object(watch_v3.subprocess, "run", fake):
            with self.assertRaises(watch_v3.ReadError):
                github("repos/o/r/contents/x?ref=abc")
        self.assertEqual(github.unreadable, ["repos/o/r/contents/x?ref=abc: HTTP 404: Not Found"])

    def test_githubs_own_not_found_is_no_failed_read(self):
        body = (b'{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/contents'
                b'#get-repository-content","status":"404"}')

        def fake(args, stdout, stderr):
            return subprocess.CompletedProcess(args, 1, body, b"gh: Not Found (HTTP 404)\n")

        github = watch_v3.GitHub()
        with mock.patch.object(watch_v3.subprocess, "run", fake):
            with self.assertRaises(watch_v3.NotFound):
                github("repos/o/r/contents/.github/governance/record.yml?ref=abc")
        self.assertEqual(github.unreadable, [])

    def test_any_other_answer_to_a_contents_read_is_a_failed_read(self):
        answers = [
            (b'{"message":"No commit found for the ref abc","documentation_url":"https://docs.github.com/v3/repos/contents/",'
             b'"status":"404"}', b"gh: No commit found for the ref abc (HTTP 404)\n"),
            (b'{"message":"Not Found"}', b"gh: Not Found (HTTP 404)\n"),
            (b'{"message":"Resource not accessible by integration","status":"403"}', b"gh: (HTTP 403)\n"),
            (b"", b"error connecting to api.github.com\n"),
        ]
        for stdout, stderr in answers:
            with self.subTest(stdout=stdout):
                def fake(args, stdout_=None, stderr_=None, **kwargs):
                    return subprocess.CompletedProcess(args, 1, stdout, stderr)

                github = watch_v3.GitHub()
                with mock.patch.object(watch_v3.subprocess, "run", fake):
                    with self.assertRaises(watch_v3.ReadError) as raised:
                        github("repos/o/r/contents/x?ref=abc")
                self.assertNotIsInstance(raised.exception, watch_v3.NotFound)
                self.assertEqual(len(github.unreadable), 1)

    def test_the_script_names_no_retired_bot(self):
        source = support.read_text(os.path.join(GOVERNANCE_V3, "merge_watch.py"))
        for retired in ("bugbot", "Bugbot", "cursor", "reduced", "substituted"):
            self.assertNotIn(retired, source)


if __name__ == "__main__":
    unittest.main()
