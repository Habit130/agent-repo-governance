"""Version six's Checks first instructions and effective protection audit."""

from branch_rules_recording import replay_branch_rules
from materialized_version_support import VersionThreeRendered, flat, level_three_section


class VersionSixProtectionAudit(VersionThreeRendered):
    VERSION = 6

    def test_gate_has_every_confirmed_check_from_the_default_branch(self):
        replay_branch_rules(self, "v6-effective-branch-rules.json")

    def test_existing_effective_branch_rules_cases_keep_their_verdicts(self):
        replay_branch_rules(self, "v5-effective-branch-rules.json", confirmed_checks=["test"])

    def test_checks_first_explains_publishers_and_the_remedy_for_missing_checks(self):
        review = level_three_section(self.text("docs/agents/review.md"), "### Checks first")
        step_three, step_four = review.split("\n3. ", 1)[1].split("\n4. ", 1)
        self.assertIn(
            "Confirmed product checks are required by name, from any publisher, and an owner-script "
            "rerun replaces a publisher binding added by hand.", flat(step_three))
        self.assertNotIn("Product checks retain their configured publishers", step_three)
        self.assertIn("missing confirmed check or wrong gate publisher, have habit rerun the owner script",
                      flat(step_four))
