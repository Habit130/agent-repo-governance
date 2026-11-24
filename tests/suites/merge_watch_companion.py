"""Ticket #262: the conditional medium Reviewer, at the qualified Copilot push entry."""

import json
from pathlib import Path

from merge_watch_history import EARLY, LATE, RecordedMerge, load_v4_case_for_v5
from merge_watch_push import case_file
import support


class CompanionReviewer(RecordedMerge):
    def setUp(self):
        super().setUp()
        self.change = case_file("v5/companion-change.json")["comparison"]
        self.api[self.change_path] = self.change
        self.declare("medium", "bot-1=clear(copilot)")

    def test_each_missing_witness_is_named(self):
        self.replay(missing=("merge-summary",))
        self.declare("medium", "bot-1=clear(copilot)", "reviewer=clear")
        self.replay()
        self.statuses[0]["created_at"] = LATE
        self.replay(missing=("reviewer",))
        self.statuses.clear()
        self.replay(missing=("reviewer",))
        self.declare("medium", "bot-1=clear(copilot)")
        self.replay(missing=("reviewer", "merge-summary"))
        self.declare("medium", "bot-1=clear(copilot)", "reviewer=waived")
        self.comments.append(self.waiver("reviewer"))
        self.replay(missing=("reviewer", "merge-summary"))

    def test_qualified_files_follow_the_v5_manifest(self):
        manifest = json.loads(Path(support.REAL_STORE, "5", "manifest.json").read_text())
        for entry in manifest["templates"]:
            with self.subTest(path=entry["path"]):
                status = "removed" if entry["class"] == "record" else "added"
                self.change["files"] = [{"status": status, "filename": entry["path"]}]
                self.replay(missing=() if entry["class"] == "skeleton" else ("merge-summary",))

    def test_removed_fixed_file_and_either_side_of_instruction_rename(self):
        for row in (
            {"status": "removed", "filename": "docs/agents/review.md"},
            {"status": "renamed", "previous_filename": ".claude/CLAUDE.md", "filename": "guide.md"},
            {"status": "renamed", "previous_filename": "guide.md", "filename": "AGENTS.md"},
            {"status": "modified", "filename": "AGENTS.md",
             "patch": "@@ -100 +100 @@\n-old repository-owned note\n+new repository-owned note"},
        ):
            with self.subTest(row=row):
                self.change["files"] = [row]
                self.replay(missing=("merge-summary",))

    def test_sensitive_repository_owned_files_and_confirmed_values(self):
        self.change["files"] = [{"status": "modified", "filename": ".github/workflows/ci.yml"},
                                {"status": "modified", "filename": ".github/governance/record.yml"}]
        merged = self.record_path.replace(self.parent, self.squash)
        self.api[merged] = self.record.replace('    - "codex"\n', "")
        self.replay()
        self.api[merged] = self.record.replace("HistoricalAgent", "NewAgent")
        self.replay(missing=("merge-summary",))
        self.api[merged] = self.record.replace("confirmed:\n", "")
        self.replay(missing=("merge-summary",))
        self.errors[merged] = '{"message":"could not read file"}'
        self.declare("medium", "bot-1=fallback(codex)")
        self.replay(missing=("bot-1",), incomplete="merged change")

    def test_only_historical_enabled_completions_count_regardless_of_slot_claim(self):
        marker = {"code_review": {"commit_sha": self.head, "status": "completed"}}
        codex = {"user": {"login": "chatgpt-codex-connector[bot]"}, "created_at": EARLY,
                 "updated_at": EARLY, "body": f"<!-- codex-review-state:v1 {json.dumps(marker)} -->"}
        self.comments.append(codex)
        self.statuses.clear()
        self.replay()
        self.api[self.record_path] = self.record.replace('    - "codex"\n', "")
        self.replay(missing=("reviewer", "merge-summary"))
        self.api[self.record_path] = self.record
        codex.update(created_at=LATE, updated_at=LATE)
        self.declare("medium", "bot-1=fallback(codex)")
        self.replay(missing=("bot-1", "reviewer", "merge-summary"))
        self.review["submitted_at"] = LATE
        self.replay(missing=("bot-1",))

    def test_upgrade_and_following_merge_use_their_respective_parent_policies(self):
        self.statuses.clear()
        # Place the published v4 Copilot fallback immediately before the qualified v5 merge.
        upgrade = load_v4_case_for_v5("medium-fallback.json")
        before = upgrade["event"]["before"]
        answers = json.dumps(upgrade["github"]).replace(upgrade["event"]["after"], self.parent)
        self.api.update(json.loads(answers.replace("Habit130/tally", self.repo)))
        self.api[f"{self.prefix}/commits/{self.parent}/pulls"][0]["merged_at"] = EARLY
        self.api[f"{self.prefix}/compare/{before}...{self.parent}"] = {
            "base_commit": {"sha": before}, "total_commits": 1, "commits": [{"sha": self.parent}],
            "files": [{"status": "modified", "filename": "AGENTS.md"}],
        }
        self.event["before"] = before
        self.event["commits"].insert(0, {"id": self.parent})
        self.replay(missing=("reviewer", "merge-summary"))

    def test_incomplete_change_keeps_the_proven_slot_miss(self):
        self.declare("medium", "bot-1=fallback(codex)")
        self.statuses.clear()
        for files in (None, [{"status": "renamed", "filename": "ordinary.md"}],
                      [{"status": "modified", "filename": f"src/{n}"} for n in range(300)]):
            with self.subTest(size=len(files) if files else None):
                self.change["files"] = files
                self.replay(missing=("bot-1",), incomplete="merged change")
        self.change["files"][-1]["filename"] = "AGENTS.md"
        self.replay(missing=("bot-1", "reviewer", "merge-summary"))
        self.change["commits"][0]["sha"] = self.head
        self.replay(missing=("bot-1",), incomplete="merged change")

    def test_incomplete_provider_or_status_keeps_independent_misses(self):
        self.declare("medium", "bot-1=fallback(codex)")
        self.review.pop("submitted_at")
        self.replay(missing=("bot-1",), incomplete="submitted_at")
        self.review["submitted_at"] = EARLY
        self.statuses[0].pop("state")
        self.replay(missing=("bot-1", "merge-summary"), incomplete="status state")
        codex = {"user": {"login": "chatgpt-codex-connector[bot]"}, "created_at": EARLY,
                 "updated_at": LATE, "body": "edited after merge"}
        self.comments.append(codex)
        self.declare("medium", "bot-1=clear(copilot)", "reviewer=clear")
        self.statuses.clear()
        self.replay(missing=("reviewer",))
        self.declare("medium", "bot-1=clear(copilot)")
        self.summary["body"] = self.summary["body"].replace("self-verification=clear", "self-verification=waived")
        self.replay(missing=("self-verification",), incomplete="pre-edit content")

    def test_known_nonqualifying_change_supersedes_uncertain_optional_bot(self):
        self.change["files"] = [{"filename": "README.md", "status": "modified"}]
        self.comments.append({"user": {"login": "chatgpt-codex-connector[bot]"}, "created_at": EARLY,
                              "updated_at": LATE, "body": "edited after merge"})
        self.replay()
        self.change["files"][0]["filename"] = "AGENTS.md"
        self.review["state"] = "PENDING"
        self.declare("medium", "bot-1=no-provider(none)", "reviewer=clear")
        self.replay()

    def test_unknown_change_does_not_affect_proven_substitution(self):
        self.declare("medium", "bot-1=no-provider(none)", "reviewer=clear")
        self.errors[self.change_path] = '{"message":"comparison unavailable"}'
        self.review["state"] = "PENDING"
        self.replay()
        self.declare("medium", "bot-1=waived(copilot)")
        self.comments.append(self.waiver("bot-1"))
        self.replay()

    def test_optional_provider_is_complete_despite_an_uncertain_sibling(self):
        self.declare("medium", "bot-1=waived(copilot)")
        self.comments.append(self.waiver("bot-1"))
        malformed = dict(self.review)
        del malformed["submitted_at"]
        self.api[f"{self.prefix}/pulls/54/reviews"].append(malformed)
        self.replay(missing=("merge-summary",))

    def test_quota_stop_preserves_already_established_misses_on_this_merge(self):
        self.declare("medium", "bot-1=clear(copilot)")
        self.summary["body"] = self.summary["body"].replace("self-verification=clear", "self-verification=waived")
        self.comments.append({"user": {"login": "chatgpt-codex-connector[bot]"}, "created_at": EARLY,
                              "updated_at": LATE, "body": "edited after merge"})
        self.replay(missing=("self-verification",), rate_limit=self.change_path, incomplete="rate limited")
        self.comments.pop()
        self.replay(missing=("self-verification", "merge-summary"),
                    rate_limit=f"{self.prefix}/commits/{self.head}/statuses", incomplete="rate limited")
