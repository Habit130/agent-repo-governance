"""The version 6 consolidation test at #309's rendered-policy seam."""

import os
from unittest import mock

import support
from govlib import render
from materialized_version_support import VersionThreeRendered, flat
from policy_rows_312 import ROWS as ROWS_312
from policy_rows_317 import ROWS as ROWS_317
from policy_rows_318 import MERGE, SANDBOXES, sandbox_names
from policy_rows_318 import ROWS as ROWS_318
from policy_rows_319 import ROWS as ROWS_319


ROWS = (*ROWS_312, *ROWS_317, *ROWS_318, *ROWS_319)


class VersionSixPolicy(VersionThreeRendered):
    VERSION = 6

    def test_consolidated_conditions(self):
        for row in ROWS:
            for role, clauses in (
                ("home", row.home),
                ("pointer", row.pointers),
                ("red", row.red),
                *row.branches,
            ):
                for clause in clauses:
                    section = clause.section
                    with self.subTest(row=row.number, role=role, path=section.path, heading=section.heading):
                        body = flat(section.read(self.text(section.path)))
                        if role == "red":
                            self.assertNotRegex(body, clause.text)
                        else:
                            self.assertIn(clause.text, body)

    def test_merge_handoff_names_only_registered_sandboxes(self):
        for repository, sandbox in (
            ("Habit130/governance-sandbox", True),
            ("Habit130/governance-sandbox-private", True),
            ("Habit130/tally", False),
        ):
            with self.subTest(repository=repository):
                dest = self.path(repository.rsplit("/", 1)[-1] + "-handoff")
                code, facts = support.govern([
                    "render", "--version", str(self.VERSION), "--allow-unreleased", "--dest", dest,
                    "--repository", repository, "--default-branch", "main",
                    "--confirmed", self.path("confirmed.json"),
                ])
                self.assertEqual(code, 0, facts)
                handoff = MERGE.read(support.read_text(os.path.join(dest, MERGE.path)))
                registered = sandbox_names(handoff)
                self.assertCountEqual(registered, SANDBOXES)
                self.assertEqual(repository in registered, sandbox)
                self.assertIn(
                    "only when any is open: the count of open miss records, "
                    "`gh issue list --label miss --state open --repo %s`." % repository,
                    flat(handoff),
                )

    def test_planner_docs_pr_uses_the_confirmed_floor(self):
        from parsers import load_gate

        gate = load_gate(self.VERSION)
        record_path = ".github/governance/record.yml"
        record = self.text(record_path)
        parsed = gate.parse_record(record.encode("utf-8"))
        fixed = render.record_fixed_part(record, record_path)
        for path in ("GLOSSARY.md", "docs/adr/0001-decision.md"):
            for floor in ("medium", "high", None):
                with self.subTest(path=path, floor=floor), mock.patch.dict(os.environ, support.isolated_env()):
                    repo = support.init_repo(self.path("repo-%s-%s" % (os.path.basename(path), floor)))
                    paths = [] if floor is None else [{"pattern": path, "floor": floor}]
                    confirmed = dict(parsed["confirmed"], sensitive_paths=paths)
                    base_record = render.fill_record(fixed, confirmed, record_path)
                    base = support.commit_tree(repo, {record_path: base_record}, "governance")
                    head = support.commit_tree(repo, {record_path: base_record, path: "A decision.\n"}, "docs")
                    verdict = gate.verdict(
                        repo, parsed["agent_account"], "Habit130", "Risk: low — docs only", base, head,
                        lambda sha: False,
                    )
                    self.assertIs(verdict["passed"], floor is None, verdict)
                    if floor is not None:
                        (failure,) = verdict["failures"]
                        self.assertTrue(failure.startswith("Floors:"), failure)
                        self.assertIn(path, failure)
                        self.assertIn(floor, failure)
