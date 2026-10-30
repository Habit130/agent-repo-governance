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
