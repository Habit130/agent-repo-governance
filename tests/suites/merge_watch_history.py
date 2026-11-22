"""v5 Merge watch at the rendered workflow entry, using only the recorded GitHub stand-in."""

import json
import os
import re
import shlex
import sys
import subprocess
import tempfile
from pathlib import Path

from materialized_version_support import VersionThreeRendered
from standins import environment
import support


FIXTURE = Path(support.FIXTURES, "merge-watch", "v5", "qualified-copilot.json")
EARLY = "2026-11-10T09:44:00Z"
LATE = "2026-11-10T09:46:00Z"


def supply_historical_fields(case):
    """Give a copy of the trimmed v4 recording pre-merge dates, a parent and linked Actions identity.

    These are synthetic controls for replaying its original review declarations under v5.
    qualified-copilot.json separately retains the observed positive producer fields.
    """
    event, github = case["event"], case["github"]
    repo = event["repository"]["full_name"]
    prefix = "repos/" + repo
    squash = event["after"]
    github[f"{prefix}/git/commits/{squash}"] = {"sha": squash, "parents": [{"sha": event["before"]}]}
    for path, rows in list(github.items()):
        if path.endswith("/comments"):
            for row in rows:
                row.update(created_at=EARLY, updated_at=EARLY)
        elif path.endswith("/reviews"):
            for row in rows:
                row.update(submitted_at=EARLY)
        elif path.endswith("/statuses"):
            for row in rows:
                row.update(created_at=EARLY)
        elif "/check-runs?" in path:
            for row in rows:
                row.update(completed_at=EARLY, id=17, check_suite={"id": 18},
                           details_url=f"https://github.com/{repo}/actions/runs/19/job/17")
                github[f"{prefix}/actions/jobs/17"] = {
                    "id": 17, "run_id": 19, "head_sha": row["head_sha"],
                    "check_run_url": f"https://api.github.com/{prefix}/check-runs/17",
                }
                github[f"{prefix}/actions/runs/19"] = {
                    "id": 19, "check_suite_id": 18, "head_sha": row["head_sha"],
                    "path": "dynamic/agents/copilot-pull-request-reviewer", "event": "dynamic",
                    "actor": {"login": "Copilot"},
                }
    return case


class HistoricalEvidence(VersionThreeRendered):
    VERSION = 5

    def setUp(self):
        super().setUp()
        self.case = json.loads(FIXTURE.read_text())
        self.api = self.case["github"]
        self.event = self.case["event"]
        self.repo = self.event["repository"]["full_name"]
        self.prefix = "repos/" + self.repo
        self.parent = self.event["before"]
        self.squash = self.event["after"]
        self.pr = self.api[f"{self.prefix}/commits/{self.squash}/pulls"][0]
        self.head = self.pr["head"]["sha"]
        self.record_path = f"{self.prefix}/contents/.github/governance/record.yml?ref={self.parent}"
        self.record = self.api[self.record_path]
        self.summary, = self.api[f"{self.prefix}/issues/54/comments"]
        self.statuses = self.api[f"{self.prefix}/commits/{self.head}/statuses"]
        self.review, = self.api[f"{self.prefix}/pulls/54/reviews"]
        self.check, = next(rows for path, rows in self.api.items() if "/check-runs?" in path)
        self.run = self.api[f"{self.prefix}/actions/runs/42792788901"]
        self.comments = self.api[f"{self.prefix}/issues/54/comments"]
        self.errors = {}
        self.unassociated = None

    def replay(self, missing=(), incomplete=None, notes=(), repository=None):
        """Serve the actual gh API shapes, then compare the posted records and workflow exit."""
        calls = []
        for path, value in self.api.items():
            if "/contents/" in path:
                args = ["api", "-H", "Accept: application/vnd.github.raw", path]
                output = value
            elif "/git/commits/" in path or "/actions/" in path:
                args, output = ["api", path], json.dumps(value)
            else:
                paged = path + ("&" if "?" in path else "?") + "per_page=100&page=1"
                args = ["api", paged]
                if "/check-runs?" in path:
                    value = {"check_runs": value, "total_count": len(value)}
                output = json.dumps(value)
            calls.append({"args": args, "stdout": self.errors.get(path, output),
                          "exit": int(path in self.errors)})
        expected = []
        if missing:
            title = "Miss: process miss, missing-review in #54"
            tier = self.pr["body"].split(" — ")[0].split()[-1]
            body = (f"Merged PR: #54\nKind: process miss\nCategory: missing-review\n"
                    f"Observed: Merged head {self.head}, declared {tier}, lacks: {', '.join(missing)}.\n"
                    "Found by: Merge watch\nBug issue: none\n")
            expected.append(dict(title=title, body=body, labels=["miss"]))
        if self.unassociated:
            expected.append({"title": "Miss: process miss, push-without-pr", "labels": ["miss"],
                             "body": ("Merged PR: none\nKind: process miss\nCategory: push-without-pr\n"
                                      f"Observed: Commit {self.unassociated} was pushed to main with no merged PR.\n"
                                      "Found by: Merge watch\nBug issue: none\n")})
        for item in expected:
            calls.append({"args": ["api", "--method", "POST", self.prefix + "/issues", "--input", "-"],
                          "stdin": json.dumps(item, sort_keys=True), "stdout": "{}", "exit": 0})
        with tempfile.TemporaryDirectory(dir=self.tmp) as tmp:
            event, recording = Path(tmp, "event.json"), Path(tmp, "gh.json")
            target = repository or self.repo
            event.write_text(json.dumps(self.event).replace(self.repo, target))
            recording.write_text(json.dumps({"tool": "gh", "calls": calls}).replace(self.repo, target))
            env = environment.environment(tmp, gh_recording=str(recording), base=support.isolated_env())
            env.update(GITHUB_EVENT_NAME="push", GITHUB_EVENT_PATH=str(event), GITHUB_REPOSITORY=target)
            workflow = self.text(".github/workflows/merge-watch.yml")
            command, = re.findall(r"(?m)^        run: (.+)$", workflow)
            executable, *args = shlex.split(command)
            self.assertEqual(executable, "python3")
            result = subprocess.run([sys.executable, *args], cwd=self.dest, env=env,
                                    capture_output=True, text=True)
            log = environment.read_log(tmp)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, int(incomplete is not None), output)
        if incomplete is not None:
            self.assertIn("INCOMPLETE", output)
            self.assertIn(incomplete, output)
            self.assertNotIn("No miss in this push event.", output)
        for note in notes:
            self.assertIn(note, output)
        self.assertEqual([json.loads(call["stdin"]) for call in log if "--method" in call["args"]],
                         expected, output)
        self.assertTrue(all(call["recorded"] for call in log), log)
        return [call["args"] for call in log]

    def test_qualified_review_uses_the_historical_agent(self):
        self.replay()
        checkout = Path(self.dest, ".github/governance/record.yml")
        checkout.write_text("unreadable later checkout\n")
        self.replay()
        self.summary["user"]["login"] = "Habit098"
        self.statuses[0]["creator"]["login"] = "Habit098"
        self.replay(missing=("reviewer", "merge-summary"))

    def test_repository_names_do_not_select_an_api_response_shape(self):
        for name in ("actions", "contents"):
            with self.subTest(name=name):
                self.replay(repository="Habit130/" + name)

    def test_only_the_actual_squash_parent_selects_the_policy(self):
        self.event["before"] = "a" * 40
        unrelated = self.record_path.replace(self.parent, self.event["before"])
        self.api[unrelated] = self.record.replace("HistoricalAgent", "AnotherAgent")
        self.replay()

    def medium_substitution(self):
        self.pr["body"] = "Risk: medium — internal clients"
        self.summary["body"] = (f"## Merge summary: medium at {self.head[:7]}\nRequired reviews: "
                                "self-verification=clear, bot-1=no-provider(none), reviewer=clear")

    def waiver(self, kind):
        return {"user": {"login": "Habit130"}, "created_at": EARLY, "updated_at": EARLY,
                "body": f"Waiver: {kind} at {self.head} — authorized for the fixture"}

    def use_codex(self):
        self.api[self.record_path] = self.record.replace('    - "copilot"\n', "")
        self.summary["body"] = self.summary["body"].replace("clear(copilot)", "clear(codex)")
        marker = {"code_review": {"commit_sha": self.head, "status": "completed"}}
        comment = {"user": {"login": "chatgpt-codex-connector[bot]"}, "created_at": EARLY, "updated_at": EARLY,
                   "body": f"<!-- codex-review-state:v1 {json.dumps(marker)} -->"}
        self.comments.append(comment)
        return comment

    def test_initialize_fallback_only_on_confirmed_absence(self):
        introduced = self.record_path.replace(self.parent, self.squash)
        self.api[introduced] = self.record
        self.errors[self.record_path] = json.dumps({"status": "404", "message": "Not Found"})
        self.replay(notes=("base with no governance record",))
        self.errors[self.record_path] = json.dumps({"status": "404", "message": "No commit found for the ref"})
        calls = self.replay(incomplete="historical record could not be read")
        self.assertFalse(any(introduced in args for args in calls))
        self.errors.clear()
        self.api[self.record_path] = "not a record"
        calls = self.replay(incomplete="invalid historical record")
        self.assertFalse(any(introduced in args for args in calls))

    def test_empty_absent_invalid_and_unknown_policy(self):
        self.medium_substitution()
        empty = self.record.split("  review_bots:")[0] + "  review_bots:\n"
        self.api[self.record_path] = empty
        self.replay()
        self.api[self.record_path] = empty.removesuffix("  review_bots:\n")
        self.replay(incomplete="omits review_bots")
        self.api[self.record_path] = empty + '    - "unrecognized"\n'
        self.replay(incomplete="invalid historical record")
        self.comments.append(self.waiver("bot-1"))
        self.api[self.record_path] = empty.replace("version: 5", "version: 6")
        self.replay(incomplete="unsupported historical version")

    def test_published_transition_and_modern_controls(self):
        self.medium_substitution()
        self.comments.append(self.waiver("reviewer"))
        status = self.statuses.pop()
        for version in (1, 2, 3, 4, 5):
            with self.subTest(version=version):
                base = self.record if version >= 3 else self.record.split("  review_bots:")[0]
                self.api[self.record_path] = base.replace("version: 5", f"version: {version}")
                expected = {1: ("reviewer",), 2: ("reviewer",), 3: (), 4: ("bot-1",), 5: ("bot-1",)}
                self.replay(missing=expected[version])
                self.statuses.append(status)
                self.replay()
                self.statuses.clear()
        self.api[self.record_path] = self.record.replace("version: 5", "version: 3")
        self.comments[-1]["body"] = self.comments[-1]["body"].replace(self.head, "f" * 40)
        self.summary["body"] = self.summary["body"].split("Required reviews:")[0] + "Required reviews: old-bot=done"
        self.replay(missing=("reviewer",), notes=("its review bots follow that version",))

    def test_summary_and_latest_matching_status_on_either_side_of_merge(self):
        self.summary.update(created_at=LATE, updated_at=LATE)
        self.replay(missing=("merge-summary",))
        self.summary.update(created_at=EARLY, updated_at=EARLY)
        self.statuses.insert(0, dict(self.statuses[0], state="failure", created_at=LATE))
        self.replay()
        self.statuses[0]["created_at"] = "2026-11-10T09:44:59Z"
        self.replay(missing=("reviewer",))
        self.statuses[:] = [dict(self.statuses[0], state="success", created_at=LATE)]
        self.replay(missing=("reviewer",))

    def test_waiver_on_either_side_and_pre_edit_content(self):
        self.statuses.clear()
        self.summary["body"] = self.summary["body"].replace("reviewer=clear", "reviewer=waived")
        waiver = self.waiver("reviewer")
        self.comments.append(waiver)
        self.replay()
        waiver.update(created_at=LATE, updated_at=LATE)
        self.replay(missing=("reviewer",))
        waiver.update(created_at=EARLY)
        self.replay(incomplete="pre-edit content")

    def test_codex_comment_on_either_side_and_pre_edit_content(self):
        comment = self.use_codex()
        self.replay()
        comment.update(created_at=LATE, updated_at=LATE)
        self.replay(missing=("bot-1",))
        comment.update(created_at=EARLY)
        self.replay(incomplete="pre-edit content")
        comment.update(updated_at=EARLY)
        del comment["created_at"]
        self.replay(incomplete="created_at")

    def test_edited_summary_cannot_restore_or_supersede_its_earlier_content(self):
        self.comments.append(dict(self.summary, body="body after edit", updated_at=LATE))
        self.replay(incomplete="pre-edit content")

    def test_copilot_submission_and_check_completion_are_independently_bounded(self):
        for row, field in ((self.review, "submitted_at"), (self.check, "completed_at")):
            with self.subTest(field=field):
                original = row[field]
                row[field] = LATE
                self.replay(missing=("bot-1",))
                row[field] = None
                self.replay(incomplete=field)
                row[field] = original
                self.replay()

    def test_copilot_needs_a_recognized_review_and_the_qualified_workflow(self):
        self.review["state"] = "NEW_STATE"
        self.replay(missing=("bot-1",), notes=("unrecognized submitted review state",))
        self.review["state"] = "COMMENTED"
        self.check["app"]["slug"] = "other-app"
        self.replay(missing=("bot-1",))
        self.check["app"]["slug"] = "github-actions"
        self.run["path"] = ".github/workflows/another-workflow.yml"
        self.replay(missing=("bot-1",), notes=("different Actions workflow",))
        self.run["path"] = "dynamic/agents/copilot-pull-request-reviewer"
        self.run["check_suite_id"] += 1
        self.replay(incomplete="ambiguous producer")
        self.run["check_suite_id"] -= 1
        job = self.api[f"{self.prefix}/actions/jobs/129750222497"]
        original = job["check_run_url"]
        job["check_run_url"] = original[:-1] + "9"
        self.replay(incomplete="ambiguous producer")
        job["check_run_url"] = original
        del self.check["details_url"]
        self.replay(incomplete="ambiguous producer")

    def test_malformed_status_leaves_the_independent_bot_miss_observable(self):
        self.api[f"{self.prefix}/pulls/54/reviews"].clear()
        self.statuses[:] = [None]
        self.replay(missing=("bot-1",), incomplete="malformed list member")
        self.statuses.clear()
        self.replay(missing=("bot-1", "reviewer"))

    def test_malformed_review_or_check_does_not_hide_a_missing_reviewer(self):
        self.statuses.clear()
        for path in (f"{self.prefix}/pulls/54/reviews", next(p for p in self.api if "/check-runs?" in p)):
            with self.subTest(path=path):
                original = self.api[path]
                self.api[path] = ["malformed"]
                self.replay(missing=("reviewer",), incomplete="malformed list member")
                self.api[path] = original

    def add_unassociated_commit(self):
        self.unassociated = "c" * 40
        self.event["commits"].append({"id": self.unassociated})
        self.event["after"] = self.unassociated
        self.api[f"{self.prefix}/commits/{self.unassociated}/pulls"] = []

    def test_malformed_comments_or_associations_preserve_an_independent_commit(self):
        self.add_unassociated_commit()
        self.comments[:] = [None]
        self.replay(incomplete="malformed list member")
        self.api[f"{self.prefix}/commits/{self.squash}/pulls"] = [None]
        self.replay(incomplete="malformed list member")

    def test_invalid_merge_time_and_malformed_commit_leave_the_run_incomplete(self):
        self.add_unassociated_commit()
        self.pr["merged_at"] = "not a timestamp"
        self.replay(incomplete="merged_at")
        self.pr["merged_at"] = None
        self.replay(incomplete="merged_at")
        del self.pr["merged_at"]
        self.replay(incomplete="merged_at")
        self.pr["merged_at"] = "2026-11-10T09:45:00Z"
        self.event["commits"].insert(0, None)
        self.replay(incomplete="malformed")

    def test_malformed_open_issue_does_not_hide_an_independent_miss(self):
        self.statuses.clear()
        self.api[f"{self.prefix}/issues?labels=miss&state=open"] = [None]
        self.replay(missing=("reviewer",), incomplete="malformed list member")

    def test_a_newer_known_summary_supersedes_an_older_edited_comment(self):
        self.comments.insert(0, dict(self.summary, body="later edit", updated_at=LATE))
        self.replay()

    def test_unreadable_summary_does_not_hide_a_provably_absent_bot(self):
        self.summary["updated_at"] = LATE
        self.api[f"{self.prefix}/pulls/54/reviews"].clear()
        self.replay(missing=("bot-1",), incomplete="pre-edit content")

    def test_late_rows_with_missing_identity_cannot_affect_the_merge(self):
        self.comments.append({"body": "after merge", "created_at": LATE})
        self.statuses.insert(0, {"context": "Reviewer", "created_at": LATE, "state": "failure"})
        self.replay()
        self.review["submitted_at"] = LATE
        del self.review["is_copilot_code_review"]
        self.replay(missing=("bot-1",))
        self.review.update(submitted_at=EARLY, is_copilot_code_review=True)
        self.check["completed_at"] = LATE
        del self.check["app"]
        self.replay(missing=("bot-1",))

    def test_malformed_associations_cannot_establish_direct_push_or_merged_history(self):
        self.add_unassociated_commit()
        pulls = self.api[f"{self.prefix}/commits/{self.squash}/pulls"]
        candidates = [
            {"merged_at": None},
            dict(self.pr, merge_commit_sha=""),
            dict(self.pr, merge_commit_sha="1" * 40, merged_at=""),
            dict(self.pr, merge_commit_sha="1" * 40, merged_at="unknown"),
        ]
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                pulls[:] = [candidate]
                self.replay(incomplete="association")
        pulls[:] = [dict(self.pr, merge_commit_sha="1" * 40)]
        self.replay()
