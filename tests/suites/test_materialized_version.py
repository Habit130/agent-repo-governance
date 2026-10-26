"""Materialized version 1 (#41 seam 3, through #44's rendering and exact comparison).

Version 1 renders from the real store into the tally sample repository, then exact
comparison runs on the result. #41's template tickets add their seam-3 checks here.
"""

import os
import unittest

import materialized
import support


class MaterializedVersionOne(support.TempDirCase):
    def setUp(self):
        super(MaterializedVersionOne, self).setUp()
        self.worktree, self.render_facts = materialized.render_version_one(self.tmp)

    def test_exact_comparison_finds_no_difference(self):
        code, facts = materialized.compare_version_one(self.worktree)
        self.assertEqual(code, 0, facts)
        self.assertEqual(facts["differences"], [])
        self.assertEqual((facts["repository"], facts["default_branch"]), ("Habit130/tally", "main"))

    def test_rendering_writes_only_the_versions_templates(self):
        status = support.git(self.worktree, "status", "--porcelain", "--untracked-files=all")
        changed = sorted(line[3:] for line in status.splitlines())
        self.assertEqual(changed, sorted(self.render_facts["written"]))

    def test_tally_keeps_its_own_files_and_modes(self):
        self.assertEqual(support.file_mode(os.path.join(self.worktree, "scripts", "release.sh")), "100755")
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, ".github", "workflows", "ci.yml")))
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, ".gitignore")))

    # #41's template tickets add their seam-3 checks below, against self.worktree.


if __name__ == "__main__":
    unittest.main()
