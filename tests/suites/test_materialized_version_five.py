"""Governance model version five, the unpublished draft: rendered policy-text checks."""

import re

from materialized_version_support import VersionThreeRendered, flat, level_three_section, level_two_section  # noqa: F401


class VersionFiveInitializeChecks(VersionThreeRendered):
    """Initialize requirements and Merge summary policy in version 5's review.md."""

    VERSION = 5

    def review(self):
        return flat(self.text("docs/agents/review.md"))

    def test_required_checks_say_the_gate_applies_from_the_first_pr_after_initialize(self):
        text = self.review()
        self.assertIn(
            "Required checks here are the fixed governance gate plus the checks named in the "
            "governance record. The gate is required from the first PR after Initialize. An "
            "Initialize PR, whose base has no gate workflow, is judged by the record's confirmed "
            "checks that report on it; its evidence and verification prose state the gate as not "
            "yet applicable.", text)

    def test_before_any_merge_says_the_gate_applies_from_the_first_pr_after_initialize(self):
        text = self.review()
        self.assertIn(
            "**Before any merge:** required checks green (the governance gate from the first PR "
            "after Initialize; an Initialize PR's evidence states it as not yet applicable);", text)

    def test_the_body_edit_repair_sentence_stands(self):
        self.assertIn(
            "A governance gate run after a PR body edit qualifies as repaired only when the edit "
            "corrects the failed gate input, such as its Risk declaration.", self.review())

    def test_the_merge_summary_title_and_reviews_line_are_unchanged_from_version_four(self):
        def header(text):
            return text.split("```text\n## Merge summary: <tier>", 1)[1].split("\n```", 1)[0]
        four = support_four(self)
        self.assertEqual(header(self.text("docs/agents/review.md")), header(four))

    def test_review_omits_the_descriptive_merge_watch_paragraph(self):
        review = self.review()
        self.assertNotIn("Merge watch requires self-verification and the Merge summary at every tier", review)
        self.assertNotIn("This is the Upgrade merge's transition exception.", review)

    def test_both_medium_substitution_rules_require_the_last_enabled_bot(self):
        bullets = self.text("docs/agents/review.md").split("\n- ")
        condition = ("`no-provider(none)` or `unavailable(<last enabled bot>)`, the last enabled bot "
                     "in the base record's ordered list.")
        for opening in ("**No bot left at medium.**", "At medium a substituting Reviewer"):
            with self.subTest(statement=opening):
                matches = [flat(bullet) for bullet in bullets if bullet.startswith(opening)]
                self.assertEqual(len(matches), 1)
                self.assertIn(condition, matches[0])

    def test_summary_examples_read_with_the_version_five_parser(self):
        from test_merge_watch import watch_v5

        review = self.text("docs/agents/review.md")
        examples = re.findall(
            r"^[ \t]*## Merge summary: (low|medium|high) at [0-9a-f]{7}\n[ \t]*(Required reviews: [^\n]+)",
            review, re.MULTILINE)
        self.assertEqual(len(examples), 3)
        for tier, line in examples:
            self.assertIsNotNone(watch_v5.parse_reviews(line, tier), line)


def support_four(case):
    """Version 4's review.md, read from the store."""
    import os
    import support
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "generator", "govern-repository", "store", "4", "templates",
                        "docs", "agents", "review.md")
    return support.read_text(path)


class VersionFivePureRevert(VersionThreeRendered):
    """#206: the pure-revert rule in version 5's builder.md."""

    VERSION = 5

    def pure_reverts(self):
        return flat(level_two_section(self.text("docs/agents/builder.md"), "## Pure reverts", "builder.md"))

    def test_a_pure_revert_is_confirmed_by_git_and_by_a_merged_prs_squash_commit(self):
        self.assertIn(
            "The gate confirms a pure revert only when the commit landed under governance, its "
            "parent holding the governance record, the revert's recomputed tree equals yours, and "
            "GitHub shows a PR merged into the default branch whose squash commit it is. Once "
            "confirmed, it takes the low path, even on sensitive paths. When GitHub shows no such "
            "PR or can't be read, the revert is unconfirmed and tiered as usual; that alone never "
            "fails the gate.", self.pure_reverts())
        self.assertNotIn("any doubt", self.pure_reverts())

    def test_the_definition_names_a_merged_prs_squash_commit_on_the_default_branch(self):
        self.assertIn(
            "A pure revert exactly undoes one merged PR's squash commit on the default branch.",
            self.pure_reverts())

    def test_version_fours_sentence_on_the_parent_holding_the_record_is_gone(self):
        self.assertNotIn("The gate confirms only a commit that landed under governance", self.pure_reverts())
