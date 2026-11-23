"""Ticket #234: judge v5 Merge summaries through the rendered push workflow."""

from merge_watch_history import RecordedMerge


class SummaryDeclarations(RecordedMerge):
    def declare(self, tier, *reviews):
        self.pr["body"] = f"Risk: {tier} — sandbox control"
        self.summary["body"] = (f"## Merge summary: {tier} at {self.head}\nRequired reviews: "
                                + ", ".join(("self-verification=clear", *reviews)))

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
