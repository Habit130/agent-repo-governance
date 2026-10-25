"""Exact comparison (#44 §4, ADR 0015): content and mode of every fixed file and fixed part."""

import os
import unittest

import support
from test_render import VALUES, RenderCase


class ExactComparison(RenderCase):
    def rendered(self, released=True):
        self.store = self.store_copy(released=released)
        dest = support.init_repo(self.path("worktree"))
        extra = [] if released else ["--version", "1", "--allow-unreleased"]
        code, facts = self.render(self.store, dest, extra=extra)
        self.assertEqual(code, 0, facts)
        return dest

    def compare(self, worktree, extra=VALUES):
        return support.govern(["compare", "--store", self.store, "--worktree", worktree] + list(extra))

    def edit(self, worktree, path, old, new):
        full = os.path.join(worktree, *path.split("/"))
        text = support.read_text(full)
        self.assertIn(old, text)
        with open(full, "w") as handle:
            handle.write(text.replace(old, new))

    def test_a_fresh_render_has_no_differences(self):
        worktree = self.rendered()
        code, facts = self.compare(worktree)
        self.assertEqual(code, 0, facts)
        self.assertEqual(facts["differences"], [])
        self.assertEqual(
            sorted(facts["checked"]),
            [".claude/CLAUDE.md", ".github/governance/owner.sh", "AGENTS.md", "docs/agents/review.md"],
        )
        self.assertEqual(
            facts["not_compared"],
            {
                ".github/governance/record.yml": "record: its confirmed values are the repository's own",
                "docs/agents/build.md": "skeleton: repository-owned content",
            },
        )

    def test_names_an_edited_fixed_file(self):
        worktree = self.rendered()
        self.edit(worktree, "docs/agents/review.md", "run against `main`", "run against `trunk`")
        code, facts = self.compare(worktree)
        self.assertEqual(code, 1, facts)
        self.assertEqual(
            facts["differences"],
            [{"path": "docs/agents/review.md", "class": "fixed", "kind": "content", "detail": "first difference at line 5"}],
        )

    def test_names_a_changed_mode(self):
        worktree = self.rendered()
        os.chmod(os.path.join(worktree, ".github", "governance", "owner.sh"), 0o644)
        code, facts = self.compare(worktree)
        self.assertEqual(code, 1, facts)
        self.assertEqual(
            facts["differences"],
            [
                {
                    "path": ".github/governance/owner.sh",
                    "class": "fixed",
                    "kind": "mode",
                    "detail": "expected 100755, found 100644",
                }
            ],
        )

    def test_names_edited_text_inside_markers_but_not_outside(self):
        worktree = self.rendered()
        self.edit(worktree, "AGENTS.md", "## This repository\n", "## This repository\n\nA carried rule.\n")
        code, facts = self.compare(worktree)
        self.assertEqual((code, facts["differences"]), (0, []), facts)

        self.edit(worktree, "AGENTS.md", "Only the generator changes", "Anyone changes")
        code, facts = self.compare(worktree)
        self.assertEqual(code, 1, facts)
        self.assertEqual(
            facts["differences"],
            [{"path": "AGENTS.md", "class": "fixed part", "kind": "content", "detail": "first difference at line 4"}],
        )

    def test_names_every_difference_at_once(self):
        worktree = self.rendered()
        os.remove(os.path.join(worktree, "docs", "agents", "review.md"))
        self.edit(worktree, ".claude/CLAUDE.md", "<!-- governance:end -->\n", "")
        os.chmod(os.path.join(worktree, ".github", "governance", "owner.sh"), 0o644)
        self.edit(worktree, ".github/governance/owner.sh", "echo", "printf")
        code, facts = self.compare(worktree)
        self.assertEqual(code, 1, facts)
        kinds = [(d["path"], d["kind"]) for d in facts["differences"]]
        self.assertEqual(
            kinds,
            [
                (".claude/CLAUDE.md", "markers"),
                (".github/governance/owner.sh", "content"),
                (".github/governance/owner.sh", "mode"),
                ("docs/agents/review.md", "missing"),
            ],
        )

    def test_ignores_the_record_and_skeletons(self):
        worktree = self.rendered()
        self.edit(worktree, ".github/governance/record.yml", '"test"', '"lint"')
        self.edit(worktree, "docs/agents/build.md", "# Build", "# Build and test")
        code, facts = self.compare(worktree)
        self.assertEqual((code, facts["differences"]), (0, []), facts)

    def test_runs_as_one_command_in_any_worktree_reading_values_from_origin(self):
        worktree = self.rendered()
        support.git(worktree, "remote", "add", "origin", "https://github.com/Habit130/tally.git")
        support.git(worktree, "add", "-A")
        support.git(worktree, "commit", "-q", "-m", "governance")
        support.git(worktree, "update-ref", "refs/remotes/origin/main", "HEAD")
        support.git(worktree, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        detached = self.path("detached")
        support.git(worktree, "worktree", "add", "-q", "--detach", detached, "HEAD")
        code, facts = self.compare(detached, extra=[])
        self.assertEqual(code, 0, facts)
        self.assertEqual((facts["repository"], facts["default_branch"]), ("Habit130/tally", "main"))

    def test_an_unreleased_version_is_compared_only_when_asked(self):
        worktree = self.rendered(released=False)
        code, facts = self.compare(worktree, extra=VALUES + ["--version", "1"])
        self.assertEqual(code, 2)
        self.assertIn("not released", facts["error"])
        code, facts = self.compare(worktree, extra=VALUES + ["--version", "1", "--allow-unreleased"])
        self.assertEqual((code, facts["differences"]), (0, []), facts)


if __name__ == "__main__":
    unittest.main()
