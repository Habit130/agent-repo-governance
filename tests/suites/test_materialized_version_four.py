"""Governance model version four: rendered policy-text checks."""

import os
import re

import support
from materialized_version_support import (
    VersionThreeRendered, flat, level_three_section, level_two_section,
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
        # The machine-read summary protocol remains exactly the released version's.
        old = support.read_text(os.path.join(support.REAL_STORE, "3", "templates", "docs/agents/review.md"))
        self.assertEqual(level_three_section(review, "### On the PR"),
                         level_three_section(old, "### On the PR"))
        terminal = flat(level_three_section(review, "### In the terminal"))
        self.assertIn("one plain sentence naming each Builder's and the Reviewer's vendor", terminal)
