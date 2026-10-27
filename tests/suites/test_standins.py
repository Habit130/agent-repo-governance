"""The stand-in GitHub and the Codex stand-in (#44 §11): recorded state served, every call recorded."""

import json
import os
import subprocess
import unittest

import support
from standins import environment

GH_TALLY = os.path.join(support.FIXTURES, "standins", "gh-tally.json")
CODEX_MACHINE = os.path.join(support.FIXTURES, "standins", "codex-machine.json")


class StandInCase(support.TempDirCase):
    def setUp(self):
        super(StandInCase, self).setUp()
        self.scratch = self.path("scratch")
        self.home = self.path("home")
        os.makedirs(self.home)
        self.tripwire = self.path("tripwire")
        self.real_tools = self.path("real-tools")
        os.makedirs(self.real_tools)
        # Stand-ins for the real tools, later on the path: if anything reached them, the marker appears.
        for tool in ("gh", "codex"):
            path = os.path.join(self.real_tools, tool)
            with open(path, "w") as handle:
                handle.write("#!/bin/bash\necho \"$0 $*\" >> '%s'\nexit 0\n" % self.tripwire)
            os.chmod(path, 0o755)
        base = support.isolated_env({"PATH": self.real_tools + os.pathsep + os.environ.get("PATH", ""), "HOME": self.home})
        base["GH_TOKEN"] = "not-a-real-token"
        self.env = environment.environment(
            self.scratch, gh_recording=GH_TALLY, codex_recording=CODEX_MACHINE, base=base
        )

    def call(self, args, stdin=None):
        result = subprocess.run(
            args,
            env=self.env,
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return result.returncode, result.stdout, result.stderr

    def calls(self):
        return environment.read_log(self.scratch)

    def assert_nothing_reached_the_real_tools(self):
        self.assertFalse(os.path.exists(self.tripwire), "a call reached a real tool")


class StandInGitHub(StandInCase):
    def test_is_first_on_the_path_and_carries_no_credential(self):
        code, out, _ = self.call(["/bin/bash", "-c", "command -v gh; echo \"token=${GH_TOKEN-unset}\""])
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [os.path.join(environment.BIN, "gh"), "token=unset"])
        self.assertEqual(os.listdir(self.env["GH_CONFIG_DIR"]), [])

    def test_serves_recorded_state_and_records_the_call(self):
        code, out, err = self.call(["gh", "repo", "view", "Habit130/tally", "--json", "visibility,defaultBranchRef,owner"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["visibility"], "PUBLIC")
        self.assertEqual(
            self.calls(),
            [
                {
                    "tool": "gh",
                    "args": ["repo", "view", "Habit130/tally", "--json", "visibility,defaultBranchRef,owner"],
                    "recorded": True,
                    "call": 0,
                }
            ],
        )
        self.assert_nothing_reached_the_real_tools()

    def test_replays_a_recorded_failure(self):
        code, out, err = self.call(["gh", "api", "repos/Habit130/tally/branches/main/protection"])
        self.assertEqual(code, 1)
        self.assertIn("Branch not protected", err)

    def test_matches_a_recorded_request_body_on_stdin(self):
        args = ["gh", "issue", "create", "--repo", "Habit130/tally", "--title", "Initialize governance", "--body-file", "-"]
        code, out, _ = self.call(args, stdin="habit's invocation, quoted verbatim.\n")
        self.assertEqual((code, out), (0, "https://github.com/Habit130/tally/issues/1\n"))
        code, _, err = self.call(args, stdin="a different body\n")
        self.assertNotEqual(code, 0)
        self.assertIn("no recorded call", err)
        self.assertEqual([c["recorded"] for c in self.calls()], [True, False])
        self.assertEqual(self.calls()[1]["stdin"], "a different body\n")

    def test_a_stray_call_fails_and_never_reaches_github(self):
        code, out, err = self.call(["gh", "pr", "merge", "1", "--repo", "Habit130/tally", "--squash"])
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("no recorded call matches", err)
        self.assertIn("gh pr merge 1", err)
        self.assertEqual(
            self.calls(),
            [{"tool": "gh", "args": ["pr", "merge", "1", "--repo", "Habit130/tally", "--squash"], "recorded": False}],
        )
        self.assert_nothing_reached_the_real_tools()

    def test_records_every_call_in_order(self):
        self.call(["gh", "api", "repos/Habit130/tally/rulesets"])
        self.call(["gh", "api", "repos/Habit130/tally/collaborators/Habit098/permission", "--jq", ".permission"])
        self.call(["gh", "auth", "status"])
        self.assertEqual(
            [(c["args"][:2], c["recorded"]) for c in self.calls()],
            [(["api", "repos/Habit130/tally/rulesets"], True),
             (["api", "repos/Habit130/tally/collaborators/Habit098/permission"], True),
             (["auth", "status"], False)],
        )

    def test_without_a_recording_every_call_fails(self):
        env = dict(self.env)
        del env["STANDIN_GH_RECORDING"]
        result = subprocess.run(["gh", "api", "user"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"STANDIN_GH_RECORDING", result.stderr)
        self.assert_nothing_reached_the_real_tools()


class CodexStandIn(StandInCase):
    def test_replays_execpolicy_check_with_the_home_expanded(self):
        rules = os.path.join(self.home, ".codex", "rules", "governance.rules")
        code, out, _ = self.call(["codex", "execpolicy", "check", "--rules", rules, "gh", "secret", "set", "TOKEN"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["decision"], "forbidden")

    def test_replays_debug_prompt_input(self):
        code, out, _ = self.call(["codex", "debug", "prompt-input", "x"])
        self.assertEqual(code, 0)
        self.assertIn("<skills_instructions>", out)

    def test_a_stray_call_fails_and_never_reaches_codex(self):
        code, _, err = self.call(["codex", "exec", "write a poem"])
        self.assertNotEqual(code, 0)
        self.assertIn("no recorded call matches", err)
        self.assertEqual(self.calls(), [{"tool": "codex", "args": ["exec", "write a poem"], "recorded": False}])
        self.assert_nothing_reached_the_real_tools()

    def test_refuses_a_recording_beyond_execpolicy_check_and_debug_prompt_input(self):
        recording = self.path("codex-exec.json")
        with open(recording, "w") as handle:
            json.dump({"tool": "codex", "calls": [{"args": ["exec", "hi"], "stdout": "", "stderr": "", "exit": 0}]}, handle)
        env = dict(self.env)
        env["STANDIN_CODEX_RECORDING"] = recording
        result = subprocess.run(["codex", "exec", "hi"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"execpolicy check", result.stderr)


if __name__ == "__main__":
    unittest.main()
