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


class ReleaseCheck(support.TempDirCase):
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
