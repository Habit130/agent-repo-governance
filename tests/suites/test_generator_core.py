"""The generator's mechanical core (#44 §6.1 to §6.3): Seam A, against the stand-in GitHub and fixture homes.

Each case under `tests/fixtures/generator/cases/` builds a fixture repository, serves the
case's GitHub state through the stand-in `gh`, and runs the preconditions, the mode and drift,
and the inspection through the one entry (`generator_support.py` gives the case format). Every
case also checks CRIT-5: no stand-in call is a write, except accepting habit's invitation in
the case that runs it, and the worktree and the machine home are byte-for-byte unchanged.
"""

import json
import os
import re
import subprocess
import sys
import unittest

import generator_support as gs
import machine_support as ms
import support
from target_state import TARGET_SETTINGS, target_ruleset


class SeamA(support.TempDirCase):
    """Filled below: one test per case file."""

    def assert_case(self, name):
        case = gs.load_case(name)
        run = gs.run_case(self.tmp, case)
        printed = "\n".join(out for _, _, out, _ in run["results"].values())
        for command, (code, facts, out, err) in run["results"].items():
            self.assertEqual(err, "", "%s wrote to stderr: %s" % (command, err))
            expected = case["expect"].get(command, {})
            self.assertEqual(code, expected.get("exit", 0), "%s exited %d: %s" % (command, code, out))
            if command == "preconditions" and "items" in expected:
                self.assertEqual(dict((i["item"], i["status"]) for i in facts["items"]), expected["items"], out)
                self.assertEqual([step["step"] for step in facts["checklist"]], expected["checklist"], out)
            want = dict((k, v) for k, v in expected.items() if k not in ("exit", "items", "checklist"))
            self.assertEqual(gs.subset(want, facts), [], out)
        # CRIT-5: no write but the invitation's acceptance, and nothing changed locally.
        allowed = [["api", "--method", "PATCH", "user/repository_invitations/%d" % i["id"]]
                   for i in case.get("github", {}).get("invitations", [])] if "accept-invitation" in case.get("run", []) else []
        self.assertEqual(gs.writes(run["log"]), allowed, printed)
        self.assertEqual([e["args"] for e in run["log"] if not e["recorded"]], [], printed)
        self.assertEqual(run["after"][0], run["before"][0], "a run changed the worktree")
        self.assertEqual(run["after"][1], run["before"][1], "a run changed the machine home")
        self.assertFalse(ms.ghm_called(run["scratch"]), "a run called ghm")
        for value in gs.PLANTED.values():
            self.assertNotIn(value, printed, "a planted credential's value was printed")
        if case.get("expect_no_calls"):
            self.assertEqual(run["log"], [], "a refused harness reached GitHub")
        return run


def _add_case(name):
    def test(self):
        self.assert_case(name)

    test.__doc__ = "Seam A case %s" % name
    setattr(SeamA, "test_" + re.sub(r"[^A-Za-z0-9]+", "_", name), test)


for _name in gs.case_names():
    _add_case(_name)


class Handover(support.TempDirCase):
    """CRIT-6 and CRIT-10's deterministic handover rule, through the one entry."""

    def run_rule(self, row):
        name = os.path.join(self.tmp, "mode.json")
        with open(name, "w") as handle:
            json.dump({"mode": row["mode"], "drift": {
                "owner_script_changed": row["owner_script_changed"], "in_github": row["in_github"],
                "github": {"unreadable": ["ruleset Gate: Not Found"] if row["failed_reads"] else [],
                           "rulesets_unread": row["rulesets_unread"]}}}, handle)
        args = ["handover", "--mode-facts", name]
        return support.govern(args + (["--required-checks-changed"] if row["required_checks_changed"] else []))

    def test_each_row_of_the_rule(self):
        with open(os.path.join(support.FIXTURES, "generator", "handover.json")) as handle:
            rows = json.load(handle)
        for row in rows:
            with self.subTest(row["case"]):
                code, facts = self.run_rule(row)
                self.assertEqual(code, 0, facts)
                self.assertEqual(facts["owner_command"], row["owner_command"], facts)

    def test_a_file_that_isnt_a_mode_report_is_a_refusal(self):
        name = os.path.join(self.tmp, "bad.json")
        for text in ("[]", '{"drift": []}', '{"drift": {"github": 1}}'):
            with open(name, "w") as handle:
                handle.write(text)
            code, facts = support.govern(["handover", "--mode-facts", name])
            self.assertEqual(code, 2, facts)
            self.assertIn("isn't a `mode` report", facts["error"])

    def test_the_line_says_what_the_command_does(self):
        row = {"mode": "Repair", "owner_script_changed": False, "required_checks_changed": False,
               "in_github": False, "failed_reads": True, "rulesets_unread": False}
        code, facts = self.run_rule(row)
        self.assertEqual(facts["lines"], [gs_line("at target")], facts)
        code, facts = self.run_rule(dict(row, rulesets_unread=True))
        self.assertEqual(facts["lines"], [gs_line("at target"), gs_line("list unread")], facts)


def gs_line(which):
    return {"at target": "这条命令在 GitHub 已是目标状态时不写入任何内容，否则把 GitHub 恢复到目标状态。",
            "list unread": "规则集列表没有读到，所以脚本可能删除作用于默认分支、但本次运行没有事先列出的规则集；它的报告会写明删除了哪些。"}[which]


class SkillFiles(unittest.TestCase):
    """CRIT-1: #41 §11's four conditions on the real skill files, and the identity hash."""

    SKILL = os.path.dirname(os.path.dirname(support.GOVERN))

    def test_the_frontmatter_has_the_shape_the_entry_check_proved(self):
        text = support.read_text(os.path.join(self.SKILL, "SKILL.md"))
        head = text.split("---\n")[1]
        self.assertIn("name: govern-repository\n", head)
        self.assertIn("disable-model-invocation: true\n", head)
        self.assertIn("metadata:\n  opencode/autoinvoke: false\n", head)
        self.assertEqual(os.path.basename(self.SKILL), "govern-repository")

    def test_every_outcome_begins_with_exactly_one_branch_of_step_3(self):
        sys.path.insert(0, os.path.join(self.SKILL, "scripts"))
        from govlib import drift
        text = support.read_text(os.path.join(self.SKILL, "SKILL.md"))
        step = text.split("3. Follow the report's `outcome`")[1].split("\n4. ")[0]
        heads = [re.match(r"((?:`[^`]+`(?:,\s*|\s+or\s+)?)+)", " ".join(bullet.split()))
                 for bullet in re.split(r"\n   - ", step)[1:]]
        branches = [re.findall(r"`([^`]+)`", head.group(1)) if head else [] for head in heads]
        ends = ["no drift", "inactive", "section 6", "carry on"]
        routes = {}
        for mode, present in (("Initialize", False), ("Initialize", True)):
            routes[drift.outcome(mode, {"present": present}, {})] = "carry on"
        for files in (False, True):
            for in_github in (False, True):
                for unread in ([], ["a read"]):
                    for unplaced in ([], ["a ruleset"]):
                        facts = {"in_files": files, "in_github": in_github,
                                 "github": {"unreadable": unread, "unplaced": unplaced}}
                        routes[drift.outcome("Upgrade", {"present": True}, facts)] = "carry on"
                        want = ("carry on" if files else "section 6" if in_github or unread
                                else "inactive" if unplaced else "no drift")
                        routes[drift.outcome("Repair", {"present": True}, facts)] = want
        for said, want in routes.items():
            matched = [i for i, prefixes in enumerate(branches) if any(said.startswith(p) for p in prefixes)]
            self.assertEqual(len(matched), 1, (said, branches))
            self.assertIn(want, step.split("\n   - ")[1 + matched[0]], said)
        self.assertEqual(len(branches), len(ends))

    def test_codex_reads_the_skill_as_user_only(self):
        sys.path.insert(0, os.path.join(support.REPO, "machine", "scripts"))
        from machinelib import skills
        with open(os.path.join(self.SKILL, "agents", "openai.yaml"), "rb") as handle:
            self.assertEqual(skills.codex_policy(handle.read()), skills.FALSE)

    def test_the_identity_is_the_directory_hash_and_ignores_bytecode(self):
        code, facts = support.govern(["identity"])
        self.assertEqual(code, 0, facts)
        self.assertRegex(facts["identity"], "^[0-9a-f]{64}$")
        cache = os.path.join(self.SKILL, "scripts", "__pycache__")
        made = not os.path.isdir(cache)
        os.makedirs(cache, exist_ok=True)
        planted = os.path.join(cache, "planted.cpython-39.pyc")
        with open(planted, "w") as handle:
            handle.write("bytecode")
        try:
            code, again = support.govern(["identity"])
        finally:
            os.remove(planted)
            if made:
                os.rmdir(cache)
        self.assertEqual(again["identity"], facts["identity"])


class MendMarkers(support.TempDirCase):
    """Damaged markers become one well-formed block that `render` can fill, keeping the repository's own text."""

    OWNED = "## This repository\n\n- An owned rule the repository wrote.\n"
    NOTES = "## Claude Code notes\n\n- An owned Claude Code note.\n"

    def governed(self, edits):
        store = gs.build_store("released")
        owned = [{"path": "AGENTS.md", "replace": ["## This repository\n", self.OWNED]},
                 {"path": ".claude/CLAUDE.md", "replace": ["## Claude Code notes\n", self.NOTES]}]
        worktree = gs.build_repository(self.tmp, {"repository": {"governed_at": 3, "edits": owned + edits}}, store)
        return worktree, store

    def mend(self, worktree, store):
        return support.govern(["mend-markers", "--worktree", worktree, "--store", store])

    def render_and_compare(self, worktree, store):
        confirmed = self.path("confirmed.json")
        with open(confirmed, "w") as handle:
            json.dump(gs.TALLY_CONFIRMED, handle)
        code, facts = support.govern(["render", "--store", store, "--version", "3", "--dest", worktree,
                                      "--repository", "Habit130/tally", "--default-branch", "main", "--confirmed", confirmed])
        self.assertEqual(code, 0, facts)
        code, facts = support.govern(["compare", "--store", store, "--version", "3", "--worktree", worktree])
        self.assertEqual((code, facts["differences"]), (0, []), facts)

    def after_end(self, worktree, path):
        return support.read_text(os.path.join(worktree, *path.split("/"))).split("<!-- governance:end -->\n")[1]

    def test_intact_text_gets_its_markers_back(self):
        worktree, store = self.governed([{"path": "AGENTS.md", "replace": ["<!-- governance:end -->\n", ""]}])
        owned = self.after_end_of(worktree)
        code, facts = self.mend(worktree, store)
        self.assertEqual(code, 0, facts)
        self.assertEqual([(m["path"], m["repair"], m["dropped"]) for m in facts["mended"]],
                         [("AGENTS.md", "restore the markers", [])])
        self.render_and_compare(worktree, store)
        self.assertEqual(self.after_end(worktree, "AGENTS.md"), owned)

    def after_end_of(self, worktree):
        """AGENTS.md's text after the governance text, with its end marker gone."""
        text = support.read_text(os.path.join(worktree, "AGENTS.md"))
        return text[text.index("\n" + self.OWNED):]

    def test_duplicated_markers_around_intact_text_are_restored(self):
        worktree, store = self.governed([{"path": "AGENTS.md", "replace": ["# AGENTS.md\n", "<!-- governance:end -->\n# AGENTS.md\n"]}])
        code, facts = self.mend(worktree, store)
        self.assertEqual(code, 0, facts)
        self.assertEqual([m["repair"] for m in facts["mended"]], ["restore the markers"])
        self.render_and_compare(worktree, store)
        self.assertTrue(self.after_end(worktree, "AGENTS.md").startswith("\n" + self.OWNED))

    def test_edited_text_without_its_end_marker_is_rebuilt_and_the_owned_part_kept(self):
        worktree, store = self.governed([{"path": "AGENTS.md", "replace": ["<!-- governance:end -->\n", ""]},
                                         {"path": "AGENTS.md", "replace": ["# AGENTS.md\n", "# AGENTS.md (edited)\n"]}])
        owned = self.after_end_of(worktree)
        code, facts = self.mend(worktree, store)
        self.assertEqual(code, 0, facts)
        self.assertEqual([(m["path"], m["repair"], m["dropped"]) for m in facts["mended"]],
                         [("AGENTS.md", "rebuild as at Initialize", ["# AGENTS.md (edited)"])])
        self.render_and_compare(worktree, store)
        self.assertNotIn("(edited)", support.read_text(os.path.join(worktree, "AGENTS.md")))
        self.assertEqual(self.after_end(worktree, "AGENTS.md"), owned)

    def test_edited_text_without_its_begin_marker_is_rebuilt_and_the_owned_part_kept(self):
        worktree, store = self.governed([{"path": ".claude/CLAUDE.md", "replace": ["<!-- governance:begin v3 -->\n", ""]},
                                         {"path": ".claude/CLAUDE.md", "replace": ["@../AGENTS.md", "@../AGENTS.md (edited)"]}])
        code, facts = self.mend(worktree, store)
        self.assertEqual(code, 0, facts)
        self.assertEqual([(m["path"], m["repair"]) for m in facts["mended"]], [(".claude/CLAUDE.md", "rebuild as at Initialize")])
        self.render_and_compare(worktree, store)
        self.assertNotIn("(edited)", support.read_text(os.path.join(worktree, ".claude", "CLAUDE.md")))
        self.assertTrue(self.after_end(worktree, ".claude/CLAUDE.md").startswith("\n" + self.NOTES))

    def test_a_rebuild_leaves_no_stray_marker_in_the_owned_part(self):
        worktree, store = self.governed([{"path": "AGENTS.md", "replace": ["<!-- governance:end -->\n", ""]},
                                         {"path": "AGENTS.md", "replace": ["# AGENTS.md\n", "# AGENTS.md (edited)\n"]},
                                         {"path": "AGENTS.md", "replace": [self.OWNED, self.OWNED + "<!-- governance:begin v3 -->\n"]}])
        code, facts = self.mend(worktree, store)
        self.assertEqual(code, 0, facts)
        self.assertEqual([m["repair"] for m in facts["mended"]], ["rebuild as at Initialize"])
        self.render_and_compare(worktree, store)
        self.assertTrue(self.after_end(worktree, "AGENTS.md").startswith("\n" + self.OWNED))

    def test_a_symlinked_parent_is_refused_before_anything_is_written(self):
        worktree, store = self.governed([{"path": ".claude/CLAUDE.md", "replace": ["<!-- governance:end -->\n", ""]}])
        outside = self.path("outside")
        os.rename(os.path.join(worktree, ".claude"), outside)
        os.symlink(outside, os.path.join(worktree, ".claude"))
        with open(os.path.join(worktree, "AGENTS.md")) as handle:
            agents = handle.read()
        with open(os.path.join(worktree, "AGENTS.md"), "w") as handle:
            handle.write(agents.replace("<!-- governance:end -->\n", ""))
        before = (gs.tree_snapshot(worktree), support.read_text(os.path.join(outside, "CLAUDE.md")))
        code, facts = self.mend(worktree, store)
        self.assertEqual(code, 2, facts)
        self.assertIn("symlink", facts["error"])
        self.assertEqual((gs.tree_snapshot(worktree), support.read_text(os.path.join(outside, "CLAUDE.md"))), before)

    def test_owned_text_that_cant_be_told_apart_is_a_refusal_that_writes_nothing(self):
        worktree, store = self.governed([{"path": "AGENTS.md", "replace": ["<!-- governance:end -->\n", ""]},
                                         {"path": "AGENTS.md", "replace": ["# AGENTS.md\n", "# AGENTS.md (edited)\n"]},
                                         {"path": "AGENTS.md", "replace": ["## This repository\n", "## Ours\n"]}])
        before = gs.tree_snapshot(worktree)
        code, facts = self.mend(worktree, store)
        self.assertEqual(code, 2, facts)
        self.assertIn("AGENTS.md", facts["error"])
        self.assertEqual(gs.tree_snapshot(worktree), before)

    def test_well_formed_markers_are_left_alone(self):
        worktree, store = self.governed([])
        before = gs.tree_snapshot(worktree)
        self.assertEqual(self.mend(worktree, store), (0, {"ok": True, "version": 3, "mended": []}))
        self.assertEqual(gs.tree_snapshot(worktree), before)


class ScenarioSettings(support.TempDirCase):
    def test_the_runners_repository_setting_names_a_local_origin(self):
        worktree = support.init_repo(self.path("r"))
        support.git(worktree, "remote", "add", "origin", self.path("bare.git"))
        self.assertIn("isn't a GitHub repository", self.compare(worktree, {})["error"])
        facts = self.compare(worktree, {"GOVERN_SCENARIO_REPOSITORY": "Habit130/tally"})
        self.assertEqual(facts.get("repository"), "Habit130/tally", facts)

    def compare(self, worktree, extra):
        env = dict(os.environ, **extra)
        env.pop("GOVERN_SCENARIO_REPOSITORY", None) if not extra else None
        result = subprocess.run([sys.executable, support.GOVERN, "compare", "--worktree", worktree, "--default-branch", "main",
                                 "--store", gs.build_store("released")],
                                env=env, stdout=subprocess.PIPE, universal_newlines=True)
        return json.loads(result.stdout)


class HarnessProbes(unittest.TestCase):
    """Each harness's shell, as probed by name, is judged as #44 §6 and ADR 0013 require."""

    def test_only_claude_code_and_opencode_pass(self):
        from govlib import harness

        with open(os.path.join(support.FIXTURES, "generator", "harness-probes.json")) as handle:
            probes = json.load(handle)["harnesses"]
        self.assertEqual(sorted(probes), ["Claude Code", "OpenCode", "deepseekharness", "the Codex harness"])
        for name, probe in sorted(probes.items()):
            judged = harness.judge(dict((variable, "set") for variable in probe["names"]))
            self.assertEqual(judged["passed"], probe["passes"], (name, judged))
            self.assertEqual(judged["harness"], name, judged)


class DriftTarget(unittest.TestCase):
    """Drift's #41 §7 target is the spec's, as `tests/target_state.py` writes it, not the owner script's."""

    def test_each_ruleset_matches_the_spec_for_any_confirmed_checks(self):
        from govlib import target

        for checks in ([], ["test"], ["lint", "governance-gate", "build"]):
            for name in ("Gate", "Merge", "History"):
                self.assertEqual(target.ruleset(name, checks), target_ruleset(name, checks), (name, checks))
                self.assertEqual(target.ruleset_differences(target_ruleset(name, checks), name, checks), [])

    def test_the_settings_match_the_spec(self):
        from govlib import target

        self.assertEqual(target.SETTINGS, TARGET_SETTINGS)

    def test_the_agent_accounts_view_of_a_gate_in_place_is_no_drift(self):
        from govlib import target

        with open(os.path.join(support.FIXTURES, "generator", "agent-view-gate-ruleset.json")) as handle:
            recorded = json.load(handle)
        self.assertEqual(target.ruleset_differences(recorded["ruleset"], "Gate", recorded["checks"]), [])
        self.assertNotEqual(target.ruleset_differences(recorded["ruleset"], "Gate", []), [])


class Checklist(support.TempDirCase):
    def test_a_missing_collaborator_gets_habits_ready_invite_command(self):
        run = gs.run_case(self.tmp, gs.load_case("missing-collaborator"))
        facts = run["results"]["preconditions"][1]
        invite = [step for step in facts["checklist"] if step["step"] == "invite"]
        self.assertEqual(
            [step.get("command") for step in invite],
            ["ghm api --method PUT repos/Habit130/tally/collaborators/Habit098 -f permission=push"],
        )


if __name__ == "__main__":
    unittest.main()
