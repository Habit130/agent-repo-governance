"""The version 6 consolidation test at #309's rendered-policy seam."""

import os
from unittest import mock

import support
from govlib import render
from materialized_version_support import VersionThreeRendered, flat
from policy_rows_312 import ROWS as ROWS_312


ROWS = (*ROWS_312,)


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
