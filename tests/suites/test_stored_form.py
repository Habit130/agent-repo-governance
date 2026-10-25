"""Stored form (#44 §3): the reversible encoding that keeps stored files from loading."""

import os
import unittest

import support
from govlib import storedform


class EncodingRoundTrip(unittest.TestCase):
    CASES = [
        (".github/workflows/ci.yml", "dot-github/workflows/ci.yml"),
        (".cursor/BUGBOT.md", "dot-cursor/BUGBOT.md"),
        ("AGENTS.md", "AGENTS.md.stored"),
        ("src/nested/AGENTS.override.md", "src/nested/AGENTS.override.md.stored"),
        (".claude/CLAUDE.md", "dot-claude/CLAUDE.md.stored"),
        ("CLAUDE.local.md", "CLAUDE.local.md.stored"),
        ("opencode.json", "opencode.json.stored"),
        (".opencode/opencode.jsonc", "dot-opencode/opencode.jsonc.stored"),
        (".gitignore", "dot-gitignore"),
        (".dot-files/x", "dot-dot-files/x"),
        ("docs/agents/build.md", "docs/agents/build.md"),
        ("scripts/release.sh", "scripts/release.sh"),
    ]

    def test_encode_matches_the_spec_examples(self):
        for real, stored in self.CASES:
            self.assertEqual(storedform.encode(real), stored, real)

    def test_decode_reverses_encode(self):
        for real, stored in self.CASES:
            self.assertEqual(storedform.decode(stored), real, stored)

    def test_loaded_names_match_whatever_their_case(self):
        # macOS's default file system ignores case, so `claude.md` opens as `CLAUDE.md`.
        self.assertEqual(storedform.encode("docs/claude.md"), "docs/claude.md.stored")
        self.assertEqual(storedform.decode("docs/claude.md.stored"), "docs/claude.md")

    def test_encoder_refuses_names_that_would_decode_wrongly(self):
        for real in ["dot-github/x.yml", "a/dot-b/c", "notes.stored", "a/b.stored/c", "AGENTS.md.stored"]:
            with self.assertRaises(storedform.StoredFormError, msg=real):
                storedform.encode(real)

    def test_encoder_refuses_paths_that_are_not_plain_relative_paths(self):
        for real in ["/etc/passwd", "a/../b", "./a", "a//b", "", "a/"]:
            with self.assertRaises(storedform.StoredFormError, msg=real):
                storedform.encode(real)

    def test_decoder_refuses_paths_encode_never_produces(self):
        for stored in [".github/x", "AGENTS.md", "notes.txt.stored", "dot-", "dot-.", "a/dot-./b", "a//b"]:
            with self.assertRaises(storedform.StoredFormError, msg=stored):
                storedform.decode(stored)

    def test_problems_name_a_dot_segment_and_a_loaded_name(self):
        self.assertEqual(storedform.problems("tests/fixtures/dot-github/ci.yml"), [])
        self.assertTrue(storedform.problems("tests/fixtures/.github/ci.yml"))
        self.assertTrue(storedform.problems("tests/fixtures/repo/AGENTS.md"))
        self.assertTrue(storedform.problems("tests/fixtures/repo/notes.md.stored"))


class Materializing(support.TempDirCase):
    def make_stored_tree(self):
        source = self.path("stored")
        support.write_tree(
            source,
            {
                "dot-github/workflows/ci.yml": "on: pull_request\n",
                "AGENTS.md.stored": "# Agents\n",
                "scripts/release.sh": {"content": "#!/bin/bash\necho release\n", "mode": "100755"},
            },
        )
        return source

    def test_restores_paths_and_executable_bits_into_a_temporary_directory(self):
        source = self.make_stored_tree()
        dest = self.path("out")
        code, facts = support.govern(["materialize", "--source", source, "--dest", dest])
        self.assertEqual(code, 0, facts)
        self.assertEqual(
            sorted(facts["written"]),
            [".github/workflows/ci.yml", "AGENTS.md", "scripts/release.sh"],
        )
        self.assertEqual(support.read_text(os.path.join(dest, "AGENTS.md")), "# Agents\n")
        self.assertEqual(support.file_mode(os.path.join(dest, "scripts", "release.sh")), "100755")
        self.assertEqual(support.file_mode(os.path.join(dest, ".github", "workflows", "ci.yml")), "100644")

    def test_writes_into_a_target_worktree(self):
        source = self.make_stored_tree()
        tmpdir = self.path("tmpdir")
        os.makedirs(tmpdir)
        target = support.init_repo(self.path("target"))
        env = support.isolated_env({"TMPDIR": tmpdir})
        code, facts = support.govern(["materialize", "--source", source, "--dest", target], env=env)
        self.assertEqual(code, 0, facts)
        self.assertTrue(os.path.isfile(os.path.join(target, ".github", "workflows", "ci.yml")))

    def test_refuses_a_destination_that_is_neither_temporary_nor_a_worktree(self):
        source = self.make_stored_tree()
        tmpdir = self.path("tmpdir")
        os.makedirs(tmpdir)
        env = support.isolated_env({"TMPDIR": tmpdir})
        elsewhere = self.path("elsewhere")
        code, facts = support.govern(["materialize", "--source", source, "--dest", elsewhere], env=env)
        self.assertNotEqual(code, 0)
        self.assertIn("temporary directory", facts["error"])
        self.assertFalse(os.path.exists(os.path.join(elsewhere, "AGENTS.md")))

    def test_refuses_a_subdirectory_of_a_worktree(self):
        source = self.make_stored_tree()
        tmpdir = self.path("tmpdir")
        os.makedirs(tmpdir)
        target = support.init_repo(self.path("target"))
        env = support.isolated_env({"TMPDIR": tmpdir})
        code, facts = support.govern(
            ["materialize", "--source", source, "--dest", os.path.join(target, "sub")], env=env
        )
        self.assertNotEqual(code, 0)
        self.assertIn("worktree", facts["error"])

    def test_refuses_a_target_whose_parent_is_a_symlink_and_writes_nothing(self):
        source = self.make_stored_tree()
        outside = self.path("outside")
        os.makedirs(outside)
        dest = self.path("out")
        os.makedirs(dest)
        os.symlink(outside, os.path.join(dest, "scripts"))
        code, facts = support.govern(["materialize", "--source", source, "--dest", dest])
        self.assertEqual(code, 2, facts)
        self.assertIn("symlink", facts["error"])
        self.assertEqual(os.listdir(outside), [])
        self.assertFalse(os.path.exists(os.path.join(dest, "AGENTS.md")))

    def test_refuses_a_stored_tree_holding_a_path_that_does_not_decode(self):
        source = self.path("stored")
        support.write_tree(source, {"dot-github/ok.yml": "x\n", "notes.txt.stored": "y\n"})
        code, facts = support.govern(["materialize", "--source", source, "--dest", self.path("out")])
        self.assertNotEqual(code, 0)
        self.assertIn("notes.txt.stored", facts["error"])
        self.assertFalse(os.path.exists(self.path("out", ".github", "ok.yml")))


class StoredFormCheck(support.TempDirCase):
    """The CI check fails on any stored path with a dot segment or a loaded name."""

    def check(self, repo):
        return support.run_cli(support.RUN, ["stored-form", "--repo", repo])

    def test_passes_a_clean_tree(self):
        repo = support.init_repo(self.path("repo"))
        support.write_tree(
            repo,
            {
                ".github/workflows/ci.yml": "on: pull_request\n",
                "AGENTS.md": "# Outside the four areas, so not stored\n",
                "tests/fixtures/repo/dot-github/ci.yml": "x\n",
                "tests/fixtures/repo/AGENTS.md.stored": "x\n",
                "generator/govern-repository/scripts/govern.py": "x\n",
            },
        )
        support.git(repo, "add", "-A")
        code, out, err = self.check(repo)
        self.assertEqual(code, 0, out + err)
        self.assertIn("PASS", out)

    def test_fails_on_a_planted_dot_segment_and_a_planted_loaded_name(self):
        repo = support.init_repo(self.path("repo"))
        support.write_tree(
            repo,
            {
                "tests/fixtures/repo/.github/workflows/ci.yml": "x\n",
                "skill-copies/tdd/AGENTS.md": "x\n",
                "machine/notes.txt.stored": "x\n",
                "generator/ok.py": "x\n",
            },
        )
        support.git(repo, "add", "-A")
        code, out, err = self.check(repo)
        self.assertEqual(code, 1, out + err)
        self.assertIn("FAIL", out)
        self.assertIn("tests/fixtures/repo/.github/workflows/ci.yml", out)
        self.assertIn("skill-copies/tdd/AGENTS.md", out)
        self.assertIn("machine/notes.txt.stored", out)
        self.assertNotIn("generator/ok.py", out)


if __name__ == "__main__":
    unittest.main()
