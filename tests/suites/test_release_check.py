"""Seam E, the release check (#44 §11): the PR's base and head trees in, one line per rule out."""

import glob
import json
import os
import re
import shutil
import unittest

import support

CASES = sorted(glob.glob(os.path.join(support.FIXTURES, "release-check", "*.json")))
RULES = ["frozen", "consecutive", "notes", "note-fields", "next-draft", "version-copy", "fixtures"]
LINE = re.compile(r"^(PASS|FAIL) ([a-z-]+): .+$")
RELEASE_AND_COPY = os.path.join(support.FIXTURES, "release-check", "release-and-copy.json")
REPOSITORY_SECTION_BUDGET = 6351


def edited(base, step):
    head = dict(base)
    prefix = "generator/govern-repository/store/"
    for path in step.get("remove", []):
        del head[prefix + path]
    for path, value in step.get("write", {}).items():
        head[prefix + path] = value
    return head


def draft_transitions():
    """Independent fixture edits, each paired with the prior complete tree."""
    with open(os.path.join(support.FIXTURES, "release-check", "new-version-without-note.json")) as handle:
        initial = json.load(handle)["base"]
    with open(os.path.join(support.FIXTURES, "release-check", "drafts", "lifecycle.json")) as handle:
        fixture = json.load(handle)

    base = initial
    for step in fixture["steps"]:
        head = edited(base, step)
        yield step["name"], base, head, step.get("failures", [])
        base = head
    # An all-released historical base still freezes v2, even though a new release must add v3.
    for step in fixture["after_release"]:
        yield step["name"], base, edited(base, step), ["frozen"]
    # Layout validation is independent of immutability; fixtures may override the v1 base.
    for step in fixture["invalid_layouts"]:
        head = edited(base, step)
        start = {"released-v1": initial, "empty": {}}[step.get("base", "released-v1")]
        yield step["name"], start, head, step["failures"]


class RepositoryInstructions(unittest.TestCase):
    def test_repeated_conditions_link_to_rendered_governance(self):
        # Row numbers and sections refer to the policy inventory on #229.
        cases = (
            (23, "AGENTS.md", "## This repository",
             ("each parallel writer, a subagent included, works in its own git worktree",),
             ("(`builder.md`, Whole-spec delivery and step 3).",)),
            (46, "AGENTS.md", "### Verification by change",
             ("rendered governance files change only through the generator",),
             ("[Governance files](#governance-files) for this repository's rendered governance.",)),
            (57, "AGENTS.md", "### Verification by change",
             ("All offline checks, CI, live checks, reviews and after-merge smoke remain required.",),
             ("Record checks under `review.md`, Evidence comment.",)),
            (58, "AGENTS.md", "### Verification by change",
             ("the Builder repairs it before handing over",),
             ("`review.md`, Minimum reviews, and `builder.md`, Escalations.",)),
            (28, "docs/build/releasing.md", "## Cut a version",
             ("try the next enabled bot only when the current one is unavailable",
              "the first confirmed bot for one slot",),
             ("choose the provider under [Review bots](../agents/review.md#review-bots)",
              "[On the PR](../agents/review.md#on-the-pr).",)),
            (59, "docs/build/generator.md", "# Generator command line",
             ("It leaves the confirmed values, which are the repository's own",),
             ("For changes to confirmed values, follow [Governance "
              "files](../../AGENTS.md#governance-files).",)),
            (60, "docs/build/generator.md", "# Generator command line",
             ("**The harness comes first** in all four",),
             ("**Harness eligibility** follows [How to start](../../AGENTS.md#how-to-start).",)),
            (27, "docs/build/live-checks.md", "## Merge watch",
             ("when Copilot alone completed a bot review on fixed content or an instruction file",),
             ("[Copilot code review](../agents/review.md#copilot-code-review) for the companion "
              "Reviewer",
              "proof for the companion Reviewer.",)),
            (29, "docs/build/live-checks.md", "## Merge watch",
             ("At Initialize it reads the introduced record after a confirmed path 404",
              "reads the policy version, agent account and ordered bots from the squash commit's "
              "parent",),
             ("[Review bots](../agents/review.md#review-bots) for enabled bot selection",
              "[Merge watch module contract](../../.github/governance/merge_watch.py) covers "
              "historical record resolution",)),
            (49, "docs/build/live-checks.md", "## Owner permission verification",
             ("The current gate still uses shared GitHub Actions App 15368",),
             ("For effective rules and recovery, follow [Checks "
              "first](../agents/review.md#checks-first).",)),
            (50, "docs/build/live-checks.md", "## Merge watch",
             ("Read back all 40 head digits on each v5 probe",),
             ("Read back each v5 probe's summary title and check it against "
              "[On the PR](../agents/review.md#on-the-pr).",
              "suite check the transition under the [module "
              "contract](../../.github/governance/merge_watch.py).",)),
            (52, "docs/build/live-checks.md", "## Merge watch",
             ("It compares comments, Reviewer statuses, Copilot submissions and check completions "
              "with the PR's merge time",),
             ("[Merge watch module contract](../../.github/governance/merge_watch.py) covers "
              "historical record resolution, reviewer identity, the evidence cutoff",)),
            (53, "docs/build/live-checks.md", "## The gate's live check",
             ("Its gate reads the PR from GitHub when it runs",
              "edit judges the current body",
              "a run that started before a push judges and posts on the newest head",),
             ("For the PR, policy and changed-path sources, see the [gate module "
              "contract](../../.github/governance/gate.py).",)),
            (68, "docs/build/live-checks.md", "## Merge watch",
             ("it never blocks anything and is never a required check",
              "it never blocks anything",
              "is never a required check",),
             ("its evidence and enforcement boundary, see the [Merge watch module "
              "contract](../../.github/governance/merge_watch.py).",)),
            (71, "docs/build/live-checks.md", "## The gate's live check",
             ("30 minutes for the Codex review bot, 15 for Copilot",),
             ("[Review bots](../agents/review.md#review-bots) for provider request steps, wait "
              "durations and the ordinary PR retry policy.",)),
            (43, "docs/build/testing.md", "## Parsers",
             ("requires the historical record to be a regular file in the parent tree",
              "GitHub must show a PR merged into the default branch whose squash commit is the named "
              "one",),
             ("follows step 3 in the [gate module contract](../../.github/governance/gate.py) for "
              "confirmation.",)),
            (54, "docs/build/testing.md", "## Parsers",
             ("the record reads it as an empty list",
              "doesn't parse unless double-quoted",),
             ("For scalar and empty-list syntax, use the [gate record "
              "grammar](../../.github/governance/gate.py).",)),
        )
        for row, path, heading, restatements, pointers in cases:
            with self.subTest(row=row, path=path, section=heading):
                text = support.read_text(os.path.join(support.REPO, path))
                if path == "AGENTS.md":
                    text = text.split("<!-- governance:end -->", 1)[1]
                _, found, section = ("\n" + text).partition(f"\n{heading}\n")
                self.assertTrue(found, f"Missing section: {heading}")
                section = re.split(r"\n#{1,6} ", section, maxsplit=1)[0]
                section = " ".join(section.split())
                for restatement in restatements:
                    self.assertFalse(restatement in section, f"Restatement remains: {restatement}")
                for pointer in pointers:
                    self.assertTrue(pointer in section, f"Missing pointer: {pointer}")

    def test_repository_section_fits_its_byte_budget(self):
        with open(os.path.join(support.REPO, "AGENTS.md"), "rb") as instructions:
            for line in instructions:
                if line.rstrip(b"\r\n") == b"<!-- governance:end -->":
                    break
            else:
                self.fail("AGENTS.md is missing its governance end marker")
            size = len(instructions.read())

        if size > REPOSITORY_SECTION_BUDGET:
            self.fail(
                f"AGENTS.md's repository section is {size} bytes, over its {REPOSITORY_SECTION_BUDGET}-byte budget: "
                "delete as much as you add, or raise the budget in the same PR with habit's approval quoted in its body."
            )


class CIConfiguration(unittest.TestCase):
    def test_ci_covers_prs_and_only_main_pushes(self):
        workflow = support.read_text(os.path.join(support.REPO, ".github", "workflows", "ci.yml"))
        # This deliberately pins the small event contract, not a general YAML parser.
        events = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertEqual(events.strip("\n"), "  pull_request:\n  push:\n    branches: [main]")
        permissions = workflow.split("\npermissions:\n", 1)[1].split("\njobs:", 1)[0]
        self.assertEqual(permissions.strip(), "contents: read")
        jobs = workflow.split("\njobs:\n", 1)[1]
        self.assertEqual(re.findall(r"^  ([a-z0-9-]+):$", jobs, re.M),
                         ["linux", "macos-shard-1", "macos-shard-2", "macos-shard-3", "macos"])
        self.assertEqual(re.findall(r"^    name: (.+)$", workflow, re.M),
                         ["linux", "macos shard 1 of 3", "macos shard 2 of 3", "macos shard 3 of 3", "macos"])
        self.assertEqual(re.findall(r"^    runs-on: (.+)$", workflow, re.M),
                         ["ubuntu-24.04", "macos-15", "macos-15", "macos-15", "ubuntu-24.04"])
        report = "printf 'report=%s\\n' \"$(cat \"$RUNNER_TEMP/shard.json\")\" >> \"$GITHUB_OUTPUT\""
        self.assertEqual(re.findall(r"^        run: (.+)$", workflow, re.M), [
            "python3 tests/run.py stored-form",
            "python3 tests/run.py release-check --base HEAD^1 --head HEAD",
            "python3 tests/run.py suites --job linux",
            "/usr/bin/python3 tests/run.py py39",
            "/usr/bin/python3 tests/run.py suites --all --shard 1/3 --report \"$RUNNER_TEMP/shard.json\"",
            report,
            "/usr/bin/python3 tests/run.py suites --all --shard 2/3 --report \"$RUNNER_TEMP/shard.json\"",
            report,
            "/usr/bin/python3 tests/run.py suites --all --shard 3/3 --report \"$RUNNER_TEMP/shard.json\"",
            report,
            'echo "shard 1 $SHARD_1, shard 2 $SHARD_2, shard 3 $SHARD_3"; '
            'test "$SHARD_1" = success && test "$SHARD_2" = success && test "$SHARD_3" = success',
            'python3 tests/run.py shard-check "$REPORT_1" "$REPORT_2" "$REPORT_3"',
        ])
        self.assertEqual(workflow.count("persist-credentials: false"), 5)
        # The required macos check runs after every shard outcome and passes only when every shard succeeded.
        aggregate = jobs.split("\n  macos:\n", 1)[1]
        self.assertIn("    needs: [macos-shard-1, macos-shard-2, macos-shard-3]\n    if: always()\n", aggregate)
        for index in ("1", "2", "3"):
            self.assertIn("SHARD_%s: ${{ needs.macos-shard-%s.result }}" % (index, index), aggregate)
            self.assertIn("REPORT_%s: ${{ needs.macos-shard-%s.outputs.report }}" % (index, index), aggregate)
        for shard in jobs.split("\n  macos-shard-")[1:]:
            self.assertIn("      report: ${{ steps.report.outputs.report }}", shard)
            self.assertIn("        id: report\n        if: always()\n", shard)


class ReleaseCheck(support.TempDirCase):
    def test_draft_lifecycle_and_invalid_layouts(self):
        repo = support.init_repo(self.path("lifecycle"))
        for name, base_files, head_files, failures in draft_transitions():
            with self.subTest(transition=name):
                base = support.commit_tree(repo, base_files, "before " + name)
                head = support.commit_tree(repo, head_files, name)
                code, out, err = support.run_cli(support.RUN, [
                    "release-check", "--repo", repo, "--base", base, "--head", head,
                ])
                self.assertEqual((code, err), (1 if failures else 0, ""), out)
                self.assertEqual([line.split()[1][:-1] for line in out.splitlines()
                                  if line.startswith("FAIL ")], failures, out)

    def check_ci_history(self, shape):
        workflow = support.read_text(os.path.join(support.REPO, ".github", "workflows", "ci.yml"))
        linux = workflow.split("  linux:\n", 1)[1].split("\n  macos-shard-1:\n", 1)[0]
        depth = re.search(r"fetch-depth: (\d+)", linux).group(1)
        command = re.search(r"run: python3 tests/run.py (release-check .+)", linux).group(1).split()
        with open(os.path.join(support.FIXTURES, "release-check", "released-template-edited.json")) as handle:
            case = json.load(handle)
        with open(RELEASE_AND_COPY) as handle:
            release = json.load(handle)
        cases = [("ordinary", case["base"], case["base"], []),
                 ("frozen-edit", case["base"], case["head"], ["frozen"]),
                 ("release-and-copy", release["base"], release["head"], [])]
        for step in release["other_cuts"]:
            cases.append((step["name"], release["base"], edited(release["head"], step), step["failures"]))
        cases += list(draft_transitions())
        for name, before, after, failures in cases:
            with self.subTest(shape=shape, transition=name):
                source = support.init_repo(self.path("source-" + name))
                root = support.commit_tree(source, before, "base version")
                base_files = dict(before, **{"main.txt": "intervening main change\n"})
                base = support.commit_tree(source, base_files, "advance main")
                support.git(source, "checkout", "-q", "-b", "feature", root)
                feature_files = dict(after)
                feature_files["feature.txt"] = "proposed change\n"
                feature = support.commit_tree(source, feature_files, "feature")
                support.git(source, "checkout", "-q", "main")
                if shape == "pr-merge":
                    support.git(source, "merge", "--no-ff", "-m", "PR merge", "feature")
                    ref = "refs/pull/1/merge"
                else:
                    support.git(source, "merge", "--squash", "feature")
                    support.git(source, "commit", "-q", "-m", "squash feature")
                    ref = "refs/heads/main"
                head = support.git(source, "rev-parse", "HEAD").strip()
                parents = support.git(source, "show", "-s", "--format=%P", head).split()
                self.assertEqual(parents, [base, feature] if shape == "pr-merge" else [base])
                support.git(source, "update-ref", ref, head)

                checkout = support.init_repo(self.path("checkout-" + name))
                # Local transport, but a real depth-limited fetch (not clone's local shortcut).
                support.git(checkout, "fetch", "--no-tags", "--depth=" + depth, source, ref)
                support.git(checkout, "checkout", "-q", "--detach", "FETCH_HEAD")
                self.assertEqual(support.git(checkout, "rev-parse", "--is-shallow-repository").strip(), "true")
                self.assertEqual(support.git(checkout, "rev-parse", "HEAD^1").strip(), base)
                self.assertEqual(support.git(checkout, "rev-parse", "HEAD").strip(), head)
                # CI's entry lives in its checkout; point this entry at the synthetic one.
                code, out, err = support.run_cli(support.RUN, command + ["--repo", checkout], cwd=checkout)
                self.assertEqual(code, 1 if failures else 0, out + err)
                self.assertEqual(err, "")
                self.assertEqual([line.split()[1][:-1] for line in out.splitlines()
                                  if line.startswith("FAIL ")], failures, out)
                self.assertEqual(len([line for line in out.splitlines() if line.startswith("PASS ")]),
                                 len(RULES) - len(failures))
                if name == "frozen-edit":
                    frozen = next(line for line in out.splitlines() if line.startswith("FAIL frozen:"))
                    self.assertIn("templates/docs/agents/review.md", frozen)
                if name == "release":
                    self.assertRegex(out, r"(?m)^FAIL next-draft: .*\bdraft version 3\b")

    def test_depth_two_pr_merge_compares_first_parent_and_rejects_frozen_edit(self):
        self.check_ci_history("pr-merge")

    def test_depth_two_squash_push_compares_previous_main_and_rejects_frozen_edit(self):
        self.check_ci_history("squash-push")

    def run_case(self, case):
        repo = support.init_repo(self.path("repo"))
        base = support.commit_tree(repo, case["base"], "base")
        head = support.commit_tree(repo, case["head"], "head")
        return support.run_cli(support.RUN, ["release-check", "--repo", repo, "--base", base, "--head", head])

    def test_every_seam_e_fixture(self):
        self.assertGreaterEqual(len(CASES), 8)
        for path in CASES:
            name = os.path.basename(path)
            with open(path) as handle:
                case = json.load(handle)
            with self.subTest(case=name):
                code, out, err = self.run_case(case)
                verdicts = {}
                info = {}
                for line in out.splitlines():
                    match = LINE.match(line)
                    if match:
                        self.assertNotIn(match.group(2), verdicts, "rule printed twice: " + line)
                        verdicts[match.group(2)] = match.group(1)
                    elif line.startswith("INFO "):
                        key, _, value = line[len("INFO "):].partition(" fixtures: ")
                        info[key] = [] if value == "none" else value.split(", ")
                    else:
                        self.fail("unexpected line %r in %s" % (line, name))
                expected = {"next-draft": "PASS", "version-copy": "PASS", **case["expect"]}
                self.assertEqual(verdicts, expected, out + err)
                failed = "FAIL" in expected.values()
                self.assertEqual(code, 1 if failed else 0, out + err)
                if "expect_info" in case:
                    self.assertEqual(info, case["expect_info"], out)
                shutil.rmtree(os.path.join(self.tmp, "repo"))

    def test_names_what_changed_in_a_released_version(self):
        with open(os.path.join(support.FIXTURES, "release-check", "released-template-edited.json")) as handle:
            case = json.load(handle)
        code, out, _ = self.run_case(case)
        self.assertEqual(code, 1)
        self.assertIn("templates/docs/agents/review.md", out)

    def test_names_first_difference_in_an_added_version(self):
        with open(RELEASE_AND_COPY) as handle:
            case = json.load(handle)
        for step in case["mismatches"]:
            with self.subTest(difference=step["name"]):
                code, out, err = self.run_case(dict(case, head=edited(case["head"], step)))
                self.assertEqual((code, err), (1, ""), out)
                self.assertEqual(
                    [line for line in out.splitlines() if line.startswith("FAIL ")],
                    ["FAIL version-copy: version 2 differs from version 1 at %r" % step["first_difference"]],
                    out,
                )


if __name__ == "__main__":
    unittest.main()
