"""Offline replays at the GitHub read, local registration and queue boundaries of wait-on-pr."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "machine" / "scripts"))
sys.path.insert(0, str(ROOT / "machine" / "skills" / "wait-on-pr"))
from machinelib import AGENT
import wait_on_pr as wait

RECORD = json.loads((ROOT / "tests/fixtures/wait-on-pr/pr-268.json").read_text())


def page(nodes):
    return {"nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}


def github(nit=False, reply=False, resolved=False):
    thread = {"id": RECORD["thread"], "isResolved": resolved, "comments": page([
        {"id": comment, "lastEditedAt": None}
        for comment in ([RECORD["nit"], RECORD["reply"]] if reply else [RECORD["nit"]])])}
    commit = {"oid": RECORD["head"], "status": {"contexts": [RECORD["status"]]}}
    return {"id": "PR_268", "state": "OPEN", "headRefOid": RECORD["head"],
            "commits": {"nodes": [{"commit": commit}]},
            "reviews": page([RECORD["nit_review"]] if nit else []),
            "reviewThreads": page([thread] if nit else []), "comments": page([])}


def snapshot(raw):
    return wait.snapshot(lambda *_: {"repository": {"pullRequest": raw}}, "owner/repo", 268)


class Changes(unittest.TestCase):
    def test_268_same_head_nit_reply_and_resolution_each_wake(self):
        before = snapshot(github())
        nit = snapshot(github(nit=True))
        reply = snapshot(github(nit=True, reply=True))
        resolved = snapshot(github(nit=True, reply=True, resolved=True))
        for previous, current in ((before, nit), (nit, reply), (reply, resolved)):
            self.assertEqual(wait.event(previous, current), "change")
        self.assertIsNone(wait.event(resolved, resolved))

    def test_head_status_issue_comment_add_and_edit_and_exclusions(self):
        baseline = snapshot(github())
        raw = github()
        raw["headRefOid"] = raw["commits"]["nodes"][0]["commit"]["oid"] = "a" * 40
        self.assertEqual(wait.event(baseline, snapshot(raw)), "change")
        raw = github()
        raw["commits"]["nodes"][0]["commit"]["status"] = None
        self.assertEqual(wait.event(baseline, snapshot(raw)), "change")
        raw = github()
        raw["comments"] = page([{"id": "C1", "lastEditedAt": None}])
        added = snapshot(raw)
        self.assertEqual(wait.event(baseline, added), "change")
        raw["comments"]["nodes"][0]["lastEditedAt"] = "2026-11-24T05:00:00Z"
        self.assertEqual(wait.event(added, snapshot(raw)), "change")
        for field in ("checkSuites", "labels", "body", "reactions"):
            with self.subTest(field=field):
                changed = github()
                changed[field] = "new"
                self.assertIsNone(wait.event(baseline, snapshot(changed)))
                self.assertNotIn(field, wait.QUERY)

    def test_terminal_baseline_distinguishes_merge_and_close(self):
        for state in ("MERGED", "CLOSED"):
            self.assertEqual(wait.event(None, snapshot({"state": state})), state.lower())

    def test_nested_replies_after_first_page(self):
        raw = github(nit=True)
        raw["reviewThreads"]["nodes"][0]["comments"]["pageInfo"] = {"hasNextPage": True, "endCursor": "next"}
        def fetch(query, variables):
            if "after" in variables:
                self.assertEqual(variables, {"id": RECORD["thread"], "after": "next"})
                self.assertIn("PullRequestReviewThread", query)
                return {"node": {"comments": page([{"id": RECORD["reply"], "lastEditedAt": None}])}}
            return {"repository": {"pullRequest": raw}}
        self.assertEqual(wait.snapshot(fetch, "owner/repo", 268), snapshot(github(nit=True, reply=True)))


class GitHubReads(unittest.TestCase):
    def test_replacement_stops_pagination_before_the_next_request(self):
        raw = github(nit=True)
        raw["reviews"]["pageInfo"] = {"hasNextPage": True, "endCursor": "next"}
        requests = []
        def fetch(query, variables):
            requests.append(variables)
            return {"repository": {"pullRequest": raw}}
        with self.assertRaises(wait.Replaced):
            wait.snapshot(fetch, "owner/repo", 268, active=lambda: not requests)
        self.assertEqual(len(requests), 1)

    def test_wrong_default_account_cannot_read_the_pr(self):
        result = subprocess.CompletedProcess([], 0, "another-login\n")
        with mock.patch.object(subprocess, "run", return_value=result) as run:
            with self.assertRaisesRegex(wait.ReadFailure, "agent account"):
                wait.github_read("gh", "owner/repo", 268, float("inf"))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-3:], ["user", "--jq", ".login"])

    def test_normal_login_and_pr_read_use_the_same_gh(self):
        result = {"data": {"repository": {"pullRequest": {"state": "MERGED"}}}}
        outputs = [subprocess.CompletedProcess([], 0, AGENT + "\n"),
                   subprocess.CompletedProcess([], 0, json.dumps(result))]
        with mock.patch.object(subprocess, "run", side_effect=outputs) as run:
            self.assertEqual(wait.github_read("/installed/gh", "owner/repo", 268, float("inf")), {"state": "MERGED"})
        self.assertEqual([call.args[0][:5] for call in run.call_args_list],
                         [["/installed/gh", "api", "--hostname", "github.com", route] for route in ("user", "graphql")])

    def test_account_overrides_refused_before_github_runs(self):
        env = {"HOME": "/fixture-home", "XDG_CONFIG_HOME": "/fixture-config"}
        for name in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GH_CONFIG_DIR"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "agent account"):
                    wait.github_cli(dict(env, **{name: "/fixture-other"}))
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(ValueError, "gh unavailable"):
                wait.github_cli(dict(env, GH_CONFIG_DIR="/fixture-config/gh"))


class WaitLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.slot = wait.Slot(Path(self.temp.name), "owner/repo", 268, "12345678-1234-4321-8765-123456789012")
        self.time = 0
        self.sent = []
        self.reads = []

    def sleep(self, seconds):
        self.time += seconds

    def replay(self, observations, kind="copilot", send=None, sleep=None):
        def read(deadline, active):
            self.reads.append(self.time)
            observation = observations[min(len(self.reads) - 1, len(observations) - 1)]
            if isinstance(observation, Exception):
                raise observation
            return snapshot(observation)
        def queue(message):
            self.sent.append(message)
            return send(message) if send else "queue exited 0; resume unconfirmed"
        return wait.watch(self.slot, kind, read, queue, clock=lambda: self.time, sleep=sleep or self.sleep)

    def test_own_write_is_in_baseline_failed_read_retries_then_notifies_once(self):
        nonce = self.replay([github(nit=True), github(nit=True), wait.ReadFailure("GitHub timeout"),
                             github(nit=True, reply=True)])
        self.assertEqual(self.reads, [0, 60, 120, 180])
        self.assertEqual(len(self.sent), 1)
        for field in ("owner/repo#268", "change", nonce, "GitHub timeout"):
            self.assertIn(field, self.sent[0])
        self.assertEqual(self.slot.stop(nonce), "change")
        self.assertEqual(self.slot.stop(nonce), "late or duplicate")

    def test_arming_waits_for_a_baseline_and_reports_the_startup_gap(self):
        output = StringIO()
        observed = []
        def read(deadline, active):
            self.reads.append(self.time)
            observed.append(output.getvalue())
            if len(self.reads) == 1:
                raise wait.ReadFailure("GitHub timeout")
            return snapshot(github(nit=True, reply=len(self.reads) > 2))
        with redirect_stdout(output):
            wait.watch(self.slot, "role", read, self.sent.append, clock=lambda: self.time, sleep=self.sleep)
        self.assertEqual(self.reads, [0, 60, 120])
        self.assertNotIn("Armed", observed[0] + observed[1])
        self.assertIn("Armed", observed[2])
        self.assertIn("Recheck GitHub", observed[2])
        self.assertEqual(len(self.sent), 1)

    def test_deadline_wins_when_a_successful_read_crosses_it(self):
        def read(deadline, active):
            if self.time < 840:
                return snapshot(github())
            self.time = 901
            return snapshot(github(nit=True))
        wait.watch(self.slot, "copilot", read, self.sent.append, clock=lambda: self.time, sleep=self.sleep)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("event=deadline", self.sent[0])

    def test_deadline_after_failed_baseline_no_retry_of_an_ambiguous_delivery(self):
        self.assertEqual(wait.DURATIONS, {"codex": 1800, "copilot": 900, "role": 86400, "merge": 86400})
        def ambiguous(message):
            raise subprocess.TimeoutExpired("codex", 10)
        nonce = self.replay([wait.ReadFailure("GitHub timeout")], send=ambiguous)
        self.assertEqual((self.time, self.reads), (900, list(range(0, 900, 60))))
        self.assertEqual(len(self.sent), 1)
        self.assertIn("deadline", self.sent[0])
        self.assertIn("GitHub timeout x15", self.sent[0])
        receipt = json.loads(self.slot.receipt(nonce).read_text())
        self.assertIn("timeout", receipt["outcome"])
        self.slot.deliver(nonce, "copilot", "deadline", {}, self.sent.append)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.slot.stop(nonce), "deadline")

    def test_replacing_a_waiter_during_a_read_fences_its_delivery(self):
        replacement = []
        def read(deadline, active):
            replacement.append(self.slot.start())
            return {"state": "MERGED"}
        old = wait.watch(self.slot, "merge", read, self.sent.append)
        self.assertNotEqual(old, replacement[0])
        self.assertEqual(self.sent, [])
        self.assertEqual(self.slot.stop(old), "late or duplicate")
        self.assertEqual(self.slot.current(), replacement[0])
        self.assertEqual(self.slot.stop(), "stopped")
        self.assertEqual(self.slot.current(), "")

    def test_late_delivered_nonce_does_not_cancel_new_waiter(self):
        old = self.replay([{"state": "CLOSED"}])
        fresh = self.slot.start()
        self.assertEqual(self.slot.stop(old), "late or duplicate")
        self.assertEqual(self.slot.current(), fresh)
