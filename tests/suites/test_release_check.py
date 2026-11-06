"""Seam E, the release check (#44 §11): the PR's base and head trees in, one line per rule out."""

import glob
import json
import os
import re
import shutil
import unittest

import support

CASES = sorted(glob.glob(os.path.join(support.FIXTURES, "release-check", "*.json")))
RULES = ["frozen", "consecutive", "notes", "note-fields", "fixtures"]
LINE = re.compile(r"^(PASS|FAIL) ([a-z-]+): .+$")


class CIConfiguration(unittest.TestCase):
    def test_ci_covers_prs_and_only_main_pushes(self):
        workflow = support.read_text(os.path.join(support.REPO, ".github", "workflows", "ci.yml"))
        # This deliberately pins the small event contract, not a general YAML parser.
        events = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertEqual(events.strip("\n"), "  pull_request:\n  push:\n    branches: [main]")
        permissions = workflow.split("\npermissions:\n", 1)[1].split("\njobs:", 1)[0]
        self.assertEqual(permissions.strip(), "contents: read")
        self.assertEqual(re.findall(r"^  ([a-z]+):$", workflow.split("\njobs:\n", 1)[1], re.M),
                         ["linux", "macos"])
        self.assertEqual(re.findall(r"^    name: (.+)$", workflow, re.M), ["linux", "macos"])
        self.assertEqual(re.findall(r"^        run: (.+)$", workflow, re.M), [
            "python3 tests/run.py stored-form",
            "python3 tests/run.py release-check --base HEAD^1 --head HEAD",
            "python3 tests/run.py suites --job linux",
            "/usr/bin/python3 tests/run.py py39",
            "/usr/bin/python3 tests/run.py suites --all",
        ])
        self.assertEqual(workflow.count("persist-credentials: false"), 2)


class ReleaseCheck(support.TempDirCase):
    def check_ci_history(self, shape):
        workflow = support.read_text(os.path.join(support.REPO, ".github", "workflows", "ci.yml"))
        linux = workflow.split("  linux:\n", 1)[1].split("  macos:\n", 1)[0]
        depth = re.search(r"fetch-depth: (\d+)", linux).group(1)
        command = re.search(r"run: python3 tests/run.py (release-check .+)", linux).group(1).split()
        with open(os.path.join(support.FIXTURES, "release-check", "released-template-edited.json")) as handle:
            case = json.load(handle)
        for frozen_edit in (False, True):
            with self.subTest(shape=shape, frozen_edit=frozen_edit):
                source = support.init_repo(self.path("source-" + str(frozen_edit)))
                root = support.commit_tree(source, case["base"], "released version")
                base_files = dict(case["base"], **{"main.txt": "intervening main change\n"})
                base = support.commit_tree(source, base_files, "advance main")
                support.git(source, "checkout", "-q", "-b", "feature", root)
                feature_files = dict(case["head"] if frozen_edit else case["base"])
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

                checkout = support.init_repo(self.path("checkout-" + str(frozen_edit)))
                # Local transport, but a real depth-limited fetch (not clone's local shortcut).
                support.git(checkout, "fetch", "--no-tags", "--depth=" + depth, source, ref)
                support.git(checkout, "checkout", "-q", "--detach", "FETCH_HEAD")
                self.assertEqual(support.git(checkout, "rev-parse", "--is-shallow-repository").strip(), "true")
                self.assertEqual(support.git(checkout, "rev-parse", "HEAD^1").strip(), base)
                self.assertEqual(support.git(checkout, "rev-parse", "HEAD").strip(), head)
                # CI's entry lives in its checkout; point this entry at the synthetic one.
                code, out, err = support.run_cli(support.RUN, command + ["--repo", checkout], cwd=checkout)
                self.assertEqual(code, 1 if frozen_edit else 0, out + err)
                self.assertEqual(err, "")
                failures = [line for line in out.splitlines() if line.startswith("FAIL ")]
                if frozen_edit:
                    self.assertEqual(len(failures), 1, out)
                    self.assertTrue(failures[0].startswith("FAIL frozen:"), out)
                    self.assertIn("templates/docs/agents/review.md", failures[0])
                else:
                    self.assertEqual(failures, [])
                    self.assertEqual(len([line for line in out.splitlines() if line.startswith("PASS ")]), 5)

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
                self.assertEqual(verdicts, case["expect"], out + err)
                failed = "FAIL" in case["expect"].values()
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


if __name__ == "__main__":
    unittest.main()
