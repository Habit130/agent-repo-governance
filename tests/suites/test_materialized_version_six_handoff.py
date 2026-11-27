"""Run the summary writer's read-only recheck in a rendered repository (#296, #334)."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import support
from materialized_version_support import VersionThreeRendered
from standins import environment


class VersionSixHandoffRecheck(VersionThreeRendered):
    VERSION = 6
    repository = "Habit130/tally"
    script = ".github/governance/handoff_recheck.py"

    def setUp(self):
        super().setUp()
        support.init_repo(self.dest)
        support.git(self.dest, "add", ".")
        support.git(self.dest, "commit", "-qm", "Adopt policy")
        self.base = support.git(self.dest, "rev-parse", "HEAD").strip()
        support.git(self.dest, "checkout", "-qb", "topic")
        support.write_tree(self.dest, {"notes.txt": "Edited\n"})
        support.git(self.dest, "add", ".")
        support.git(self.dest, "commit", "-qm", "Edit notes")
        self.head = support.git(self.dest, "rev-parse", "HEAD").strip()
        support.git(self.dest, "checkout", "-q", "main")
        self.recording = self.path("reads.json")
        self.remote = {"id": 123, "full_name": self.repository, "default_branch": "main",
                       "owner": {"login": "Habit130"}}
        fixture = Path(support.FIXTURES, "generator", "v6-handoff-recheck.json")
        self.fixture = json.loads(fixture.read_text())
        self.checks = self.fixture["checks"]
        self.pull = dict(self.fixture["pull"], base={"ref": "main", "repo": dict(self.remote)},
                         head={"sha": self.head})
        self.tip = {"ref": "refs/heads/main", "object": {"type": "commit", "sha": self.base}}

    def run_helper(self, mode="judge", receipt="", number=17, last_pull=None):
        prefix = "repos/" + self.repository
        reads = [
            (["api", prefix], self.remote),
            (["api", prefix + "/git/ref/heads/main"], self.tip),
            (["api", prefix + "/pulls/" + str(number)], self.pull),
        ]
        reads.append((["pr", "checks", str(number), "--repo", self.repository, "--required",
                       "--json", "name,state"], self.checks))
        calls = [{"args": args, "stdout": json.dumps(value)} for args, value in reads]
        if last_pull is not None:
            calls[2]["once"] = True
            calls.append({"args": reads[2][0], "stdout": json.dumps(last_pull)})
        with open(self.recording, "w") as handle:
            json.dump({"tool": "gh", "calls": calls}, handle)
        scratch = tempfile.mkdtemp(dir=self.tmp)
        env = environment.environment(scratch, self.recording, base=support.isolated_env())
        result = subprocess.run([sys.executable, self.script, mode, str(number), self.head],
                                cwd=self.dest, env=env, input=receipt, capture_output=True, text=True)
        for call in environment.read_log(scratch):
            self.assertIn(call["args"], [args for args, _ in reads])
        return result

    def test_stable_judgment_identifies_the_remote_pr_and_policy(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        for key, value in {"repository": self.repository, "pr": 17, "target": "main",
                           "base": self.base, "head": self.head, "outcome": "pass"}.items():
            self.assertEqual(receipt[key], value)
        self.assertRegex(receipt["metadata"], r"^[0-9a-f]{64}$")
        self.assertNotIn(self.pull["body"], result.stdout)

    def test_confirmation_compares_the_pr_and_requires_all_checks(self):
        receipt = self.run_helper().stdout
        confirmed = self.run_helper("confirm", receipt)
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        self.assertEqual(confirmed.stdout, receipt)
        for rows in (self.checks[:1], self.checks[1:],
                     [self.checks[0], {"name": "test", "state": "FAILURE"}], None):
            with self.subTest(checks=rows):
                self.checks = rows
                held = self.run_helper("confirm", receipt)
                self.assertNotEqual(held.returncode, 0)
                self.assertIn("check", held.stderr.lower())
        self.checks = self.fixture["checks"]
        self.assertEqual(self.run_helper("confirm", receipt).returncode, 0)

    def test_shared_head_metadata_state_and_target_changes_hold_the_receipt(self):
        receipt = self.run_helper().stdout
        original = copy.deepcopy(self.pull)
        for field, value in self.fixture["changed_pr"]:
            with self.subTest(field=field, value=value):
                self.pull = copy.deepcopy(original)
                parent = self.pull
                keys = field.split(".")
                for key in keys[:-1]:
                    parent = parent[key]
                parent[keys[-1]] = value
                self.assertNotEqual(self.run_helper("confirm", receipt).returncode, 0)
        self.pull = dict(original, number=18)
        self.assertNotEqual(self.run_helper("confirm", receipt, number=18).returncode, 0)
        fresh = self.run_helper(number=18)
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        self.assertEqual(self.run_helper("confirm", fresh.stdout, number=18).returncode, 0)

    def test_moved_policy_judges_the_same_pr_against_its_new_floor(self):
        previous = self.run_helper()
        self.assertEqual(previous.returncode, 0, previous.stderr)
        path = Path(self.dest, ".github/governance/record.yml")
        path.write_text(path.read_text().replace("confirmed:\n  sensitive_paths:",
                        'confirmed:\n  sensitive_paths:\n    - pattern: "notes.txt"\n      floor: high'))
        support.git(self.dest, "commit", "-qam", "Raise the notes floor")
        self.tip["object"]["sha"] = support.git(self.dest, "rev-parse", "HEAD").strip()
        held = self.run_helper("confirm", previous.stdout)
        self.assertNotEqual(held.returncode, 0)
        self.assertIn("high floor", held.stderr)
        self.assertEqual(json.loads(held.stdout)["outcome"], "fail")
        self.pull["body"] = "Risk: high — notes now have a high floor"
        self.assertNotEqual(self.run_helper("confirm", previous.stdout).returncode, 0)
        new = self.run_helper()
        self.assertEqual(new.returncode, 0, new.stderr)
        self.assertEqual(self.run_helper("confirm", new.stdout).returncode, 0)

    def test_unreadable_evidence_or_unverified_checkout_holds_handoff(self):
        receipt = self.run_helper().stdout
        for incomplete in ("", "unreadable", '{"outcome":"pass"}'):
            self.assertNotEqual(self.run_helper("confirm", incomplete).returncode, 0)
        self.tip["object"]["sha"] = self.head
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.tip["object"]["sha"] = self.base
        pull = self.pull
        self.pull = None
        self.assertNotEqual(self.run_helper("confirm", receipt).returncode, 0)
        self.pull = pull
        support.write_tree(self.dest, {"local.txt": "untracked"})
        self.assertNotEqual(self.run_helper().returncode, 0)

    def test_summary_writer_routes_affected_uncertain_unaffected_and_initialize(self):
        review = self.text("docs/agents/review.md")
        section = review.split("### The merge handoff", 1)[1]
        for phrase in ("remained open across an Upgrade", "policy the gate reads",
                       "applicability is uncertain", "unaffected PR", "Initialize",
                       "policy already adopted on its base", "git ls-remote", self.script + " judge",
                       self.script + " confirm", "Merge summary", "required checks", "after the comparison"):
            self.assertIn(phrase, " ".join(section.split()))

    def test_change_during_the_last_comparison_withholds_confirmation(self):
        receipt = self.run_helper().stdout
        held = self.run_helper("confirm", receipt, last_pull=dict(self.pull, body="Risk: low — new text"))
        self.assertNotEqual(held.returncode, 0)
        self.assertEqual(held.stdout, "")
        self.assertIn("changed", held.stderr)

    def test_fresh_default_clone_fetches_pr_objects_without_checking_out_the_pr(self):
        origin = self.dest
        self.dest = self.path("clean-default")
        support.git(self.tmp, "clone", "-q", "--no-local", "--single-branch", origin, self.dest)
        missing = subprocess.run(["git", "cat-file", "-e", self.head], cwd=self.dest,
                                 env=support.isolated_env(), capture_output=True)
        self.assertNotEqual(missing.returncode, 0)
        judged = self.run_helper()
        self.assertEqual(judged.returncode, 0, judged.stderr)
        self.assertEqual(support.git(self.dest, "rev-parse", "HEAD").strip(), self.base)
        self.assertEqual(support.git(self.dest, "status", "--porcelain"), "")
