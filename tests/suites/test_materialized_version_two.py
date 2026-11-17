"""Governance model version two: rendered policy-text checks."""

import json
import os

import materialized
import support
from govlib import record
from test_record import RECORD


class VersionTwoPolicy(support.TempDirCase):
    """#122 rendered instructions at the existing materialization seam."""

    def test_gate_and_record_templates_keep_the_existing_trust_boundary(self):
        for path in ("dot-github/governance/gate.py", "dot-github/workflows/governance-gate.yml",
                     "dot-github/governance/record.yml"):
            self.assertEqual(support.read_text(os.path.join(support.REAL_STORE, "2", "templates", path)),
                             support.read_text(os.path.join(support.REAL_STORE, "1", "templates", path)), path)

    def test_upgrade_preserves_repository_policy_and_confirmed_values(self):
        dest = materialized.tally_worktree(self.tmp)
        confirmed = self.path("confirmed.json")
        values = materialized.tally_fixture()["confirmed"]
        with open(confirmed, "w") as handle:
            json.dump(values, handle)
        args = ["--dest", dest, "--repository", "Habit130/tally", "--default-branch", "main"]
        code, facts = support.govern(["render", "--version", "1", "--confirmed", confirmed] + args)
        self.assertEqual(code, 0, facts)
        policy = "\nRepository-owned rule: hosted builds must use the dedicated command.\n"
        agents = os.path.join(dest, "AGENTS.md")
        with open(agents, "a") as handle:
            handle.write(policy)
        build = os.path.join(dest, "docs/agents/build.md")
        evidence = "# Repository runbook\n\nRelease-only CI; exact merged-commit smoke is local.\n"
        with open(build, "w") as handle:
            handle.write(evidence)
        code, facts = support.govern(["render", "--version", "2", "--allow-unreleased", "--confirmed", confirmed] + args)
        self.assertEqual(code, 0, facts)
        self.assertTrue(support.read_text(agents).endswith(policy))
        self.assertEqual(support.read_text(build), evidence)
        with open(os.path.join(dest, RECORD), "rb") as handle:
            self.assertEqual(record.parse(handle.read())["confirmed"], values)
        code, facts = support.govern([
            "compare", "--worktree", dest, "--version", "2", "--allow-unreleased",
            "--repository", "Habit130/tally", "--default-branch", "main",
        ])
        self.assertEqual(code, 0, facts)
        self.assertEqual(facts["differences"], [])

    def test_product_smoke_is_bound_to_the_merged_commit(self):
        fixture = materialized.tally_fixture()
        confirmed = self.path("confirmed.json")
        with open(confirmed, "w") as handle:
            json.dump(fixture["confirmed"], handle)
        dest = self.path("rendered")
        code, facts = support.govern([
            "render", "--version", "2", "--allow-unreleased", "--dest", dest,
            "--repository", fixture["repository"], "--default-branch", fixture["default_branch"],
            "--confirmed", confirmed,
        ])
        self.assertEqual(code, 0, facts)
        builder = support.read_text(os.path.join(dest, "docs/agents/builder.md"))
        self.assertIn("exact merged commit", builder)
        self.assertIn("delivery incomplete", builder)
        self.assertIn("Governance audits", builder)

    def test_label_descriptions_are_creation_defaults_not_retention_requirements(self):
        dest = self.path("rendered")
        confirmed = self.path("confirmed.json")
        with open(confirmed, "w") as handle:
            json.dump(materialized.tally_fixture()["confirmed"], handle)
        code, facts = support.govern([
            "render", "--version", "2", "--allow-unreleased", "--dest", dest,
            "--repository", "Habit130/tally", "--default-branch", "main", "--confirmed", confirmed,
        ])
        self.assertEqual(code, 0, facts)
        labels = support.read_text(os.path.join(dest, "docs/agents/triage-labels.md"))
        self.assertIn("creation defaults", labels)
        self.assertIn("same-name, same-purpose", labels)
        self.assertIn("purpose conflict", labels)
        self.assertNotIn("exact description", labels)
