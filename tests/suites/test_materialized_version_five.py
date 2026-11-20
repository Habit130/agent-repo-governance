"""Governance model version five, the unpublished draft: rendered policy-text checks."""

from materialized_version_support import VersionThreeRendered, flat, level_three_section  # noqa: F401


class VersionFiveInitializeChecks(VersionThreeRendered):
    """#207: the checks an Initialize PR is judged by, in version 5's review.md."""

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
