"""Materialized version 1 (#41 seam 3, through #44's rendering and exact comparison).

Version 1 renders from the real store into the tally sample repository, then exact
comparison runs on the result. #41's template tickets add their seam-3 checks here.
"""

import os
import json
import posixpath
import re
import unittest

import materialized
import parsers
import support
from govlib import record, render, store
from test_record import DEFAULT_PATTERNS, RECORD


class VersionTwoPolicy(support.TempDirCase):
    """#122 rendered instructions at the existing materialization seam."""

    def test_gate_and_record_templates_keep_the_existing_trust_boundary(self):
        for path in ("dot-github/governance/gate.py", "dot-github/workflows/governance-gate.yml",
                     "dot-github/governance/record.yml"):
            self.assertEqual(support.read_text(os.path.join(support.REAL_STORE, "2", "templates", path)),
                             support.read_text(os.path.join(support.REAL_STORE, "1", "templates", path)), path)

    def test_upgrade_preserves_repository_policy_and_confirmed_values(self):
        dest = materialized.tally_worktree(self.tmp)
        confirmed = self.path("confirmed.json")
        values = materialized.tally_fixture()["confirmed"]
        with open(confirmed, "w") as handle:
            json.dump(values, handle)
        args = ["--dest", dest, "--repository", "Habit130/tally", "--default-branch", "main"]
        code, facts = support.govern(["render", "--version", "1", "--confirmed", confirmed] + args)
        self.assertEqual(code, 0, facts)
        policy = "\nRepository-owned rule: hosted builds must use the dedicated command.\n"
        agents = os.path.join(dest, "AGENTS.md")
        with open(agents, "a") as handle:
            handle.write(policy)
        build = os.path.join(dest, "docs/agents/build.md")
        evidence = "# Repository runbook\n\nRelease-only CI; exact merged-commit smoke is local.\n"
        with open(build, "w") as handle:
            handle.write(evidence)
        code, facts = support.govern(["render", "--version", "2", "--allow-unreleased", "--confirmed", confirmed] + args)
        self.assertEqual(code, 0, facts)
        self.assertTrue(support.read_text(agents).endswith(policy))
        self.assertEqual(support.read_text(build), evidence)
        with open(os.path.join(dest, RECORD), "rb") as handle:
            self.assertEqual(record.parse(handle.read())["confirmed"], values)
        code, facts = support.govern([
            "compare", "--worktree", dest, "--version", "2", "--allow-unreleased",
            "--repository", "Habit130/tally", "--default-branch", "main",
        ])
        self.assertEqual(code, 0, facts)
        self.assertEqual(facts["differences"], [])

    def test_product_smoke_is_bound_to_the_merged_commit(self):
        fixture = materialized.tally_fixture()
        confirmed = self.path("confirmed.json")
        with open(confirmed, "w") as handle:
            json.dump(fixture["confirmed"], handle)
        dest = self.path("rendered")
        code, facts = support.govern([
            "render", "--version", "2", "--allow-unreleased", "--dest", dest,
            "--repository", fixture["repository"], "--default-branch", fixture["default_branch"],
            "--confirmed", confirmed,
        ])
        self.assertEqual(code, 0, facts)
        builder = support.read_text(os.path.join(dest, "docs/agents/builder.md"))
        self.assertIn("exact merged commit", builder)
        self.assertIn("delivery incomplete", builder)
        self.assertIn("Governance audits", builder)

    def test_label_descriptions_are_creation_defaults_not_retention_requirements(self):
        dest = self.path("rendered")
        confirmed = self.path("confirmed.json")
        with open(confirmed, "w") as handle:
            json.dump(materialized.tally_fixture()["confirmed"], handle)
        code, facts = support.govern([
            "render", "--version", "2", "--allow-unreleased", "--dest", dest,
            "--repository", "Habit130/tally", "--default-branch", "main", "--confirmed", confirmed,
        ])
        self.assertEqual(code, 0, facts)
        labels = support.read_text(os.path.join(dest, "docs/agents/triage-labels.md"))
        self.assertIn("creation defaults", labels)
        self.assertIn("same-name, same-purpose", labels)
        self.assertIn("purpose conflict", labels)
        self.assertNotIn("exact description", labels)

class VersionThreeRendered(support.TempDirCase):
    """Version 3 rendered into the tally sample: the approved rendered-text seam."""

    def setUp(self):
        super().setUp()
        self.dest = self.path("rendered")
        confirmed = self.path("confirmed.json")
        with open(confirmed, "w") as handle:
            json.dump(materialized.tally_fixture()["confirmed"], handle)
        code, facts = support.govern([
            "render", "--version", "3", "--allow-unreleased", "--dest", self.dest,
            "--repository", "Habit130/tally", "--default-branch", "main", "--confirmed", confirmed,
        ])
        self.assertEqual(code, 0, facts)

    def text(self, path):
        return support.read_text(os.path.join(self.dest, path))


class VersionThreeRerunPolicy(VersionThreeRendered):
    """#136: instructions observed through the approved rendered-text seam."""

    def test_builder_owns_each_required_check_rerun_cause_before_handover(self):
        builder = self.text("docs/agents/builder.md")
        handover = builder.split("9. **Hand over**:", 1)[1].split("## The Reviewer handoff", 1)[0]
        self.assertIn("rerun-only pass", handover)
        self.assertIn("open issue", handover)
        self.assertIn("needs-triage", handover)
        self.assertIn("failed run", handover)
        self.assertIn("how it ended", handover)
        self.assertIn("outside cause", handover)
        self.assertIn("Merge summary", handover)
        self.assertNotIn("Planner", handover)

    def test_review_defines_reruns_and_requires_history_and_head_bound_evidence(self):
        review = self.text("docs/agents/review.md")
        rule = " ".join(level_two_section(review, "## Rerun-only passes", "review.md").split())
        for phrase in ("governance record", "failed, timed out or was cancelled",
                       "unrepaired", "body edit",
                       "repair", "Reviewer", "Merge summary", "earlier attempts",
                       "latest attempt", "Important", "open issue"):
            self.assertIn(phrase, rule)
        evidence = level_two_section(review, "## Evidence comment", "review.md")
        for phrase in ("rerun-only pass", "failed run", "issue"):
            self.assertIn(phrase, evidence)
        summary = level_two_section(review, "## Merge summary", "review.md")
        self.assertIn("Rerun-only passes", summary)
        self.assertIn("cause's open issue", summary)
        agents = self.text("AGENTS.md")
        important = agents.split("- **Important**", 1)[1].split("- **Nit**", 1)[0]
        self.assertIn("rerun-only pass", important)
        self.assertIn("no linked open issue", important)

    def test_rerun_repairs_are_check_specific_and_include_the_fixed_gate(self):
        review = self.text("docs/agents/review.md")
        rule = " ".join(level_two_section(review, "## Rerun-only passes", "review.md").split())
        for phrase in ("fixed governance gate plus", "checks named in the governance record",
                       "input or configuration used by that check repairs the failure",
                       "An unrelated PR edit is not a repair",
                       "corrects the failed gate input"):
            self.assertIn(phrase, rule)
        evidence = " ".join(level_two_section(review, "## Evidence comment", "review.md").split())
        self.assertIn("repair and why it fixes that check's failure", evidence)

    def test_version_three_keeps_copy_budget_routing_and_skill_contracts(self):
        agents = self.text("AGENTS.md")
        bugbot = self.text(".cursor/BUGBOT.md")
        self.assertEqual(bugbot.split("\n\n", 1)[1],
                         level_two_section(agents, CODE_REVIEW_RULES, AGENTS))
        self.assertEqual(budget_failures(agents.encode("utf-8")), [])
        manifest = store.Store(support.REAL_STORE).manifest(3)
        self.assertEqual(routing_failures(self.dest, [e["path"] for e in manifest["templates"]]), [])
        self.assertEqual(skill_mismatches(self.dest, manifest["relied_on_skills"]), [])
        for role, path in ROLE_FILES.items():
            self.assertEqual(role_skills(self.text(path), path), ROLE_SKILLS[role])

    def test_merge_watch_reads_the_rendered_summary_with_a_cause_issue(self):
        import test_merge_watch as watch_tests

        review = self.text("docs/agents/review.md")
        header = review.split("```text\n", 1)[1].split("\n```", 1)[0]
        self.assertEqual(header.splitlines(), [
            "## Merge summary: <tier> at <short sha>",
            "Required reviews: <kind>=<state>, <kind>=<state>",
        ])
        case = watch_tests.load(os.path.join(watch_tests.CASES, "high-complete.json"))
        comments = case["github"]["repos/Habit130/tally/issues/42/comments"]
        comments[-1]["body"] = header.replace("<tier>", "high").replace("<short sha>", "1a95462").replace(
            "<kind>=<state>, <kind>=<state>",
            "self-verification=clear, bugbot=clear, codex=clear, reviewer=clear",
        ) + "\n\nRerun-only pass: required CI; cause: https://github.com/Habit130/tally/issues/43\n"
        self.assertEqual(watch_tests.watch_v3.decide(
            case["event_name"], case["event"], watch_tests.agent_account(),
            watch_tests.recorded(case["github"]),
        ), [])

class VersionThreeReviewerStartAndReread(VersionThreeRendered):
    """#149: the Reviewer start carries its writes; the after-merge report rereads GitHub."""

    REREAD = ("Before any after-merge report, reread from GitHub, for the PR's exact head at "
              "merge: each required review's result, at medium and high the Comment review and "
              "the `Reviewer` status, and the Merge summary. The report states only what that "
              "reading shows.")

    def reviewer_starts(self):
        """Every Reviewer start the rendered tree or the generator procedure prints."""
        paths = [os.path.join(root, name) for root, _, files in os.walk(self.dest) for name in files]
        paths.append(os.path.join(os.path.dirname(os.path.dirname(support.GOVERN)), "SKILL.md"))
        starts = []
        for path in paths:
            starts += [" ".join(found.split())
                       for found in re.findall(r"`(Role: Reviewer\.[^`]*)`", support.read_text(path))]
        return starts

    def test_every_rendered_reviewer_start_is_one_instruction_naming_its_writes(self):
        starts = self.reviewer_starts()
        self.assertGreaterEqual(len(starts), 2, starts)
        self.assertEqual(len(set(starts)), 1, starts)
        start = starts[0]
        self.assertTrue(start.startswith("Role: Reviewer. PR: #<n>. Skills: code-review. "), start)
        for write in ("Comment review", "Reviewer status", "Merge summary", "when clear"):
            self.assertIn(write, start)
        reviewer = level_two_section(self.text("docs/agents/reviewer.md"), "## Start", "reviewer.md")
        self.assertIn(start, " ".join(reviewer.split()))
        handoff = level_two_section(self.text("docs/agents/builder.md"), "## The Reviewer handoff",
                                    "builder.md")
        self.assertIn(start, " ".join(handoff.split()))

    def test_reviewer_start_names_the_writes_and_the_stop_and_tell_rule(self):
        start = " ".join(level_two_section(self.text("docs/agents/reviewer.md"), "## Start",
                                           "reviewer.md").split())
        for phrase in ("habit's start asks for", "Comment review", "`Reviewer` status",
                       "Merge summary", "cannot make them", "stops and tells habit",
                       "instead of posting a summary alone"):
            self.assertIn(phrase, start)

    def test_builder_and_the_procedure_reread_the_exact_head_before_the_after_merge_report(self):
        after = " ".join(level_two_section(self.text("docs/agents/builder.md"), "## After merge",
                                           "builder.md").split())
        self.assertIn(self.REREAD, after)
        skill = support.read_text(os.path.join(os.path.dirname(os.path.dirname(support.GOVERN)),
                                               "SKILL.md"))
        procedure = " ".join(skill.split("## 6. After merge", 1)[1].split())
        self.assertIn(self.REREAD, procedure)

    def test_new_text_names_no_review_bot(self):
        start = level_two_section(self.text("docs/agents/reviewer.md"), "## Start", "reviewer.md")
        writes = [p for p in start.split("\n\n") if "habit's start asks for" in p]
        self.assertEqual(len(writes), 1, start)
        texts = writes + [self.REREAD]
        texts += self.reviewer_starts()
        for text in texts:
            for bot in ("Bugbot", "Codex"):
                self.assertNotIn(bot, text)


def flat(text):
    """A text with its whitespace runs collapsed to single spaces."""
    return " ".join(text.split())


def level_three_section(text, heading):
    """One level-3 section: its heading line up to the next level-2 or level-3 heading."""
    body = text.split("\n" + heading + "\n", 1)[1]
    return re.split(r"\n#{2,3} ", body, 1)[0]


class VersionThreeHandoffs(VersionThreeRendered):
    """#150: two light forms of message to habit, Planner-only dispatch plans, whole-spec delivery."""

    HANDOFF = "docs/agents/handoff.md"
    ROLE_TEXTS = ("docs/agents/builder.md", "docs/agents/reviewer.md", "docs/agents/review.md")

    def rendered_paths(self):
        return sorted(os.path.relpath(os.path.join(root, name), self.dest)
                      for root, _, files in os.walk(self.dest) for name in files)

    def test_the_manifest_writes_the_handoff_file_and_agents_points_to_it(self):
        manifest = store.Store(support.REAL_STORE).manifest(3)
        entries = [e for e in manifest["templates"] if e["path"] == self.HANDOFF]
        self.assertEqual(entries, [{"path": self.HANDOFF, "class": "fixed", "mode": "100644"}])
        handoff = self.text(self.HANDOFF)
        self.assertEqual(handoff.split("\n", 1)[0], MARKDOWN_NOTICE.replace("version 1", "version 3"))
        agents = self.text(AGENTS)
        self.assertIn("`docs/agents/handoff.md`", level_two_section(
            agents, "## Talking to habit and to other agents", AGENTS))
        self.assertIn("`docs/agents/handoff.md`", level_two_section(agents, "## Where to find more", AGENTS))

    def test_handoff_defines_three_kinds_the_moments_and_three_constant_parts_in_order(self):
        handoff = self.text(self.HANDOFF)
        kinds = flat(level_two_section(handoff, "## Three kinds of message", self.HANDOFF))
        for kind in ("**Ordinary conversation**", "**A mid-session request**", "**A final handoff**"):
            self.assertIn(kind, kinds)
        self.assertIn("An escalation is a mid-session request", kinds)
        final = flat(level_two_section(handoff, "## A final handoff", self.HANDOFF))
        for moment in ("**Planner**", "**Builder**", "**Reviewer**", "**Any role**", "after its Merge summary",
                       "the after-merge report", "with the merge command",
                       "cannot continue and another must take over"):
            self.assertIn(moment, final)
        parts = ["1. **The conclusion.**", "2. **What habit does next**", "3. **This session**"]
        found = [final.find(part) for part in parts]
        self.assertTrue(all(index >= 0 for index in found), found)
        self.assertEqual(found, sorted(found))
        for optional in ("**The dispatch plan**", "**Unfinished or risky**", "left out"):
            self.assertIn(optional, final)
        examples = level_two_section(handoff, "## Examples", self.HANDOFF)
        self.assertIn("illustrations, never a template", flat(examples))

    def test_handoff_names_no_review_bot_trigger_or_path_in_its_examples(self):
        handoff = self.text(self.HANDOFF)
        for bot in ("Bugbot", "Codex", "@cursor", "@codex"):
            self.assertNotIn(bot, handoff)
        examples = level_two_section(handoff, "## Examples", self.HANDOFF)
        self.assertEqual([m.group(1) for m in POINTER.finditer(examples)], [])
        self.assertNotIn("diff", examples)

    def test_no_builder_or_reviewer_text_offers_a_next_ticket_or_progress(self):
        for path in self.ROLE_TEXTS:
            text = self.text(path)
            for phrase in ("next ticket", "first unclaimed", "first unblocked"):
                self.assertNotIn(phrase, text, path)
        merge = flat(level_three_section(self.text("docs/agents/review.md"), "### The merge handoff"))
        for kept in ("ghm pr merge <n> --admin --squash --match-head-commit <sha>",
                     "say merged in the Builder's terminal", "can be closed", "retro"):
            self.assertIn(kept, merge)
        self.assertNotIn("**The next ticket.**", merge)
        rules = flat(level_two_section(self.text(self.HANDOFF), "## Only the Planner arranges what comes next",
                                       self.HANDOFF))
        for phrase in ("name no next ticket and show no progress", "only when above zero",
                       "the Planner must rearrange", "a Planner start request"):
            self.assertIn(phrase, rules)

    def test_planner_defines_the_dispatch_plan_its_parent_issue_copy_and_its_owner(self):
        planner = flat(level_two_section(self.text("docs/agents/planner.md"), "## Tickets", "planner.md"))
        for phrase in ("**The dispatch plan.**", "every approved ticket", "dispatch order",
                       "start instruction and its condition", "parent issue", "Only a Planner updates it",
                       "a list, never a table", "its own block", "surely can run together",
                       "When unsure, one"):
            self.assertIn(phrase, planner)
        self.assertNotIn("first unblocked", planner)

    def test_the_start_forms_and_the_builder_limit_agree_everywhere(self):
        spec_starts, ticket_starts = [], []
        for path in self.rendered_paths():
            text = self.text(path)
            spec_starts += [(path, flat(s)) for s in re.findall(r"`(Role: Builder\. Spec: [^`]*)`", text)]
            ticket_starts += [(path, flat(s)) for s in re.findall(r"`(Role: Builder\. Ticket: #<n>[^`]*)`", text)]
        self.assertEqual(len({s for _, s in spec_starts}), 1, spec_starts)
        self.assertEqual({p for p, _ in spec_starts} >= {AGENTS, "docs/agents/builder.md",
                                                         "docs/agents/planner.md"}, True, spec_starts)
        spec = spec_starts[0][1]
        self.assertEqual(spec, "Role: Builder. Spec: #<n>. Skills: implement-spec, tdd.")
        self.assertEqual(len({s for _, s in ticket_starts}), 1, ticket_starts)
        agents = self.text(AGENTS)
        start = flat(level_two_section(agents, "## How to start", AGENTS))
        self.assertIn(ticket_starts[0][1], start)
        self.assertIn(spec, start)
        limit = flat(level_two_section(agents, "## Hard limits", AGENTS))
        self.assertIn("**Builder**: one delivery, one ticket or one spec habit approved for whole-spec "
                      "delivery, in a fresh session", limit)
        builder = flat(level_two_section(self.text("docs/agents/builder.md"), "## Whole-spec delivery",
                                         "builder.md"))
        for phrase in (spec, "the spec and each of its tickets", "its own worktree", "in the Builder's role",
                       "one integration branch", "only that branch is pushed", "**One PR** closes the spec",
                       "highest tier any part reaches", "`planner.md`, Delivery shape"):
            self.assertIn(phrase, builder)
        tracker = flat(self.text("docs/agents/issue-tracker.md"))
        self.assertIn("claims the spec and each of its tickets", tracker)

    def test_the_foreseen_high_rule_is_stated_once_in_the_planner(self):
        places = [path for path in self.rendered_paths()
                  if "high for the same reason" in flat(self.text(path))]
        self.assertEqual(places, ["docs/agents/planner.md"])
        shape = flat(level_two_section(self.text("docs/agents/planner.md"), "## Delivery shape", "planner.md"))
        for phrase in ("habit approves it with the spec", "each ticket is small",
                       "reviewable in one pass", "one-way door", "always gets its own PR"):
            self.assertIn(phrase, shape)
        self.assertNotIn("make sense only merged together", shape)
        self.assertIn("only the high part in the PR", self.text("docs/agents/review.md"))

    def test_the_merge_summary_terminal_copy_is_unchanged(self):
        terminal = flat(level_three_section(self.text("docs/agents/review.md"), "### In the terminal"))
        self.assertIn(flat("""- **First line**: the tier, the verdict, and the Important, Nit and Pre-existing counts.
- **Seven items:**
  1. the tier and why;
  2. what changed, in three to five bullets;
  3. each acceptance criterion, met or not;
  4. the evidence, in plain words;
  5. each finding in one sentence, with its answer;
  6. what the checks don't cover;
  7. how to revert."""), terminal)

    def test_a_start_request_names_the_shared_resource_it_takes(self):
        talking = flat(level_two_section(self.text(AGENTS), "## Talking to habit and to other agents", AGENTS))
        self.assertIn("any shared resource the session takes", talking)
        self.assertIn("never a list of options", talking)


# The governance gate (#41 §8): its workflow and the one script it runs.
GATE_FILES = (".github/workflows/governance-gate.yml", ".github/governance/gate.py")
# Merge watch (#41 §9): its workflow and the one script it runs, beside the gate's.
MERGE_WATCH_FILES = (".github/workflows/merge-watch.yml", ".github/governance/merge_watch.py")
NOTICE = "# Generated by governance model version 1. Only the generator changes this file."
# The owner script (#41 §1, #44 §7): a bash entry, so its shebang takes line 1, the notice
# line 2, and its mode is executable, in the manifest and in the rendered tree alike.
OWNER_SCRIPT = ".github/governance/owner.sh"
# A fixed Markdown file's notice is its first line, as an HTML comment.
MARKDOWN_NOTICE = "<!-- Generated by governance model version 1. Only the generator changes this file. -->"

# The role files and review.md (#41 §1), and each role's skills (#41 §13).
ROLE_FILES = {
    "planner": "docs/agents/planner.md",
    "builder": "docs/agents/builder.md",
    "reviewer": "docs/agents/reviewer.md",
}
ROLE_AND_REVIEW_FILES = tuple(sorted(ROLE_FILES.values())) + ("docs/agents/review.md",)
# The tracker, label and domain files and the PR template, fixed (#41 §1); build.md is the
# skeleton the generator fills, repository-owned once written, so it carries no notice.
TRACKER_FILES = (
    "docs/agents/issue-tracker.md",
    "docs/agents/triage-labels.md",
    "docs/agents/domain.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
)
BUILD_SKELETON = "docs/agents/build.md"
# triage-labels.md gives each label the generator creates, with the manifest's description.
TRIAGE_LABELS = "docs/agents/triage-labels.md"
# Required roles are independent of the manifest (#79); categories are not states.
TRIAGE_ROLES = {
    "Category": ("bug", "enhancement"),
    "State": ("needs-triage", "needs-info", "ready-for-agent", "ready-for-human", "wontfix"),
}
# The PR template (#41 §1): the gate reads every body line that starts with `Risk:` or
# `Reverts:`, inside HTML comments too (#41 §8), so no comment line may start that way.
PR_TEMPLATE = ".github/PULL_REQUEST_TEMPLATE.md"
GATE_FIELDS = ("Risk:", "Reverts:")
# An HTML comment runs to its first `-->`, or to the end of the text when none follows.
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
ROLE_SKILLS = {
    "planner": {
        "to-spec", "to-tickets", "triage", "wayfinder", "retro",
        "grilling", "domain-modeling", "research", "prototype", "codebase-design", "writing-for-agents",
    },
    "builder": {
        "implement-spec",
        "tdd", "code-review", "pr", "diagnosing-bugs", "codebase-design", "prototype", "research", "grilling",
        "writing-for-agents",
    },
    "reviewer": {"code-review", "research"},
}
NOT_RELIED_ON = ("implement", "grill-with-docs", "grill-me", "handoff", "ask-matt")

# AGENTS.md and .claude/CLAUDE.md are mixed (#41 §1): the fixed part sits between the markers,
# its first line inside them the notice, and repository-owned text follows the end marker.
# .cursor/BUGBOT.md is fixed: its notice on line 1, then AGENTS.md's Code Review Rules.
AGENTS = "AGENTS.md"
CLAUDE = ".claude/CLAUDE.md"
BUGBOT = ".cursor/BUGBOT.md"
MIXED_FILES = (AGENTS, CLAUDE)
BEGIN_MARKER = "<!-- governance:begin v1 -->"
END_MARKER = "<!-- governance:end -->"
MIXED_NOTICE = "<!-- Generated by governance model version 1. Only the generator changes the text between the markers. -->"
# AGENTS.md's sections, in order, inside the markers (#41 §1); the skeleton's after them.
AGENTS_SECTIONS = (
    "How to start",
    "Flow at a glance",
    "Hard limits",
    "Talking to habit and to other agents",
    "Governance files",
    "Secrets",
    "Code Review Rules",
    "Where to find more",
)
REPOSITORY_SECTIONS = ("This repository",)
CODE_REVIEW_RULES = "## Code Review Rules"
# AGENTS.md's budget, rendered and skeleton included: #41 §1's "about 10 KB", with 10% over
# allowed, which leaves 21 KiB of the Codex harness's 32 KiB cap for the repository's own text.
AGENTS_BUDGET = 11 * 1024
# Version 1 writes no root CLAUDE.md, AGENTS.override.md or .codex/ (#41 §1, §11), in any case,
# since a case-insensitive file system opens claude.md for CLAUDE.md.
NEVER_WRITTEN = re.compile(r"^(?:CLAUDE\.md|(?:.*/)?AGENTS\.override\.md|\.codex/.*)$", re.I)

# Routing (#41 seam 3): every path pointer in a Markdown file version 1 writes names a file
# version 1 writes. A pointer is a path ending in one of these extensions, backticked or not,
# or a backticked directory ending in `/`. A path starting `./` or `../` is relative to its
# file, one with a `/` is root-relative, and a bare name is a root or `docs/agents/` file.
# Outside the check: the workflows and the scripts they and habit run, and files the generator
# never writes, repository-owned or named as absent.
POINTER = re.compile(
    r"(?<![\w./-])((?:\.\.?/)*(?:\.?[A-Za-z0-9_-]+/)*\.?[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.(?:md|yml|yaml|py|sh|json))(?!\.?[\w/-])"
)
DIRECTORY_POINTER = re.compile(r"`((?:\.?[A-Za-z0-9_-]+/)+)`")
UNROUTED = (
    ".github/workflows/",
    ".github/governance/gate.py",
    ".github/governance/owner.sh",
    "GLOSSARY.md",
    "GLOSSARY-MAP.md",
    "docs/adr/",
    "CLAUDE.md",
    "AGENTS.override.md",
    ".codex/",
)

# A role file lists its skills on these two lines, and only there, under this heading.
SKILLS_HEADING = "## Skills this role relies on"
SKILL_LINES = ("- habit invokes:", "- The session calls:")
SKILL_NAME = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")


def role_skills(text, where):
    """The skills one role file lists: the backticked names on its two skill lines."""
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line == SKILLS_HEADING]
    if len(starts) != 1:
        raise AssertionError("%s has %d %r headings; it needs one" % (where, len(starts), SKILLS_HEADING))
    section = []
    for line in lines[starts[0] + 1:]:
        if line.startswith("#"):
            break
        section.append(line)
    skills = set()
    for prefix in SKILL_LINES:
        found = [line for line in section if line.startswith(prefix)]
        if len(found) != 1:
            raise AssertionError("%s has %d %r lines under its skills heading; it needs one" % (where, len(found), prefix))
        skills.update(SKILL_NAME.findall(found[0]))
    return skills


def skill_mismatches(worktree, relied_on):
    """One line per disagreement between the role files' skill lists and the relied-on list."""
    listed = set()
    for path in sorted(ROLE_FILES.values()):
        listed |= role_skills(support.read_text(os.path.join(worktree, *path.split("/"))), path)
    lines = ["no role file lists the relied-on skill %s" % name for name in sorted(set(relied_on) - listed)]
    lines += ["a role file lists %s, which the relied-on list lacks" % name for name in sorted(listed - set(relied_on))]
    return lines


def comment_line_numbers(text):
    """The 1-based numbers of every line an HTML comment spans, its continuation lines included."""
    numbers = set()
    for match in HTML_COMMENT.finditer(text):
        first = text.count("\n", 0, match.start()) + 1
        numbers.update(range(first, text.count("\n", 0, match.end()) + 2))
    return numbers


def comment_line_failures(text, where):
    """One line per comment line that starts with `Risk:` or `Reverts:`, as the gate's parser reads a line."""
    lines = text.split("\n")
    failures = []
    for number in sorted(comment_line_numbers(text)):
        for field in GATE_FIELDS:
            if lines[number - 1].startswith(field):
                failures.append("%s line %d starts with %s inside an HTML comment" % (where, number, field))
    return failures


def label_mismatches(text, labels):
    """One line per manifest label that no table row of the text gives, backticked, with its description."""
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in text.split("\n") if line.startswith("|")]
    return [
        "%s has no table row for %s with the description %r" % (TRIAGE_LABELS, label["name"], label["description"])
        for label in labels
        if not any("`%s`" % label["name"] in row and label["description"] in row for row in rows)
    ]


def triage_role_failures(text, labels):
    """Required category/state roles must be provisioned and mapped to their own labels."""
    failures = []
    for kind, roles in TRIAGE_ROLES.items():
        section = level_two_section(text, "## %s roles" % kind, TRIAGE_LABELS)
        rows = [[cell.strip() for cell in line.strip("|").split("|")]
                for line in section.split("\n") if line.startswith("|")]
        for role in roles:
            if sum(label["name"] == role for label in labels) != 1:
                failures.append("manifest must provision %s once" % role)
            matches = [row for row in rows if row[0] == "`%s`" % role]
            if len(matches) != 1 or len(matches[0]) < 2 or matches[0][1] != "`%s`" % role:
                failures.append("%s role %s must map to its own label once" % (kind, role))
    return failures


def marker_failures(text, where):
    """One line per way a mixed file's markers fail: the generator's marker reader, then the version and the notice."""
    try:
        start, end = render.find_block(text, where)
    except render.MarkerError as error:
        return [str(error)]
    block = text[start:end].split("\n")
    failures = []
    if block[0] != BEGIN_MARKER:
        failures.append("%s's begin marker is %r, not version 1's" % (where, block[0]))
    if block[1] != MIXED_NOTICE:
        failures.append("%s's first line inside the markers is %r, not the notice" % (where, block[1]))
    return failures


def headings(text):
    """The level-2 headings of a text, in order."""
    return [line[3:] for line in text.split("\n") if line.startswith("## ")]


def level_two_section(text, heading, where):
    """One level-2 section: its heading line up to the next level-2 heading, trailing blank lines dropped."""
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line == heading]
    if len(starts) != 1:
        raise AssertionError("%s has %d %r headings; it needs one" % (where, len(starts), heading))
    end = next((index for index in range(starts[0] + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    body = lines[starts[0]:end]
    while not body[-1].strip():
        body.pop()
    return "\n".join(body) + "\n"


def bugbot_failures(agents_text, bugbot_text):
    """A line naming where .cursor/BUGBOT.md first departs from its notice, a blank line and AGENTS.md's Code Review Rules."""
    expected = (MARKDOWN_NOTICE + "\n\n" + level_two_section(agents_text, CODE_REVIEW_RULES, AGENTS)).split("\n")
    found = bugbot_text.split("\n")
    if found == expected:
        return []
    number = next(
        (number for number, (want, got) in enumerate(zip(expected, found), 1) if want != got),
        min(len(expected), len(found)) + 1,
    )
    return ["%s departs from %s's Code Review Rules at its line %d" % (BUGBOT, AGENTS, number)]


def budget_failures(data):
    """A line when the rendered AGENTS.md is over its budget, in bytes."""
    if len(data) <= AGENTS_BUDGET:
        return []
    return ["%s is %d bytes, over its %d-byte budget" % (AGENTS, len(data), AGENTS_BUDGET)]


def pointer_targets(source, pointer):
    """The store paths a pointer in the file at source may name."""
    if pointer.startswith(("./", "../")):
        return [posixpath.normpath(posixpath.join(posixpath.dirname(source), pointer))]
    if "/" in pointer:
        return [pointer]
    return [pointer, "docs/agents/" + pointer]


def covers(name, path):
    """Whether a file or directory name, a directory ending in `/`, covers a path."""
    return path.startswith(name) if name.endswith("/") else path == name


def routing_failures(worktree, paths, unrouted=UNROUTED):
    """One line per path pointer, in the Markdown files among paths, that names no file among paths."""
    failures = []
    for source in sorted(path for path in paths if path.endswith(".md")):
        text = support.read_text(os.path.join(worktree, *source.split("/")))
        for number, line in enumerate(text.split("\n"), 1):
            pointers = [match.group(1) for match in POINTER.finditer(line)]
            pointers += [match.group(1) for match in DIRECTORY_POINTER.finditer(line)]
            for pointer in pointers:
                targets = pointer_targets(source, pointer)
                if any(covers(target, path) for target in targets for path in paths):
                    continue
                if any(covers(name, target) for target in targets for name in unrouted):
                    continue
                failures.append("%s line %d points at %s, which version 1 doesn't write" % (source, number, pointer))
    return failures


class MaterializedVersionOne(support.TempDirCase):
    def setUp(self):
        super(MaterializedVersionOne, self).setUp()
        self.worktree, self.render_facts = materialized.render_version_one(self.tmp)

    def test_exact_comparison_finds_no_difference(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        self.assertEqual(facts["differences"], [])
        self.assertEqual((facts["repository"], facts["default_branch"]), ("Habit130/tally", "main"))
        self.assertIn(RECORD, facts["checked"])

    def test_rendering_writes_only_the_versions_templates(self):
        status = support.git(self.worktree, "status", "--porcelain", "--untracked-files=all")
        changed = sorted(line[3:] for line in status.splitlines())
        self.assertEqual(changed, sorted(self.render_facts["written"]))

    def test_tally_keeps_its_own_files_and_modes(self):
        self.assertEqual(support.file_mode(os.path.join(self.worktree, "scripts", "release.sh")), "100755")
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, ".github", "workflows", "ci.yml")))
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, ".gitignore")))

    # #41's template tickets add their seam-3 checks below, against self.worktree.

    def test_the_gate_workflow_and_script_carry_the_notice_with_their_placeholders_resolved(self):
        for path in GATE_FILES:
            text = support.read_text(os.path.join(self.worktree, *path.split("/")))
            self.assertEqual(text.split("\n")[0], NOTICE, path)
            self.assertNotIn("@@", text, path)
        workflow = support.read_text(os.path.join(self.worktree, ".github", "workflows", "governance-gate.yml"))
        self.assertIn('    branches:\n      - "main"\n', workflow)

    def test_the_gate_files_keep_their_mode_and_pass_exact_comparison(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in GATE_FILES:
            self.assertIn(path, facts["checked"])
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)

    def test_merge_watchs_workflow_and_script_carry_the_notice_keep_their_mode_and_pass_exact_comparison(self):
        entries = {entry["path"]: entry for entry in store.Store(support.REAL_STORE).manifest(1)["templates"]}
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in MERGE_WATCH_FILES:
            text = support.read_text(os.path.join(self.worktree, *path.split("/")))
            self.assertEqual(text.split("\n")[0], NOTICE, path)
            self.assertNotIn("@@", text, path)
            self.assertEqual((entries[path]["class"], entries[path]["mode"]), ("fixed", "100644"), path)
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)
            self.assertIn(path, facts["checked"])
        workflow = support.read_text(os.path.join(self.worktree, *MERGE_WATCH_FILES[0].split("/")))
        self.assertEqual(workflow.count('      - "main"\n'), 2)

    def test_the_owner_script_carries_the_notice_after_its_shebang_and_stays_executable(self):
        text = support.read_text(os.path.join(self.worktree, *OWNER_SCRIPT.split("/")))
        self.assertEqual(text.split("\n")[:2], ["#!/bin/bash", NOTICE])
        self.assertNotIn("@@", text)
        self.assertEqual(support.file_mode(os.path.join(self.worktree, *OWNER_SCRIPT.split("/"))), "100755")
        entries = {entry["path"]: entry for entry in store.Store(support.REAL_STORE).manifest(1)["templates"]}
        self.assertEqual((entries[OWNER_SCRIPT]["class"], entries[OWNER_SCRIPT]["mode"]), ("fixed", "100755"))
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        self.assertIn(OWNER_SCRIPT, facts["checked"])

    def test_the_role_files_and_review_md_carry_the_notice_and_pass_exact_comparison(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in ROLE_AND_REVIEW_FILES:
            text = support.read_text(os.path.join(self.worktree, *path.split("/")))
            self.assertEqual(text.split("\n")[0], MARKDOWN_NOTICE, path)
            self.assertNotIn("@@", text, path)
            self.assertIn(path, facts["checked"])
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)

    def test_the_tracker_label_domain_files_and_pr_template_carry_the_notice_and_pass_exact_comparison(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in TRACKER_FILES:
            text = support.read_text(os.path.join(self.worktree, *path.split("/")))
            self.assertEqual(text.split("\n")[0], MARKDOWN_NOTICE, path)
            self.assertNotIn("@@", text, path)
            self.assertIn(path, facts["checked"])
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)
        tracker = support.read_text(os.path.join(self.worktree, "docs", "agents", "issue-tracker.md"))
        self.assertIn("--repo Habit130/tally", tracker)

    def test_the_build_skeleton_is_written_without_the_notice_and_left_uncompared(self):
        entries = {entry["path"]: entry for entry in store.Store(support.REAL_STORE).manifest(1)["templates"]}
        self.assertEqual(entries[BUILD_SKELETON]["class"], "skeleton")
        self.assertIn(BUILD_SKELETON, self.render_facts["written"])
        text = support.read_text(os.path.join(self.worktree, *BUILD_SKELETON.split("/")))
        self.assertNotIn("Generated by governance model", text)
        self.assertNotIn("@@", text)
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        self.assertNotIn(BUILD_SKELETON, facts["checked"])
        self.assertEqual(facts["not_compared"], {BUILD_SKELETON: "skeleton: repository-owned content"})

    def pr_template(self):
        return support.read_text(os.path.join(self.worktree, *PR_TEMPLATE.split("/")))

    def test_no_pr_template_comment_line_starts_with_risk_or_reverts(self):
        self.assertEqual(comment_line_failures(self.pr_template(), PR_TEMPLATE), [])

    def test_a_planted_comment_line_fails_the_comment_check(self):
        self.plant(PR_TEMPLATE, "- The evidence and the Merge summary", "Reverts: <full sha>\n- The evidence and the Merge summary")
        self.plant(PR_TEMPLATE, "<!-- Written with `pr`. -->", "<!-- Written with `pr`.\nRisk: low — planted\n-->")
        lines = self.pr_template().split("\n")
        self.assertEqual(
            comment_line_failures("\n".join(lines), PR_TEMPLATE),
            [
                "%s line %d starts with Reverts: inside an HTML comment" % (PR_TEMPLATE, lines.index("Reverts: <full sha>") + 1),
                "%s line %d starts with Risk: inside an HTML comment" % (PR_TEMPLATE, lines.index("Risk: low — planted") + 1),
            ],
        )

    def test_a_comment_naming_the_fields_mid_sentence_passes_the_comment_check(self):
        self.plant(PR_TEMPLATE, "<!-- Written with `pr`. -->", "<!-- Written with `pr`; no line here\n  starts with Risk: or Reverts: -->")
        self.assertEqual(comment_line_failures(self.pr_template(), PR_TEMPLATE), [])

    def test_the_pr_templates_one_risk_line_sits_outside_its_comments_and_no_line_starts_with_reverts(self):
        text = self.pr_template()
        risk = [number for number, line in enumerate(text.split("\n"), 1) if line.startswith("Risk:")]
        self.assertEqual(len(risk), 1, risk)
        self.assertNotIn(risk[0], comment_line_numbers(text))
        self.assertEqual([line for line in text.split("\n") if line.startswith("Reverts:")], [])

    def test_the_pr_template_with_its_risk_line_filled_passes_both_parsers(self):
        body = self.pr_template().replace("Risk: <low|medium|high> — <reason>", "Risk: medium — edits docs/agents")
        sha = "0123456789abcdef0123456789abcdef01234567"
        reverting = body.replace("Risk: medium — edits docs/agents\n", "Risk: medium — edits docs/agents\nReverts: %s\n" % sha)
        for parser in parsers.PARSERS:
            self.assertEqual(
                parser.pr_body(body), {"risk": {"tier": "medium", "reason": "edits docs/agents"}, "reverts": None}, parser.name
            )
            self.assertEqual(parser.pr_body(reverting)["reverts"], {"sha": sha}, parser.name)

    def test_triage_labels_md_gives_each_label_the_generator_creates_with_its_description(self):
        labels = store.Store(support.REAL_STORE).manifest(1)["labels"]
        text = support.read_text(os.path.join(self.worktree, *TRIAGE_LABELS.split("/")))
        self.assertEqual(label_mismatches(text, labels), [])

    def test_triage_mapping_independently_requires_two_categories_and_five_states(self):
        labels = store.Store(support.REAL_STORE).manifest(1)["labels"]
        self.assertEqual(triage_role_failures(self.text(TRIAGE_LABELS), labels), [])

    def test_each_missing_or_wrong_category_mapping_fails_even_with_joint_omissions(self):
        labels = store.Store(support.REAL_STORE).manifest(1)["labels"]
        text = self.text(TRIAGE_LABELS)
        for category in ("bug", "enhancement"):
            row = next(line for line in text.splitlines() if line.startswith("| `%s` |" % category))
            missing_mapping = text.replace(row + "\n", "")
            missing_label = [label for label in labels if label["name"] != category]
            mapping_failure = "Category role %s must map to its own label once" % category
            provision_failure = "manifest must provision %s once" % category
            cells = row.split("|")
            cells[2] = " `needs-triage` "
            wrong_mapping = text.replace(row, "|".join(cells))
            for mutation, mapped, provisioned, expected in (
                ("manifest only", text, missing_label, [provision_failure]),
                ("mapping only", missing_mapping, labels, [mapping_failure]),
                ("both missing", missing_mapping, missing_label, [provision_failure, mapping_failure]),
                ("wrong mapping", wrong_mapping, labels, [mapping_failure]),
            ):
                with self.subTest(category=category, mutation=mutation):
                    self.assertEqual(triage_role_failures(mapped, provisioned), expected)

    def test_a_planted_label_description_fails_the_label_check(self):
        labels = store.Store(support.REAL_STORE).manifest(1)["labels"]
        self.plant(TRIAGE_LABELS, "| Will not be actioned |", "| Won't be done |")
        self.plant(TRIAGE_LABELS, "| `miss` |", "| `misses` |")
        text = support.read_text(os.path.join(self.worktree, *TRIAGE_LABELS.split("/")))
        self.assertEqual(
            label_mismatches(text, labels),
            [
                "%s has no table row for wontfix with the description %r" % (TRIAGE_LABELS, "Will not be actioned"),
                "%s has no table row for miss with the description %r"
                % (TRIAGE_LABELS, "Miss record: something governance should have stopped got through"),
            ],
        )

    def test_each_role_file_lists_its_roles_skills(self):
        for role, path in ROLE_FILES.items():
            listed = role_skills(support.read_text(os.path.join(self.worktree, *path.split("/"))), path)
            self.assertEqual(listed, ROLE_SKILLS[role], path)
            self.assertEqual(listed & set(NOT_RELIED_ON), set(), path)

    def test_the_role_files_skills_equal_the_relied_on_list(self):
        relied_on = store.Store(support.REAL_STORE).manifest(1)["relied_on_skills"]
        self.assertEqual(skill_mismatches(self.worktree, relied_on), [])

    def plant(self, path, old, new):
        target = os.path.join(self.worktree, *path.split("/"))
        text = support.read_text(target)
        self.assertEqual(text.count(old), 1, (path, old))
        with open(target, "wb") as handle:
            handle.write(text.replace(old, new).encode("utf-8"))

    def test_a_planted_skill_mismatch_fails_the_skills_check(self):
        relied_on = store.Store(support.REAL_STORE).manifest(1)["relied_on_skills"]
        self.plant(ROLE_FILES["builder"], "- The session calls: `tdd`,", "- The session calls: `implement`, `tdd`,")
        self.plant(ROLE_FILES["planner"], ", `retro`", "")
        self.assertEqual(
            skill_mismatches(self.worktree, relied_on),
            [
                "no role file lists the relied-on skill retro",
                "a role file lists implement, which the relied-on list lacks",
            ],
        )

    def test_a_skill_dropped_from_the_relied_on_list_fails_the_skills_check(self):
        relied_on = [name for name in store.Store(support.REAL_STORE).manifest(1)["relied_on_skills"] if name != "pr"]
        self.assertEqual(skill_mismatches(self.worktree, relied_on), ["a role file lists pr, which the relied-on list lacks"])

    def test_a_skill_named_outside_the_skill_lines_is_not_listed(self):
        relied_on = store.Store(support.REAL_STORE).manifest(1)["relied_on_skills"]
        self.plant(ROLE_FILES["builder"], SKILLS_HEADING + "\n", SKILLS_HEADING + "\n\nhabit may still use `implement`.\n")
        self.assertEqual(skill_mismatches(self.worktree, relied_on), [])

    def test_the_record_parses(self):
        with open(os.path.join(self.worktree, *RECORD.split("/")), "rb") as handle:
            parsed = record.parse(handle.read())
        self.assertEqual(
            parsed,
            {
                "version": 1,
                "agent_account": "Habit098",
                "sensitive_paths": [{"pattern": pattern, "floor": "medium"} for pattern in DEFAULT_PATTERNS],
                "confirmed": materialized.tally_fixture()["confirmed"],
            },
        )

    def text(self, path):
        return support.read_text(os.path.join(self.worktree, *path.split("/")))

    def test_agents_md_claude_md_and_bugbot_md_carry_the_notice_and_pass_exact_comparison(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        for path in MIXED_FILES:
            self.assertEqual(marker_failures(self.text(path), path), [])
        self.assertEqual(self.text(BUGBOT).split("\n")[0], MARKDOWN_NOTICE)
        for path in MIXED_FILES + (BUGBOT,):
            self.assertIn(path, self.render_facts["written"])
            self.assertNotIn("@@", self.text(path), path)
            self.assertIn(path, facts["checked"])
            self.assertEqual(support.file_mode(os.path.join(self.worktree, *path.split("/"))), "100644", path)

    def test_planted_missing_duplicated_or_out_of_order_markers_fail_the_marker_check(self):
        text = self.text(AGENTS)
        self.assertEqual(
            marker_failures(text.replace(END_MARKER + "\n", ""), AGENTS),
            ["AGENTS.md has 1 begin and 0 end markers; a fixed part needs exactly one of each"],
        )
        self.assertEqual(
            marker_failures(text.replace(BEGIN_MARKER + "\n", BEGIN_MARKER + "\n" + BEGIN_MARKER + "\n"), AGENTS),
            ["AGENTS.md has 2 begin and 1 end markers; a fixed part needs exactly one of each"],
        )
        swapped = text.replace(BEGIN_MARKER, "<swap>").replace(END_MARKER, BEGIN_MARKER).replace("<swap>", END_MARKER)
        self.assertEqual(marker_failures(swapped, AGENTS), ["AGENTS.md has its end marker before its begin marker"])
        self.assertEqual(
            marker_failures(text.replace(BEGIN_MARKER, "<!-- governance:begin v2 -->"), AGENTS),
            ["AGENTS.md's begin marker is '<!-- governance:begin v2 -->', not version 1's"],
        )
        self.assertEqual(
            marker_failures(self.text(CLAUDE).replace(MIXED_NOTICE + "\n", ""), CLAUDE),
            [".claude/CLAUDE.md's first line inside the markers is '@../AGENTS.md', not the notice"],
        )

    def test_agents_md_holds_its_sections_in_order_with_this_repository_after_the_markers(self):
        text = self.text(AGENTS)
        start, end = render.find_block(text, AGENTS)
        self.assertEqual(headings(text[start:end]), list(AGENTS_SECTIONS))
        self.assertEqual(headings(text[end:]), list(REPOSITORY_SECTIONS))
        self.assertEqual(headings(text[:start]), [])

    def test_claude_md_imports_agents_md_from_inside_its_markers(self):
        text = self.text(CLAUDE)
        start, end = render.find_block(text, CLAUDE)
        self.assertEqual(text[start:end].split("\n")[2], "@../AGENTS.md")
        self.assertEqual(pointer_targets(CLAUDE, "../AGENTS.md"), [AGENTS])

    def test_text_after_the_end_markers_is_repository_owned_and_inside_them_is_compared(self):
        self.plant(AGENTS, "## This repository\n", "## This repository\n\nA carried rule.\n")
        self.plant(CLAUDE, END_MARKER + "\n", END_MARKER + "\n\nA Claude Code note.\n")
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual((code, facts["differences"]), (0, []))
        self.plant(AGENTS, "## Hard limits\n", "## Hard limits\n\nA planted rule.\n")
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 1)
        self.assertEqual([(d["path"], d["kind"]) for d in facts["differences"]], [(AGENTS, "content")])

    def test_agents_md_is_within_its_budget(self):
        with open(os.path.join(self.worktree, AGENTS), "rb") as handle:
            self.assertEqual(budget_failures(handle.read()), [])

    def test_a_planted_agents_md_over_its_budget_fails_the_budget_check(self):
        with open(os.path.join(self.worktree, AGENTS), "rb") as handle:
            data = handle.read()
        padded = data + b"x" * (AGENTS_BUDGET + 1 - len(data))
        self.assertEqual(budget_failures(padded), ["AGENTS.md is 11265 bytes, over its 11264-byte budget"])
        self.assertEqual(budget_failures(padded[:-1]), [])

    def test_bugbot_md_equals_agents_mds_code_review_rules(self):
        self.assertEqual(bugbot_failures(self.text(AGENTS), self.text(BUGBOT)), [])
        self.assertEqual(self.text(BUGBOT).split("\n")[2], CODE_REVIEW_RULES)

    def test_a_planted_one_character_difference_fails_the_bugbot_check(self):
        agents, bugbot = self.text(AGENTS), self.text(BUGBOT)
        line = next(line for line in bugbot.split("\n") if "Important" in line)
        planted = bugbot.replace(line, line.replace("Important", "Importent", 1), 1)
        number = bugbot.split("\n").index(line) + 1
        self.assertEqual(bugbot_failures(agents, planted), ["%s departs from %s's Code Review Rules at its line %d" % (BUGBOT, AGENTS, number)])
        self.assertEqual(
            bugbot_failures(agents.replace(line, line.replace("Important", "Importent", 1), 1), bugbot),
            ["%s departs from %s's Code Review Rules at its line %d" % (BUGBOT, AGENTS, number)],
        )
        self.assertEqual(
            bugbot_failures(agents, bugbot + "A rule only Bugbot reads.\n"),
            ["%s departs from %s's Code Review Rules at its line %d" % (BUGBOT, AGENTS, len(bugbot.split("\n")))],
        )

    def manifest_paths(self):
        return [entry["path"] for entry in store.Store(support.REAL_STORE).manifest(1)["templates"]]

    def test_every_path_pointer_names_a_file_version_one_writes(self):
        self.assertEqual(routing_failures(self.worktree, self.manifest_paths()), [])

    def line_number(self, path, text):
        """The 1-based number of the one line of a worktree file holding text."""
        numbers = [number for number, line in enumerate(self.text(path).split("\n"), 1) if text in line]
        self.assertEqual(len(numbers), 1, (path, text))
        return numbers[0]

    def test_planted_broken_pointers_fail_the_routing_check(self):
        self.plant(PR_TEMPLATE, "as builder.md, step 7", "as build-steps.md, step 7")
        self.plant(AGENTS, "`docs/agents/triage-labels.md`", "`docs/agents/labels.md`")
        self.plant(CLAUDE, "@../AGENTS.md", "@../AGENT.md")
        self.plant(CLAUDE, "## Claude Code notes\n", "## Claude Code notes\n\nSee ./local-notes.md.\n")
        self.assertEqual(
            routing_failures(self.worktree, self.manifest_paths()),
            [
                "%s line %d points at ../AGENT.md, which version 1 doesn't write" % (CLAUDE, self.line_number(CLAUDE, "@../AGENT.md")),
                "%s line %d points at ./local-notes.md, which version 1 doesn't write" % (CLAUDE, self.line_number(CLAUDE, "./local-notes.md")),
                "%s line %d points at build-steps.md, which version 1 doesn't write" % (PR_TEMPLATE, self.line_number(PR_TEMPLATE, "build-steps.md")),
                "%s line %d points at docs/agents/labels.md, which version 1 doesn't write" % (AGENTS, self.line_number(AGENTS, "docs/agents/labels.md")),
            ],
        )

    def test_unrouted_names_stay_outside_the_routing_check_and_fail_without_it(self):
        paths = self.manifest_paths()
        before = len(routing_failures(self.worktree, paths, unrouted=()))
        planted = ("`GLOSSARY.md`", "`docs/adr/`", "`.github/workflows/ci.yml`", "no root `CLAUDE.md`", "`.codex/`")
        for pointer in planted:
            self.plant(AGENTS, "## This repository\n", "## This repository\n\n%s\n" % pointer)
        self.assertEqual(routing_failures(self.worktree, paths), [])
        self.assertEqual(len(routing_failures(self.worktree, paths, unrouted=())), before + len(planted))

    def test_version_one_writes_no_root_claude_md_override_or_codex_directory(self):
        self.assertEqual([path for path in self.manifest_paths() if NEVER_WRITTEN.match(path)], [])
        self.assertEqual([path for path in self.render_facts["written"] if NEVER_WRITTEN.match(path)], [])
        planted = ["CLAUDE.md", "claude.md", "docs/AGENTS.override.md", ".codex/config.toml", ".claude/CLAUDE.md", "AGENTS.md"]
        self.assertEqual([path for path in planted if NEVER_WRITTEN.match(path)], planted[:4])


if __name__ == "__main__":
    unittest.main()
