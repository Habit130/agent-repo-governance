"""Ticket #234: judge v5 Merge summaries through the rendered push workflow."""

import json

from merge_watch_history import EARLY, RecordedMerge


class SummaryDeclarations(RecordedMerge):
    def test_optional_reviews_need_their_own_evidence_only_when_declared(self):
        reviewer, = self.statuses
        for tier in ("low", "medium"):
            with self.subTest(tier=tier):
                self.statuses[:] = [reviewer]
                self.review["state"] = "COMMENTED"
                self.declare(tier, "bot-1=clear(copilot)", "reviewer=clear")
                self.replay()
                self.statuses.clear()
                self.replay(missing=("reviewer",))
                self.declare(tier, "bot-1=clear(copilot)")
                self.replay()
                self.review["state"] = "PENDING"
                self.replay(missing=("bot-1",))
        self.declare("low")
        self.statuses.clear()
        self.review["state"] = "PENDING"
        self.replay()

    def test_a_waiver_cannot_confirm_a_completion_or_a_disabled_provider(self):
        self.api[self.record_path] = self.record.replace('    - "codex"\n', "")
        self.statuses.clear()
        self.review["state"] = "PENDING"
        self.comments.extend([self.waiver("bot-1"), self.waiver("reviewer")])
        self.declare("medium", "bot-1=clear(copilot)", "reviewer=clear")
        self.replay(missing=("bot-1", "reviewer"))
        self.declare("medium", "bot-1=waived(codex)", "reviewer=waived")
        self.replay(missing=("bot-1",))
        self.declare("medium", "bot-1=waived(copilot)", "reviewer=waived")
        self.replay()
        self.comments.pop()
        self.replay(missing=("reviewer",))
        self.comments.pop()
        self.replay(missing=("bot-1", "reviewer"))

    def test_slot_waiver_does_not_fill_a_slot_declared_exhausted(self):
        self.comments.append(self.waiver("bot-1"))
        self.review["state"] = "PENDING"
        self.declare("high", "bot-1=unavailable(codex)", "reviewer=clear")
        self.summary["body"] += "\nSecurity review applies: no"
        self.replay(missing=("bot-1",))

        self.statuses.clear()
        for slot in ("unavailable(codex)", "no-provider(none)"):
            with self.subTest(slot=slot):
                self.declare("medium", "bot-1=" + slot)
                self.replay(missing=("bot-1",))
        self.declare("medium", "bot-1=waived(none)")
        self.replay()

        # The published v4 rule credits the slot waiver with the same exhaustion declaration.
        self.api[self.record_path] = self.record.replace("version: 5", "version: 4")
        self.declare("medium", "bot-1=no-provider(none)")
        self.summary["body"] = self.summary["body"].replace(self.head, self.head[:7], 1)
        self.replay()

    def test_low_accepts_an_omitted_slot_and_reports_either_exhaustion_declaration(self):
        self.review["state"] = "PENDING"
        self.declare("low")
        self.replay()
        for slot in ("unavailable(codex)", "no-provider(none)"):
            with self.subTest(slot=slot):
                self.declare("low", "bot-1=" + slot)
                self.replay(missing=("bot-1",))

    def test_high_requires_the_writers_decision_and_the_applicable_security_row(self):
        for decision, security, waiver, missing in (
            ("no", None, False, ()),
            ("no", "waived", True, ("security",)),
            ("no", "clear", False, ()),
            ("yes", "clear", False, ()),
            ("yes", "waived", True, ()),
            ("yes", "waived", False, ("security",)),
            ("yes", None, False, ("security", "merge-summary")),
            ("yes", None, True, ("merge-summary",)),
            (None, "clear", False, ("merge-summary",)),
            ("unknown", None, False, ("merge-summary",)),
        ):
            with self.subTest(decision=decision, security=security, waiver=waiver):
                self.declare("high", "bot-1=clear(copilot)", "reviewer=clear")
                if security:
                    self.summary["body"] += ", security=" + security
                if decision:
                    self.summary["body"] += "\nSecurity review applies: " + decision
                self.comments[:] = [self.summary, self.waiver("security")] if waiver else [self.summary]
                self.replay(missing=missing)

    def test_medium_substitution_requires_the_final_provider_and_the_historical_reviewer(self):
        for slot, expected in (("unavailable(copilot)", ("bot-1",)),
                               ("unavailable(codex)", ()), ("no-provider(none)", ())):
            with self.subTest(slot=slot):
                self.declare("medium", "bot-1=" + slot, "reviewer=clear")
                self.replay(missing=expected)
        self.statuses[0]["creator"]["login"] = "AnotherAgent"
        self.replay(missing=("bot-1", "reviewer"))

    def test_an_omitted_required_kind_does_not_hide_a_separate_declaration(self):
        self.declare("medium", "reviewer=clear")
        self.statuses.clear()
        self.replay(missing=("reviewer", "merge-summary"))


class VersionSixConsolidatedDeclarations(RecordedMerge):
    VERSION = 6

    def test_incomplete_line_still_checks_the_declared_reviewer(self):
        self.api[self.record_path] = self.record.replace("version: 5", "version: 6")
        reviewer, = self.statuses
        for slot, lacks_summary in (
            ("bot-1=clear(copilot)", ()),
            (None, ("merge-summary",)),
        ):
            reviews = ("reviewer=clear",) if slot is None else (slot, "reviewer=clear")
            self.declare("medium", *reviews)
            for status, lacks_reviewer in (([reviewer], ()), ([], ("reviewer",))):
                with self.subTest(bot_slot=slot, reviewer_attested=bool(status)):
                    self.statuses[:] = status
                    self.replay(missing=lacks_reviewer + lacks_summary)

    def test_codex_completion_counts_without_a_request_comment_on_the_head(self):
        self.api[self.record_path] = self.record.replace("version: 5", "version: 6").replace('    - "copilot"\n', "")
        self.declare("medium", "bot-1=clear(codex)")
        completion = {"user": {"login": "chatgpt-codex-connector[bot]"}, "created_at": EARLY, "updated_at": EARLY}
        self.comments.append(completion)
        for sha, status, missing in (
            (self.head, "completed", ()),
            ("f" * 40, "completed", ("bot-1",)),
            (self.head, "in_progress", ("bot-1",)),
        ):
            with self.subTest(head=sha, status=status):
                marker = {"code_review": {"commit_sha": sha, "status": status}}
                completion["body"] = f"<!-- codex-review-state:v1 {json.dumps(marker)} -->"
                self.replay(missing=missing)
