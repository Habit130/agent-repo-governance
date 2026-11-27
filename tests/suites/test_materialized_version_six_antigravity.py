"""#327's Antigravity app translation and the version 6 AGENTS.md budget at #309's rendered policy seam."""

import os
import re

import support
from materialized_version_support import VersionThreeRendered, flat
from policy_rows_316 import HANDOFF, START, LIMITS
from policy_text import Section

BUDGET = 12288
END_MARKER = "<!-- governance:end -->\n"
SECRETS = Section("AGENTS.md", "## Secrets")
GOVERNANCE_FILES = Section("AGENTS.md", "## Governance files")
REPOSITORY_README = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "README.md")


def budgeted_bytes(text):
    """Bytes of a rendered AGENTS.md up to and including its end-marker line."""
    return len((text.split(END_MARKER, 1)[0] + END_MARKER).encode("utf-8"))


class VersionSixAntigravityApp(VersionThreeRendered):
    VERSION = 6

    def entry(self):
        body = START.read(self.text(START.path))
        found = re.findall(r"^- \*\*Antigravity app\*\*:.*?(?=^- \*\*|^## |\Z)", body, re.M | re.S)
        self.assertEqual(len(found), 1)
        return flat(found[0])

    def test_agents_file_fits_its_budget_and_a_planted_byte_fails(self):
        text = self.text("AGENTS.md")
        self.assertLessEqual(budgeted_bytes(text), BUDGET)
        before, after = text.split(END_MARKER, 1)
        planted = before + "x" * (BUDGET - budgeted_bytes(text)) + "\n" + END_MARKER + after
        self.assertEqual(budgeted_bytes(planted), BUDGET + 1)
        with self.assertRaises(AssertionError):
            self.assertLessEqual(budgeted_bytes(planted), BUDGET)

    def test_how_to_start_translates_for_the_antigravity_app(self):
        entry = self.entry()
        for clause in (
            "a two-folder project: the checkout and its persistent sibling worktree directory, named for the checkout, "
            "in Local Checkout mode under habit's Auto preset; never New Worktree mode or remote projects.",
            "Builders' worktrees and Reviewers' temporary ones go there.",
            "The start instruction is the first message; skills use `/name`.",
            "One paste is unverified; use the two-step form.",
            "No-history subagents are `research`, or `self` when one must run commands.",
            "No whole-spec delivery, teamwork, swarm or remote agents; the generator never runs there; "
            "the Antigravity CLI is unsupported.",
            "Waiting is unverified: stop and say what you wait for.",
            "Without machine rules against `ghm` or Actions-secret writes, those limits rest on instructions.",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, entry)

    def test_machine_rule_limits_do_not_name_the_app(self):
        for section in (LIMITS, SECRETS):
            body = flat(section.read(self.text(section.path)))
            with self.subTest(heading=section.heading):
                self.assertNotIn("Antigravity", body)
                self.assertIn("Claude Code and OpenCode, partly in Codex.", body)

    def test_governance_files_name_the_apps_files(self):
        body = flat(GOVERNANCE_FILES.read(self.text(GOVERNANCE_FILES.path)))
        self.assertIn("`GEMINI.md`", body)
        self.assertIn("Antigravity `.agents/` or `.agent/` instruction or rule file", body)

    def test_reviewer_handoff_hints_the_apps_vendor_by_its_model(self):
        body = flat(HANDOFF.read(self.text(HANDOFF.path)))
        self.assertIn("and OpenCode and the Antigravity app whatever model they run. "
                      "The model's vendor decides, not the harness.", body)
        self.assertEqual(body.count("The model's vendor decides"), 1)

    def test_readme_names_the_app_and_the_unsupported_cli(self):
        text = support.read_text(REPOSITORY_README)
        for condition in ("仓库已采用 version 6（目前是草稿）", "machine check 的 Antigravity app 项通过",
                          "仓库里没有该 app 自己的指令或配置文件"):
            self.assertIn(condition, text)
        self.assertRegex(text, r"Antigravity app 支持角色 session，需同时满足三个条件")
        self.assertIn("Antigravity CLI 不受支持", text)
        self.assertIn("Codex harness、deepseekharness 和 Antigravity app 不能运行它", text)
