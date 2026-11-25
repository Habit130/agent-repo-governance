"""Governance model version five, the unpublished draft: rendered policy-text checks."""

import json
import os
import re
import shlex
import subprocess
import tempfile
from textwrap import dedent

from materialized_version_support import VersionThreeRendered, flat, level_three_section, level_two_section
from merge_watch_history import RecordedMerge


class VersionFiveCopilotCompletion(RecordedMerge):
    def test_copilot_completion_requires_success_from_its_own_workflow(self):
        self.replay()
        self.check["conclusion"] = "failure"
        self.replay(missing=("bot-1",))
        self.check["conclusion"] = "success"
        self.run["path"] = ".github/workflows/other.yml"
        self.replay(missing=("bot-1",))

        copilot = level_three_section(self.text("docs/agents/review.md"), "### Copilot code review")
        completion = flat(copilot.split("- **Completed on the head**:", 1)[1].split("\n- ", 1)[0])
        self.assertIn("count Copilot's submitted review (`is_copilot_code_review` true, `commit_id` "
                      "equal to the head) only with a completed `copilot-pull-request-reviewer` "
                      "check run whose `conclusion` is `success`", completion)
        self.assertIn("Verify the check came from Copilot's dynamic Actions workflow by matching "
                      "the head, linked job and check suite.", completion)
        self.assertNotIn("beside a completed `copilot-pull-request-reviewer` check run on the head", completion)


class VersionFiveCodexPRWait(VersionThreeRendered):
    """#286: rendered wait routing, not the installed skill's operations or model behavior."""

    VERSION = 5

    def test_desktop_local_pr_waits_choose_the_available_skill_or_the_existing_fallback(self):
        agents = self.text("AGENTS.md")
        start = flat(level_two_section(agents, "## How to start", "AGENTS.md"))
        codex = start.split("**Codex harness**:", 1)[1]
        self.assertIn(
            "For a Codex Desktop Local Builder or Reviewer waiting on a PR, use the installed "
            "`wait-on-pr` skill when available; if unavailable, poll within that limit or stop "
            "and say what the session is waiting for.", codex)
        self.assertIn("Each poll waits at most 5 minutes.", codex)
        self.assertEqual(agents.count("`wait-on-pr`"), 1)

    def test_cli_and_other_harness_instructions_preserve_the_released_policy(self):
        import support

        prior = self.path("version-four")
        code, facts = support.govern([
            "render", "--version", "4", "--dest", prior,
            "--repository", "Habit130/tally", "--default-branch", "main",
            "--confirmed", self.path("confirmed.json"),
        ])
        self.assertEqual(code, 0, facts)
        previous = support.read_text(os.path.join(prior, "AGENTS.md"))
        previous_start = flat(level_two_section(previous, "## How to start", "AGENTS.md"))
        start = flat(level_two_section(self.text("AGENTS.md"), "## How to start", "AGENTS.md"))
        self.assertEqual(start.split(" For a Codex Desktop Local ", 1)[0], previous_start)


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

    def test_high_report_waits_for_the_builders_answer_to_each_finding(self):
        checks = flat(level_three_section(self.text("docs/agents/review.md"), "### Checks first"))
        for requirement in (
            "At high, match each finding on the reviewed head, including Nits, to the Builder's answer on GitHub",
            "A successful `Reviewer` status, a resolved thread or a mention in the report cannot supply it",
            "If any answer is missing, hold both the high-risk report and the pinned merge command",
            "Wait as the harness permits, then reread the PR",
            "If the head changed, follow Rounds",
            "a reasoned answer to keep the current behavior can settle a Nit without a repair push",
            "Once all answers are present and the other merge requirements pass, publish the report",
            "link each disposition to the Builder's answer",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, checks)

    def test_reviewer_outputs_route_publication_to_the_merge_summary_checks(self):
        outputs = flat(level_two_section(self.text("docs/agents/reviewer.md"), "## Outputs", "reviewer.md"))
        self.assertIn("`failure` while an Important finding is open, `success` otherwise", outputs)
        self.assertIn("[Checks first](review.md#checks-first) before publishing the Merge summary", outputs)
        self.assertIn("[The merge handoff](review.md#the-merge-handoff)", outputs)
        self.assertNotIn("**When clear**", outputs)

    def test_reviewer_start_leaves_publication_timing_to_outputs(self):
        start = flat(level_two_section(self.text("docs/agents/reviewer.md"), "## Start", "reviewer.md"))
        instruction_end = "Reviewer status and, when clear, the Merge summary.`"
        self.assertIn(instruction_end, start)
        guidance = start.split(instruction_end, 1)[1]
        self.assertIn("[Outputs](#outputs)", guidance)
        self.assertNotIn("when clear", guidance)

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
                    check_rule = next(rule for rule in rules if rule["type"] == "required_status_checks")
                    if "checks_rule_id" in row:
                        check_rule["ruleset_id"] = row["checks_rule_id"]
                    if "checks" in row:
                        check_rule["parameters"] = {"required_status_checks": row["checks"]}
                    rules.append({"type": "update", "ruleset_id": row.get("merge_rule_id", 42)})
                    branch_read = ["api", "--paginate", "--slurp", "repos/Habit130/tally/rules/branches/release%2Fcurrent"]
                    response = (ow.http_error(branch_read, row["http_error"], row.get("message", "Unavailable"))
                                if "http_error" in row else ow.ok(branch_read, [rules[:2], rules[2:]]))
                    gate_meta = dict(listed[0], name=row.get("gate_name", "Gate"), target=row.get("gate_target", "branch"),
                                     enforcement=row.get("gate_enforcement", "active"))
                    other_meta = dict(listed[2], name=row.get("other_name", "Other"))
                    calls = [
                        ow.ok(["api", "repos/{owner}/{repo}"],
                              {"full_name": "Habit130/tally", "visibility": visibility.lower(), "default_branch": branch}),
                        ow.ok(["api", "--paginate", "--slurp", "repos/Habit130/tally/rulesets?includes_parents=false"],
                              [[gate_meta], [listed[1], other_meta]]),
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


class VersionFiveBuilderMergeWait(VersionThreeRendered):
    """#269: the original high Builder's merge evidence and handoffs."""

    VERSION = 5

    def after_merge(self):
        return flat(level_two_section(self.text("docs/agents/builder.md"), "## After merge", "builder.md"))

    def test_build_skeleton_routes_smoke_without_default_branch_product_ci(self):
        self.assertIn("Otherwise state its absence; a high-risk ticket must have predetermined an "
                      "executable local smoke, which runs on that exact commit.", self.after_merge())
        tickets = level_two_section(self.text("docs/agents/planner.md"), "## Tickets", "planner.md")
        self.assertIn("At high, identify actual default-branch product verification; when none "
                      "exists, predetermine an executable local smoke on the exact merged commit", flat(tickets))
        ci = flat(level_two_section(self.text("docs/agents/build.md"), "## CI", "build.md"))
        self.assertIn("For smoke without default-branch product CI, follow `builder.md`, After merge.", ci)
        self.assertNotIn("there is no smoke check", ci)

    def test_returned_wait_requires_the_intended_merge_before_verification(self):
        rule = self.after_merge()
        self.assertIn("At high, when its permitted in-session wait returns, the original Builder", rule)
        self.assertIn("closed without merge, an unrelated event or a mismatched identity, "
                      "report the discrepancy and stop", rule)
        self.assertNotIn('habit says "merged"', rule)
        merged_pr = rule.partition("- If GitHub shows a merge,")[2].split(" - ", 1)[0]
        for condition in (
            "habit merged it into the intended default branch",
            "the full PR head SHA at merge matches the reviewed head pinned for habit",
            "GitHub identifies the resulting squash commit",
            "Only then begin verification without another message from habit",
        ):
            with self.subTest(condition=condition):
                self.assertIn(condition, merged_pr)

    def test_open_pr_distinguishes_an_unanswered_nit_from_its_answered_control(self):
        import support

        with open(os.path.join(support.FIXTURES, "generator", "v5-builder-open-pr.json")) as handle:
            fixture = json.load(handle)
        section = level_two_section(self.text("docs/agents/builder.md"), "## After merge", "builder.md")
        high = next(bullet for bullet in section.split("\n- ") if bullet.startswith("At high, when"))
        branches = high.split("\n  - ")
        self.assertIn("read the intended repository and PR number on GitHub", flat(branches[0]))
        open_pr = next((branch for branch in branches[1:] if branch.startswith("If the PR is open,")), "")
        condition, *actions = map(flat, open_pr.split("\n    - "))
        self.assertEqual(condition, fixture["open_pr"])
        for case, action in fixture["cases"].items():
            with self.subTest(case=case):
                self.assertIn(action, actions)
        self.assertEqual(len(actions), len(fixture["cases"]))

    def test_stopped_builder_keeps_its_worktree_and_rechecks_on_manual_continuation(self):
        rule = self.after_merge()
        self.assertIn("unsupported or interrupted, or the GitHub read is inconclusive", rule)
        self.assertIn("say what evidence is pending, keep your worktree and stop", rule)
        self.assertIn('habit may say “继续” (continue) in the original Builder chat', rule)
        self.assertIn("repeat the same GitHub checks, including the open-PR branch", rule)
        self.assertIn("Other sessions leave that chat and its worktree alone", rule)
        self.assertIn("Never ask habit to return just for cleanup", rule)
        wait = level_two_section(self.text("docs/agents/builder.md"), "## Syncing and waiting", "builder.md")
        self.assertIn("For the high Builder waiting for merge, follow After merge", flat(wait))

    def test_review_and_smoke_use_their_own_commits_before_any_one_way_door(self):
        rule = self.after_merge()
        self.assertIn("for the PR's exact head at merge: each required review's result, the Comment "
                      "review and `Reviewer` status when a Reviewer ran, and the Merge summary", rule)
        self.assertIn("If required evidence is missing, report the gap and escalate", rule)
        self.assertIn("**Product smoke** verifies the resulting squash commit", rule)
        self.assertIn("default-branch product build or test CI exists, confirm its run for that commit passes", rule)
        self.assertIn("predetermined an executable local smoke, which runs on that exact commit", rule)
        self.assertIn("Also run any additional smoke the ticket requires", rule)
        self.assertIn("A failing or unavailable required smoke leaves delivery incomplete", rule)
        self.assertIn("after product smoke passes, ask habit's go-ahead for each one-way-door step, one at a time", rule)

    def test_high_handoffs_give_habit_the_action_for_the_original_builders_wait(self):
        merge = flat(level_three_section(self.text("docs/agents/review.md"), "### The merge handoff"))
        self.assertIn("--squash --match-head-commit <sha>`, with the full head SHA", merge)
        self.assertIn("original Builder's wait state (`builder.md`, After merge)", merge)
        self.assertIn("A waiting Builder needs no reply", merge)
        self.assertIn("If it stopped under the wait fallback, habit may say “继续” in that chat for the same checks", merge)
        self.assertNotIn("say merged in the Builder's terminal", merge)

        examples = self.text("docs/agents/handoff.md").split("A Builder's final handoff to a Reviewer, at high.", 1)[1]
        high = examples.split("A substituting Reviewer's final handoff", 1)[0]
        self.assertIn("核实 GitHub 合并记录后开始验证，无需回复", high)
        self.assertIn("worktree 已保留", high)
        self.assertIn("回到本 chat 说“继续”，Builder 会重新核对 GitHub", high)
        self.assertNotIn("说“merged”", high)

    def test_builder_gives_the_merge_handoff_whenever_it_writes_the_summary(self):
        review = self.text("docs/agents/review.md")
        waivers = flat(level_two_section(review, "## Waivers", "review.md"))
        self.assertIn("**A waived Reviewer session** leaves the Merge summary to the Builder: "
                      "it runs the checks, writes the summary, at high as the high-risk report, "
                      "and gives the merge handoff.", waivers)
        merge = flat(level_three_section(review, "### The merge handoff"))
        self.assertIn("after the summary, as its writer's final handoff", merge)
        handoff = level_two_section(self.text("docs/agents/handoff.md"), "## A final handoff", "handoff.md")
        builder = flat(handoff.split("- **Builder**:", 1)[1].split("\n- ", 1)[0])
        self.assertIn("after writing the Merge summary at any tier (`review.md`, The merge handoff)", builder)
        self.assertNotIn("at low and medium, after its Merge summary", builder)


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
