"""Governance model version four: rendered policy-text checks."""

import os
import re

import support
from materialized_version_support import (
    VersionThreeRendered, budget_failures, flat, level_three_section, level_two_section,
)


class VersionFourSkillInvocations(VersionThreeRendered):
    """#172: rendered instructions only; no check of messages or model behavior."""

    VERSION = 4

    def test_start_instructions_separate_habits_invocation_from_session_skills(self):
        habit_skills = {"to-spec", "to-tickets", "triage", "wayfinder", "retro", "implement-spec"}
        instructions = []
        for root, _, files in os.walk(self.dest):
            for name in files:
                if name.endswith(".md"):
                    text = support.read_text(os.path.join(root, name))
                    instructions.extend(re.findall(r"Role: [^`\n]+?Skills: ([^.]+)\.", flat(text)))
        self.assertTrue(instructions)
        for skills in instructions:
            self.assertFalse(habit_skills.intersection(s.strip() for s in skills.split(",")), skills)
        for path in ("AGENTS.md", "docs/agents/planner.md", "docs/agents/builder.md"):
            text = flat(self.text(path))
            self.assertIn("habit invokes: implement-spec.", text, path)
            self.assertIn("Role: Builder. Spec: #<n>. Skills: tdd.", text, path)

    def test_harness_translations_limit_one_paste_to_tested_first_messages(self):
        start = flat(level_two_section(self.text("AGENTS.md"), "## How to start", "AGENTS.md"))
        claude = start.split("**Claude Code**:", 1)[1].split("**OpenCode**:", 1)[0]
        self.assertIn("first message", claude)
        self.assertIn("one paste is verified", claude)
        self.assertIn("`/name <arguments>`", claude)
        for harness, following in (("OpenCode", "deepseekharness"), ("deepseekharness", "Codex harness")):
            translation = start.split("**%s**:" % harness, 1)[1].split("**%s**:" % following, 1)[0]
            self.assertIn("One paste is unverified", translation)
            self.assertIn("two-step form", translation)
        codex = start.split("**Codex harness**:", 1)[1]
        for phrase in ("`$name` in both the app and the CLI", "app's first message",
                       "one paste is verified", "CLI one paste is unverified", "two-step form"):
            self.assertIn(phrase, codex)
        self.assertNotIn("`@name`", codex)
        translation = flat(self.text(".claude/CLAUDE.md"))
        for phrase in ("first message", "`/name <arguments>`", "one paste is verified",
                       "terminal argument is unverified", "two-step form"):
            self.assertIn(phrase, translation)

    def test_invocation_rule_is_central_and_requests_route_to_it(self):
        agents = self.text("AGENTS.md")
        talking = level_two_section(agents, "## Talking to habit and to other agents", "AGENTS.md")
        self.assertIn("**User-invoked skills**:", talking)
        rule = flat(talking.split("**User-invoked skills**:", 1)[1].split("\n- ", 1)[0])
        for phrase in ("any message", "explicit action of habit's", "whole invocation line",
                       "arguments", "which session", "stops", "mid-session request",
                       "started for work", "without habit's invocation",
                       "never reads the skill's text to follow it", "replaces the invocation"):
            self.assertIn(phrase, rule)
        for path in ("docs/agents/planner.md", "docs/agents/builder.md", "docs/agents/reviewer.md"):
            skills = flat(level_two_section(self.text(path), "## Skills this role relies on", path))
            self.assertIn("User-invoked skills", skills, path)
            self.assertNotIn("never reads the skill's text", self.text(path), path)
        planner = flat(self.text("docs/agents/planner.md"))
        self.assertIn("Reaching `to-spec`, `to-tickets`, `triage` or `wayfinder` mid-session", planner)
        self.assertIn("habit invokes: retro #<miss>.", planner)
        self.assertIn("canonical form", planner)
        self.assertIn("terminal translation", planner)
        handoff = self.text("docs/agents/handoff.md")
        for section in ("## Three kinds of message", "## A final handoff"):
            self.assertIn("User-invoked skills", level_two_section(handoff, section, "handoff.md"))
        for phrase in ("invocation alone in its own block", "Typing it is habit's reply",
                       "no other words", "本 session", "/to-spec", "$retro #51"):
            self.assertIn(phrase, flat(handoff))



class VersionFourBodyUpdateOrder(VersionThreeRendered):
    """#175: rendered instruction checks, not model behavior or concurrency proof."""

    VERSION = 4

    def test_existing_pr_body_updates_wait_for_each_whole_gate_workflow(self):
        builder = self.text("docs/agents/builder.md")
        steps = flat(level_two_section(builder, "## Steps", "builder.md"))
        self.assertIn("For pushes to an existing PR, follow Syncing and waiting", steps)
        waiting = flat(level_two_section(builder, "## Syncing and waiting", "builder.md"))
        sequence = (
            "After pushing to an existing PR",
            "wait for the current head's active `governance-gate` workflow to complete",
            "A passed gate-judgment step alone is insufficient",
            "Batch the routine PR-body edits for that head",
            "wait for the gate run caused by the edit before handoff",
            "Use that result in the required-check and handoff process",
            "a prior pass does not substitute",
        )
        cursor = 0
        for phrase in sequence:
            position = waiting.find(phrase, cursor)
            self.assertGreaterEqual(position, cursor, phrase)
            cursor = position + len(phrase)

    def test_body_update_wait_preserves_repairs_comments_and_rerun_cause_tracking(self):
        builder = self.text("docs/agents/builder.md")
        waiting = flat(level_two_section(builder, "## Syncing and waiting", "builder.md"))
        for phrase in ("Completion need not be success", "correct a failed gate input",
                       "without first obtaining a successful old run",
                       "Failures, cancellations and unavailable checks",
                       "existing repair and escalation rules", "`review.md`, Rerun-only passes",
                       "ordinary issue or evidence comments", "Other actors' concurrent edits",
                       "Otherwise stop and say what you wait for"):
            self.assertIn(phrase, waiting)
        steps = flat(level_two_section(builder, "## Steps", "builder.md"))
        self.assertIn("update it on every new head before requesting its reviews", steps)
        self.assertIn("keeping every Builder's session mark", steps)
        self.assertIn("rerun-only pass on the head", steps)
        self.assertIn("link an open issue for its cause", steps)
        reruns = flat(level_two_section(self.text("docs/agents/review.md"),
                                       "## Rerun-only passes", "review.md"))
        self.assertIn("An unrelated PR edit is not a repair", reruns)
        self.assertIn("no linked open issue is an Important finding", reruns)



class VersionFourSessionMarks(VersionThreeRendered):
    """#171: the session policy at the existing rendered-text seam, not model behavior."""

    VERSION = 4

    def test_builder_marks_have_one_definition_and_survive_takeover_and_head_updates(self):
        review = self.text("docs/agents/review.md")
        marks = flat(level_two_section(review, "## Session marks", "review.md"))
        for phrase in ("Session: <role> — <harness>, <model>, <vendor> (<source>)",
                       "system prompt", "configuration file", "model's maker",
                       "from the harness", "as habit said", "family", "asks habit",
                       "honest mistakes", "Merge watch and the governance gate do not check"):
            self.assertIn(phrase, marks)
        evidence = flat(level_two_section(review, "## Evidence comment", "review.md"))
        self.assertIn("every Builder session that pushed a commit to the PR", evidence)
        builder = self.text("docs/agents/builder.md")
        takeover = flat(level_two_section(builder, "## Takeover", "builder.md"))
        for phrase in ("adds its own mark", "keeps the earlier ones", "asks habit", "(as habit said)"):
            self.assertIn(phrase, takeover)
        for path in ("docs/agents/builder.md", "docs/agents/reviewer.md"):
            self.assertIn("`review.md`, Session marks", self.text(path))
            self.assertNotIn("Session: <role>", self.text(path))

    def test_high_reviewer_checks_all_builders_before_review_and_on_a_tier_rise(self):
        reviewer = self.text("docs/agents/reviewer.md")
        steps = level_two_section(reviewer, "## Steps", "reviewer.md")
        first = flat(steps.split("2. **Pin the head.**", 1)[0])
        for phrase in ("1. **Check session marks.**", "state your own mark",
                       "At high", "every Builder session that pushed", "missing",
                       "stop before reviewing", "Waiting on habit:",
                       "At medium, record your own mark without comparing vendors"):
            self.assertIn(phrase, first)
        classify = flat(steps.split("4. **Classify the tier**", 1)[1].split("5. **Review in full**", 1)[0])
        self.assertIn("rises to high", classify)
        self.assertIn("post the tier finding", classify)
        self.assertIn("repeat step 1", classify)
        start = flat(level_two_section(reviewer, "## Start", "reviewer.md"))
        self.assertIn("Before reading the diff", start)
        builder = self.text("docs/agents/builder.md")
        handoff = flat(level_two_section(builder, "## The Reviewer handoff", "builder.md"))
        self.assertIn("every Builder mark", handoff)
        for path in ("docs/agents/builder.md", "docs/agents/reviewer.md", "docs/agents/review.md"):
            self.assertNotIn("other than yours", self.text(path))
        minimum = flat(level_two_section(self.text("docs/agents/review.md"), "## Minimum reviews", "review.md"))
        self.assertIn("different from every Builder session", minimum)

    def test_every_new_head_reenters_the_vendor_check_before_the_next_round(self):
        reviewer = self.text("docs/agents/reviewer.md")
        steps = level_two_section(reviewer, "## Steps", "reviewer.md")
        pin = flat(steps.split("2. **Pin the head.**", 1)[1].split("3. **Worktree.**", 1)[0])
        self.assertIn("restart at step 1", pin)
        new_head = flat(level_two_section(reviewer, "## A new head", "reviewer.md"))
        for phrase in ("restart at step 1", "before reviewing", "new Builder marks",
                       "`review.md`'s Rounds", "new Comment review", "new `Reviewer` status"):
            self.assertIn(phrase, new_head)

    def test_same_vendor_waiver_stays_in_waivers_and_fixed_summary_lines_stay_unchanged(self):
        review = self.text("docs/agents/review.md")
        waivers = flat(level_two_section(review, "## Waivers", "review.md"))
        for phrase in ("same-vendor review at high does not meet", "existing `reviewer` waiver",
                       "for that head", "still binds", "`reviewer=waived`",
                       "Builder writes the high-risk report", "on a Builder's vendor"):
            self.assertIn(phrase, waivers)
        self.assertEqual(review.count("same-vendor review at high"), 1)
        # Version 4 intentionally retires the second bot slot from the protocol.
        self.assertNotIn("bot-2", level_three_section(review, "### On the PR"))
        terminal = flat(level_three_section(review, "### In the terminal"))
        self.assertIn("one plain sentence naming each Builder's and the Reviewer's vendor", terminal)

class VersionFourReviewLadder(VersionThreeRendered):
    """#187: rendered policy seam; these assertions do not verify model behavior."""

    VERSION = 4

    def test_one_bot_ladder_and_medium_summary(self):
        review = flat(self.text("docs/agents/review.md"))
        self.assertIn('| Review bot | — | one: `bot-1` | one: `bot-1` |', review)
        self.assertIn('| Merge summary by | Builder | Builder; the Reviewer when one ran |', review)
        self.assertIn('At medium a substituting Reviewer', review)
        self.assertIn('`fallback(<bot>)` at medium and high', review)
        for path in ('AGENTS.md', 'docs/agents/review.md', 'docs/agents/builder.md',
                     'docs/agents/reviewer.md', 'docs/agents/handoff.md', 'docs/agents/issue-tracker.md',
                     '.github/governance/merge_watch.py'):
            self.assertNotIn('bot-2', self.text(path), path)

    def test_substitute_and_copilot_exception_are_explicit(self):
        review = flat(self.text('docs/agents/review.md'))
        for phrase in ('**No bot left at medium.**', 'same-vendor Reviewer session substitutes',
                       '**No bot left at high.**', '**Rejecting below high.**',
                       'first raises the PR to high', 'Reviewer session is required as well',
                       'no session independent of the Builder looked at the change'):
            self.assertIn(phrase, review)
        builder = flat(self.text('docs/agents/builder.md'))
        self.assertIn('At low and medium, when no Reviewer is required and none ran', builder)
        reviewer = flat(self.text('docs/agents/reviewer.md'))
        self.assertIn('at high, or at medium as a substitute', reviewer)

    def test_summary_examples_read_with_the_version_four_parser(self):
        import test_merge_watch as watch_tests
        review = self.text('docs/agents/review.md')
        examples = re.findall(r'## Merge summary: (low|medium|high) at [0-9a-f]{7}\n[ \t]*(Required reviews: [^\n]+)', review)
        self.assertEqual(len(examples), 3)
        for tier, line in examples:
            self.assertIsNotNone(watch_tests.watch_v4.parse_reviews(line, tier), line)


class VersionFourRefresh(VersionThreeRendered):
    """#190: rendered startup rules, not execution or model-behavior evidence."""

    VERSION = 4

    def test_refresh_is_first_for_every_parent_session_and_preserves_stale_work(self):
        start = level_two_section(self.text("AGENTS.md"), "## How to start", "AGENTS.md")
        first = flat(start.split("\n- ", 2)[1])
        for phrase in ("**Refresh first**", "before reading your role's file", "fetch `origin`",
                       "identify its default branch", "clean and on that branch", "fast-forward",
                       "Every session", "no role", "read-only session", "subagent",
                       "parent's tree", "dirty", "another branch", "can't fast-forward",
                       "reach the remote", "leave it untouched", "tell habit",
                       "instruction files from the remote default branch when reachable",
                       "changed an instruction file", "read it again"):
            self.assertIn(phrase, first)
        self.assertIn("docs/agents/planner.md", first)
        self.assertIn("docs/agents/builder.md", first)
        self.assertIn("docs/agents/reviewer.md", first)

    def test_refreshed_policy_stays_within_the_fixed_part_byte_budget(self):
        agents = self.text("AGENTS.md").split("<!-- governance:end -->", 1)[0]
        self.assertEqual(budget_failures((agents + "<!-- governance:end -->\n").encode("utf-8")), [])


class VersionFourPureUpgrade(VersionThreeRendered):
    """#188: released-byte tiering at the approved rendered-policy seam."""

    VERSION = 4

    def test_upgrade_tiers_keep_confirmation_changes_and_other_modes_high(self):
        agents = flat(level_three_section(self.text("AGENTS.md"), "### Risk tiers"))
        medium = agents.split("| medium |", 1)[1].split("| high |", 1)[0]
        high = agents.split("| high |", 1)[1].split("|", 1)[0]
        self.assertIn("pure Upgrade", medium)
        for phrase in ("Initialize", "Repair", "Upgrade", "confirmed value",
                       "required checks", "owner script's target state"):
            self.assertIn(phrase, high)
        self.assertNotIn("; generator output |", agents)

    def test_purity_has_one_definition_and_evidence_states_both_facts(self):
        review = self.text("docs/agents/review.md")
        tier = flat(level_two_section(review, "## The tier", "review.md"))
        definition = ("An Upgrade is pure when exact comparison reports no differences and "
                      "the record's confirmed part is unchanged from the default branch.")
        self.assertIn(definition, tier)
        all_policy = " ".join(self.text(path) for path in (
            "AGENTS.md", "docs/agents/review.md", "docs/agents/builder.md"))
        self.assertEqual(flat(all_policy).count(definition), 1)
        evidence = flat(level_two_section(review, "## Evidence comment", "review.md"))
        self.assertIn("for a pure Upgrade, both facts in The tier's definition", evidence)

    def test_generator_run_tier_follows_the_adopted_default_policy(self):
        skill = flat(support.read_text(os.path.join(
            os.path.dirname(os.path.dirname(support.GOVERN)), "SKILL.md")))
        self.assertNotIn("This run is a high Builder delivery.", skill)
        for phrase in ("Initialize and Repair are high", "An Upgrade takes the tier",
                       "default branch's adopted policy", "Upgrade to version 4 is still high",
                       "declare the run's tier", "not the rendered target version"):
            self.assertIn(phrase, skill)
        self.assertNotIn("as the ticket and `Risk: high`", skill)
