"""Governance model version five, the unpublished draft: rendered policy-text checks."""

import json
import os
import re
import shlex
import subprocess
import tempfile
from textwrap import dedent

from materialized_version_support import VersionThreeRendered, flat, level_three_section, level_two_section


class VersionFiveInitializeChecks(VersionThreeRendered):
    """Initialize requirements, Merge summary policy, and Planner dispatch in version 5."""

    VERSION = 5

    def review(self):
        return flat(self.text("docs/agents/review.md"))

    def on_the_pr(self):
        return self.text("docs/agents/review.md").split("\n### On the PR\n")[1].split("\n### In the terminal\n")[0]

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

    def test_the_writer_names_the_full_head_and_judges_security_from_the_change(self):
        section = self.on_the_pr()
        template = section.split("```text\n", 1)[1].split("\n```", 1)[0]
        self.assertEqual(template.splitlines(), [
            "## Merge summary: <tier> at <full head sha>",
            "Required reviews: <kind>=<state>, <kind>=<state>",
            "Security review applies: <yes|no>",
        ])
        self.assertIn("all 40", section)
        self.assertIn("Security review applies: yes", section)
        self.assertIn("Security review applies: no", section)
        self.assertIn("authentication, privacy or secret handling", flat(section))
        for path in ("docs/agents/review.md", "docs/agents/reviewer.md"):
            self.assertNotIn("the tier's reason involves", flat(self.text(path)))

    def test_review_omits_the_descriptive_merge_watch_paragraph(self):
        review = self.review()
        self.assertNotIn("Merge watch requires self-verification and the Merge summary at every tier", review)
        self.assertNotIn("This is the Upgrade merge's transition exception.", review)

    def test_writer_checks_waiver_eligibility_and_omits_unused_optional_slots(self):
        checks = flat(level_three_section(self.text("docs/agents/review.md"), "### Checks first"))
        self.assertIn("required and eligible for a waiver on this PR", checks)
        self.assertIn("At low, omit an unused optional slot.", flat(self.on_the_pr()))

    def test_checks_first_verifies_the_effective_rules_as_the_agent(self):
        import owner_support as ow
        import support
        from standins import environment

        section = level_three_section(self.text("docs/agents/review.md"), "### Checks first")
        commands = re.findall(r"`(python3 [^`]+)`", section)
        self.assertEqual(len(commands), 1, "Checks first must give the writer the read-only command")
        command = shlex.split(commands[0])
        fixtures = os.path.join(support.FIXTURES, "generator")
        with open(os.path.join(fixtures, "v5-effective-branch-rules.json")) as handle:
            fixture = json.load(handle)
        with open(os.path.join(fixtures, fixture["gate_recording"])) as handle:
            gate = json.load(handle)["ruleset"]
        branch = fixture["branch"]
        listed = [{"id": i, "name": name, "target": "branch", "enforcement": "active"}
                  for i, name in ((41, "Gate"), (42, "Merge"), (51, "Other"))]
        for row in fixture["cases"]:
            for visibility in [row["visibility"]] if "visibility" in row else ["PUBLIC", "PRIVATE"]:
                with self.subTest(case=row["name"], visibility=visibility):
                    rules = [dict(rule, ruleset_id=row.get("gate_rule_id", 41)) for rule in gate["rules"]]
                    if "checks" in row:
                        check_rule = next(rule for rule in rules if rule["type"] == "required_status_checks")
                        check_rule["parameters"] = {"required_status_checks": row["checks"]}
                    rules.append({"type": "update", "ruleset_id": row.get("merge_rule_id", 42)})
                    branch_read = ["api", "--paginate", "--slurp", "repos/Habit130/tally/rules/branches/release%2Fcurrent"]
                    response = (ow.http_error(branch_read, row["http_error"], row.get("message", "Unavailable"))
                                if "http_error" in row else ow.ok(branch_read, [rules[:2], rules[2:]]))
                    calls = [
                        ow.ok(["api", "repos/{owner}/{repo}"],
                              {"full_name": "Habit130/tally", "visibility": visibility.lower(), "default_branch": branch}),
                        ow.ok(["api", "--paginate", "--slurp", "repos/Habit130/tally/rulesets?includes_parents=false"],
                              [[dict(listed[0], target=row.get("gate_target", "branch"))], listed[1:]]),
                        response,
                        ow.ok(ow.api("/rulesets/41"), {"conditions": {"ref_name": {
                            "include": row.get("gate_scope", ["~DEFAULT_BRANCH"]), "exclude": []}}}),
                        ow.ok(ow.api("/rulesets/42"), {"conditions": {"ref_name": {
                            "include": ["~DEFAULT_BRANCH"], "exclude": []}}}),
                    ]
                    root = tempfile.mkdtemp(dir=self.tmp)
                    recording = os.path.join(root, "gh.json")
                    with open(recording, "w") as handle:
                        json.dump({"tool": "gh", "calls": calls}, handle)
                    env = environment.environment(os.path.join(root, "scratch"), recording)
                    run = subprocess.run(command, cwd=self.dest, env=env, capture_output=True, text=True)
                    self.assertEqual(run.stderr, "")
                    self.assertEqual(run.returncode, row["exit"], run.stdout)
                    self.assertIn(branch, run.stdout)
                    self.assertIn(visibility.lower(), run.stdout)
                    for evidence in row["evidence"]:
                        self.assertIn(evidence, run.stdout)
                    self.assertEqual("Protection verified" in run.stdout, row["exit"] == 0)

    def test_builder_summaries_report_whether_an_independent_session_ran(self):
        section = flat(level_three_section(self.text("docs/agents/review.md"), "### In the terminal"))
        self.assertIn("state whether a session independent of the Builder reviewed the change", section)
        self.assertIn("At low, the Builder writes the Merge summary", flat(self.text("docs/agents/builder.md")))

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
        from test_merge_watch import load_v4_case_for_v5, watch_v5

        section = self.on_the_pr()
        examples = [dedent(block).strip() for block in re.findall(r"```text\n(.*?)\n *```", section, re.S)
                    if "<tier>" not in block]
        recordings = ("high-one-bot-reviewer", "medium-fallback", "medium-reviewer-no-provider-exhausted-list")
        self.assertEqual(len(examples), len(recordings))
        for body, name in zip(examples, recordings):
            with self.subTest(recording=name):
                case = load_v4_case_for_v5(name + ".json")
                github = case["github"]
                policy = next(path for path in github if "/contents/" in path)
                github[policy] = github[policy].replace("version: 4\n", "version: 5\n")
                comments = next(rows for path, rows in github.items() if path.endswith("/comments"))
                summary, = (c for c in comments if c["body"].startswith("## Merge summary:"))
                summary["body"] = body
                problems = []
                self.assertEqual(watch_v5.decide("push", case["event"], "Habit098", github.__getitem__,
                                                problems=problems), [])
                self.assertEqual(problems, [])

    def test_dispatch_rule_lives_only_in_the_planner(self):
        # #249: separate files and sandboxes did not make the reader and its consumer independent.
        planner = self.text("docs/agents/planner.md")
        tickets = level_two_section(planner, "## Tickets", "planner.md")
        dispatch_plan = tickets.split("\n**The dispatch plan.**", 1)[1]
        rule = (
            "- Read both tickets' acceptance criteria. If one ticket's acceptance test exercises an "
            "interface the other changes, record the ticket changing the interface as a native "
            "blocker of the ticket with the test. Schedule the ticket with the test to start from "
            "the updated default branch after the blocker merges. Otherwise, the tickets may run "
            "together if they share no files or resources. When unsure, schedule one after the other."
        )
        self.assertIn(rule, flat(dispatch_plan))
        self.assertEqual(flat(planner).count(rule), 1)

        handoff = self.text("docs/agents/handoff.md")
        handoff_rule = level_two_section(
            handoff, "## Only the Planner arranges what comes next", "handoff.md")
        self.assertIn(
            "- To decide which start requests are ready together, follow the dispatch plan rule in "
            "`planner.md`, Tickets. Each start request holds one start instruction.",
            flat(handoff_rule))
        examples = level_two_section(handoff, "## Examples", "handoff.md")
        self.assertIn("2. #42，按派发计划与 #41 并行。", examples.splitlines())
        self.assertNotIn("native blocker of the ticket with the test", flat(handoff))
        self.assertNotIn("no shared files", flat(handoff))
        self.assertNotIn("没有共享文件或资源", handoff)


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
