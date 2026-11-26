"""The version 6 consolidation test at #309's rendered-policy seam."""

import json
import os
import re
from unittest import mock

import support
from govlib import render
from materialized_version_support import VersionThreeRendered, flat
from policy_rows_312 import ROWS as ROWS_312
from policy_rows_316 import AFTER_MERGE, BUILD_WAIT, EXAMPLES, HANDOFF, MINIMUM, REVIEW_START, WAITS
from policy_rows_316 import ROWS as ROWS_316


ROWS = (*ROWS_312, *ROWS_316)


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

    def test_reviewer_handoff_and_examples_use_the_start_instruction(self):
        start = REVIEW_START.read(self.text(REVIEW_START.path))
        canonical, = re.findall(r"`(Role: Reviewer[^`]+)`", start)
        for number in (57, 58):
            with self.subTest(row="22", pr=number):
                expected = flat(canonical).replace("#<n>", "#%d" % number)
                self.assertIn(expected, flat(EXAMPLES.read(self.text(EXAMPLES.path))))
        handoff = flat(HANDOFF.read(self.text(HANDOFF.path)))
        self.assertIn("use the start instruction in `reviewer.md`, Start.", handoff)

    def test_high_builder_answers_an_open_head_nit_before_resuming_wait(self):
        with open(os.path.join(support.FIXTURES, "generator", "v5-builder-open-pr.json")) as handle:
            fixture = json.load(handle)
        high = next(
            bullet for bullet in AFTER_MERGE.read(self.text(AFTER_MERGE.path)).split("\n- ")
            if bullet.startswith("At high, when")
        )
        self.assertIn("read the intended repository and PR number on GitHub", flat(high))
        open_pr = next((branch for branch in high.split("\n  - ") if branch.startswith("If the PR is open,")), "")
        condition, *actions = map(flat, open_pr.split("\n    - "))
        self.assertEqual(condition, fixture["open_pr"])
        for case, action in fixture["cases"].items():
            with self.subTest(row="56", case=case):
                self.assertIn(action, actions)
        self.assertEqual(len(actions), len(fixture["cases"]))
        self.assertIn(WAITS, flat(BUILD_WAIT.read(self.text(BUILD_WAIT.path))))

    def test_high_reviewer_compares_vendors_only_with_builders_who_pushed(self):
        rule = next(
            line for line in MINIMUM.read(self.text(MINIMUM.path)).splitlines()
            if line.startswith("| Reviewer session |")
        )
        _, _, _, _, high, _ = rule.split("|")
        handoff = flat(HANDOFF.read(self.text(HANDOFF.path)))
        # Follow the handoff's pointer. The old handoff instead compared all marks.
        if "At high state the vendor constraint from `review.md`, Minimum reviews." not in handoff:
            self.assertIn("a vendor different from every Builder mark on the PR", handoff)
            high = handoff
        self.assertIn("a vendor different from every Builder", high)

        # Same Reviewer, original pusher and marked takeover in both cases.
        # Interpret the rule's selection of Builders before comparing vendors.
        original_vendor = "Anthropic"
        takeover_vendor = reviewer_vendor = "OpenAI"
        for takeover_pushed, eligible in ((False, True), (True, False)):
            with self.subTest(row="82", takeover_pushed=takeover_pushed):
                vendors = {original_vendor}
                if takeover_pushed or "that pushed to the PR" not in high:
                    vendors.add(takeover_vendor)
                self.assertIs(reviewer_vendor not in vendors, eligible)

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
