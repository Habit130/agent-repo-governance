"""Governance model version three: rendered policy-text checks."""

import os
import re

import support
from govlib import store
from materialized_version_support import (
    AGENTS, MARKDOWN_NOTICE, POINTER, ROLE_FILES, ROLE_SKILLS,
    VersionThreeRendered, budget_failures, flat, level_three_section,
    level_two_section, role_skills, routing_failures, skill_mismatches,
)


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

    def test_version_three_keeps_budget_routing_and_skill_contracts(self):
        agents = self.text("AGENTS.md")
        self.assertFalse(os.path.exists(os.path.join(self.dest, ".cursor")))
        self.assertEqual(budget_failures(agents.encode("utf-8")), [])
        manifest = store.Store(support.REAL_STORE).manifest(3)
        self.assertEqual(routing_failures(self.dest, [e["path"] for e in manifest["templates"]]), [])
        self.assertEqual(skill_mismatches(self.dest, manifest["relied_on_skills"]), [])
        for role, path in ROLE_FILES.items():
            self.assertEqual(role_skills(self.text(path), path), ROLE_SKILLS[role])

    def test_merge_watch_reads_the_rendered_summary_with_a_cause_issue(self):
        import test_merge_watch as watch_tests

        review = self.text("docs/agents/review.md")
        header = review.split("```text\n## Merge summary: <tier>", 1)[1].split("\n```", 1)[0]
        self.assertEqual(header.splitlines(), [
            " at <short sha>",
            "Required reviews: <kind>=<state>, <kind>=<state>",
        ])
        case = watch_tests.load(os.path.join(watch_tests.V3_CASES, "review-high-both.json"))
        comments = case["github"]["repos/Habit130/tally/issues/42/comments"]
        comments[-1]["body"] = comments[-1]["body"].replace(
            "\n\nThe tier", "\n\nRerun-only pass: required CI; cause: https://github.com/Habit130/tally/issues/43\n\nThe tier")
        self.assertEqual(watch_tests.watch_v3.decide(
            case["event_name"], case["event"], watch_tests.agent_account(),
            watch_tests.recorded_v3(case["github"]),
        ), [])



class VersionThreeReviewProviders(VersionThreeRendered):
    """#148: requirements name responsibilities, the providers sit in one place each, and Bugbot is gone."""

    PROVIDER_NAMES = ("Codex review bot", "Copilot", "@codex", "(codex)", "(copilot)", "`codex`", "`copilot`")
    SUBSECTIONS = ("### The Codex review bot", "### Copilot code review")

    def rendered(self):
        found = {}
        for root, _, files in os.walk(self.dest):
            for name in files:
                full = os.path.join(root, name)
                found[os.path.relpath(full, self.dest)] = support.read_text(full)
        return found

    def review(self):
        return self.text("docs/agents/review.md")

    def without_provider_places(self, path, text):
        """The text with review.md's per-provider subsections and its example blocks taken out."""
        if path != "docs/agents/review.md":
            return text
        for heading in self.SUBSECTIONS:
            text = text.replace(heading + "\n" + level_three_section(text, heading), "")
        return re.sub(r"```text\n.*?\n *```", "", text, flags=re.S)

    def test_no_bugbot_name_trigger_or_file_is_rendered(self):
        files = self.rendered()
        self.assertNotIn(".cursor/BUGBOT.md", files)
        for path, text in files.items():
            for word in ("bugbot", "@cursor", "cursor review"):
                self.assertNotIn(word, text.lower(), path)

    def test_no_provider_is_named_outside_its_subsection_and_the_examples(self):
        for path, text in self.rendered().items():
            if not path.endswith(".md"):
                continue
            rest = self.without_provider_places(path, text)
            for name in self.PROVIDER_NAMES:
                self.assertNotIn(name, rest, path)
        review = self.review()
        for heading in self.SUBSECTIONS:
            section = flat(level_three_section(review, heading))
            for fact in ("**Name**", "**Request**", "**Wait**", "**Completed on the head**", "**Findings**"):
                self.assertIn(fact, section, heading)

    def test_minimum_reviews_name_slots_not_providers(self):
        table = level_two_section(self.review(), "## Minimum reviews", "review.md")
        row = [line for line in table.splitlines() if line.startswith("| Review bots |")]
        self.assertEqual(row, ["| Review bots | — | one: `bot-1` | two, from two providers: `bot-1` and `bot-2` |"])
        self.assertIn("Two results from one provider on one head fill one bot slot.", flat(table))

    def test_reviews_examples_parse_with_merge_watchs_parser(self):
        import test_merge_watch as watch_tests

        # The fixed header's own example ends the level-2 section early, so read the whole file.
        examples = re.findall(r"```text\n *## Merge summary: (low|medium|high) at [0-9a-f]{7}\n *(Required reviews: .*)\n",
                              self.review())
        self.assertEqual([tier for tier, _ in examples], ["high", "medium"])
        for tier, line in examples:
            self.assertIsNotNone(watch_tests.watch_v3.parse_reviews(line, tier), line)

    def test_the_waiver_form_is_the_one_merge_watch_reads(self):
        import test_merge_watch as watch_tests

        waivers = level_two_section(self.review(), "## Waivers", "review.md")
        (form,) = re.findall(r"```text\n *(Waiver: .*)\n", waivers)
        self.assertEqual(form, "Waiver: <item> at <full head sha> \u2014 <reason>")
        head = "1a954628a960aaef81d7b2d4521929579f3541e6"
        for item in ("self-verification", "bot-1", "bot-2", "reviewer", "security", 'verification "Plus a live check"'):
            line = form.replace("<item>", item).replace("<full head sha>", head).replace("<reason>", "why")
            self.assertIsNotNone(watch_tests.watch_v3.WAIVER.fullmatch(line), line)
        for never in ("required status checks", "`Risk:` line", "evidence comment", "Merge summary"):
            self.assertIn(never, waivers)
        for item in ("merge-summary", "risk", "governance-gate"):
            line = form.replace("<item>", item).replace("<full head sha>", head).replace("<reason>", "why")
            self.assertIsNone(watch_tests.watch_v3.WAIVER.fullmatch(line), line)

    def test_a_reviewer_waiver_keeps_copilot_from_judging_alone_and_names_the_summary_writer(self):
        review = self.review()
        waivers = flat(level_two_section(review, "## Waivers", "review.md"))
        self.assertIn("nor a Reviewer session that a review bot's subsection keeps", waivers)
        self.assertIn("A waived Reviewer session** leaves the Merge summary to the Builder", waivers)
        self.assertIn("and any condition a review bot's subsection puts on a Reviewer waiver", waivers)
        copilot = flat(level_three_section(review, "### Copilot code review"))
        self.assertIn("that session isn't waived while Copilot's is the head's only completed bot review (Waivers)", copilot)
        minimum = flat(level_two_section(review, "## Minimum reviews", "review.md"))
        self.assertIn("| Merge summary by | Builder | Reviewer, or the Builder when it is waived | Reviewer, or the "
                      "Builder when it is waived, as the high-risk report |", minimum)
        self.assertIn("a waived Reviewer session leaves the Merge summary to the Builder (Waivers)", minimum)
        summary = flat(review.split("\n## Merge summary\n", 1)[1].split("### Checks first", 1)[0])
        self.assertIn("by the Builder when habit waived the Reviewer session (Waivers)", summary)
        builder = flat(self.text("docs/agents/builder.md").split("9. **Hand over**:", 1)[1].split("## The Reviewer handoff", 1)[0])
        self.assertIn("or when habit waived the Reviewer session for this head (`review.md`, Waivers), write the Merge summary", builder)

    def test_the_exception_consistency_rule_is_stated_once_and_applied_in_review(self):
        agents = self.text(AGENTS)
        important = flat(agents.split("- **Important**", 1)[1].split("- **Nit**", 1)[0])
        self.assertIn("a review or authorization exception stated anywhere broader than at its narrowest", important)
        self.assertIn("(`review.md`, Exceptions)", important)
        rule = flat(level_two_section(self.review(), "## Exceptions", "review.md"))
        for phrase in ("decision point", "machine-read grammar", "examples", "reports", "Important finding"):
            self.assertIn(phrase, rule)

    def test_the_merge_summary_says_no_independent_reviewer_at_low_and_lists_waivers(self):
        terminal = flat(level_three_section(self.review(), "### In the terminal"))
        self.assertIn("no reviewer independent of the Builder looked at the change", terminal)
        self.assertIn("each waiver, with its item, reason and link, and each fallback", terminal)
        self.assertNotIn("link each review bot", terminal)



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

    def test_each_example_start_instruction_and_command_stands_alone_in_its_own_block(self):
        examples = level_two_section(self.text(self.HANDOFF), "## Examples", self.HANDOFF)
        blocks = re.findall(r"```text\n(.*?)\n *```", examples, re.S)
        copied = [b for b in blocks if re.search(r"^\s*(Role: |ghm )", b, re.M)]
        self.assertGreaterEqual(len(copied), 5, blocks)
        for block in copied:
            self.assertEqual(len([line for line in block.split("\n") if line.strip()]), 1, block)
        outside = re.sub(r"```text\n.*?\n *```", "", examples, flags=re.S)
        self.assertNotIn("Role: ", outside)
        self.assertNotIn("|", examples)

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

    def test_whole_spec_delivery_reaches_dispatch_labels_reviews_and_tiers(self):
        specs = flat(level_two_section(self.text("docs/agents/planner.md"), "## Specs", "planner.md"))
        self.assertIn("approved for whole-spec delivery is the exception: it keeps the label, its "
                      "tickets never take it", specs)
        labels = flat(self.text("docs/agents/triage-labels.md"))
        self.assertIn("unless habit approved it for whole-spec delivery: then the spec keeps it and its "
                      "tickets never take it", labels)
        tracker = flat(self.text("docs/agents/issue-tracker.md"))
        self.assertIn("A spec approved for whole-spec delivery is dispatched as one", tracker)
        shape = flat(level_two_section(self.text("docs/agents/planner.md"), "## Delivery shape", "planner.md"))
        self.assertIn("every ticket of that spec is high for that reason, since a high PR holds only its "
                      "high part", shape)
        reviewer = flat(self.text("docs/agents/reviewer.md"))
        self.assertIn("for a whole-spec PR, the spec and every ticket it closes", reviewer)
        self.assertIn("for a whole-spec PR, every ticket's", reviewer)
        builder = flat(self.text("docs/agents/builder.md"))
        self.assertIn("with the ticket as the spec (for a whole-spec delivery, the spec and every ticket)",
                      builder)
        self.assertIn("Verification is every ticket's", builder)

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
        self.assertIn("any shared resource it takes", talking)
        self.assertIn("never a list of options", talking)
