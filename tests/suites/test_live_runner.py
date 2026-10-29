"""The live-check runner (#44 §11, §12) offline: its probes, its result comment and habit's commands.

The live check itself runs against the sandboxes and is its own evidence. Here the owner
script's probes read reports the owner script printed in Seam D, and the agent account's view
of a sandbox through the stand-in GitHub; habit's commands run against the stand-in with the
`ghm` tripwire first on the path.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import machine_support as ms
import owner_support as ow
import support
import target_state
from standins import environment

LIVE = os.path.join(support.REPO, "tests", "live")
if LIVE not in sys.path:
    sys.path.insert(0, LIVE)

import live  # noqa: E402
import probes  # noqa: E402
from probes import owner as owner_probes  # noqa: E402

PUBLIC, PRIVATE = "Habit130/governance-sandbox", "Habit130/governance-sandbox-private"
COMMIT = "c" * 40


def owner_report(root, name):
    """What the owner script printed for a Seam D case."""
    case = ow.load_case(name)
    worktree, head = ow.prepare(root, case)
    recording = ow.recording(case, head, os.path.join(root, "gh.json"))
    env, _, _ = ow.owner_env(root, recording)
    return ow.run_owner(os.path.join(worktree, *ow.SCRIPT.split("/")), env)[1]


def agent_view(path, repository, rulesets, rule_types, settings=None):
    """The stand-in GitHub as the agent account sees a sandbox: rulesets without bypass actors."""
    shown = []
    for ruleset in rulesets:
        ruleset = dict(ruleset)
        ruleset.pop("bypass_actors", None)
        shown.append(ruleset)
    repo = {"full_name": repository, "private": repository == PRIVATE, "default_branch": "main",
            "permissions": {"admin": False, "push": True, "pull": True}}
    repo.update(settings or target_state.TARGET_SETTINGS)
    calls = [
        ow.ok(["api", "repos/%s/rulesets?includes_parents=false&per_page=100" % repository], [ow.listed(r) for r in shown]),
        ow.ok(["api", "repos/%s/rules/branches/main" % repository],
              [{"type": kind, "ruleset_id": 1, "ruleset_source_type": "Repository"} for kind in rule_types]),
        ow.ok(["api", "repos/%s" % repository], repo),
    ] + [ow.ok(["api", "repos/%s/rulesets/%d" % (repository, r["id"])], r) for r in shown]
    with open(path, "w") as handle:
        json.dump({"tool": "gh", "calls": calls}, handle)
    return path


def target_rulesets(checks=("test",)):
    return [ow.as_github(target_state.target_ruleset(name, list(checks)), ow.TARGET_IDS[name]) for name in target_state.RULESET_NAMES]


class ProbeCase(support.TempDirCase):
    def context(self, visibility="public", inputs=None):
        directory = tempfile.mkdtemp(prefix="check-%s-" % visibility, dir=self.tmp)
        for name, text in (inputs or {}).items():
            with open(os.path.join(directory, "%s.txt" % name), "w") as handle:
                handle.write(text)
        fixture = live.seed_fixture()
        return probes.Context(PUBLIC if visibility == "public" else PRIVATE, visibility, "main", fixture["confirmed"],
                              COMMIT, 3, directory)

    def with_github(self, recording):
        scratch = tempfile.mkdtemp(dir=self.tmp)
        env = environment.environment(scratch, gh_recording=recording, base=support.isolated_env())
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        return scratch

    def results(self, name, context):
        return probes.run(probes.registered()[name], context)

    def failed(self, results):
        return [(r.assertion, r.detail) for r in results if r.passed is False]


class Registry(unittest.TestCase):
    def test_the_owner_probes_register_in_the_one_shape(self):
        known = probes.registered()
        self.assertEqual(list(known), ["owner-report", "owner-state", "owner-rerun", "owner-private-secret"])
        for probe in known.values():
            self.assertIsInstance(probe, probes.Probe)
            self.assertTrue(set(probe.sandboxes) <= {"public", "private"})
        self.assertEqual(known["owner-private-secret"].sandboxes, ("private",))

    def test_a_probe_that_raises_or_returns_nothing_fails_instead_of_passing(self):
        def raising(context):
            raise probes.ProbeError("nothing to read")

        context = probes.Context(PUBLIC, "public", "main", {}, COMMIT, 1, tempfile.gettempdir())
        for run in (raising, lambda context: []):
            results = probes.run(probes.Probe("x", ("public",), lambda c: [], run), context)
            self.assertEqual([r.passed for r in results], [False])

    def test_the_runner_refuses_an_unknown_probe_or_one_for_the_other_sandbox(self):
        with self.assertRaises(live.RunnerError):
            live.chosen_probes(["no-such-probe"], "public")
        with self.assertRaises(live.RunnerError):
            live.chosen_probes(["owner-private-secret"], "public")


class OwnerReport(ProbeCase):
    def test_a_first_run_on_a_public_repository_passes(self):
        context = self.context("public", {"owner_report": owner_report(self.path("run"), "public-from-nothing")})
        results = self.results("owner-report", context)
        self.assertEqual(self.failed(results), [])
        self.assertGreater(len(results), 10)

    def test_a_private_run_passes_with_the_skip_and_its_reason(self):
        context = self.context("private", {"owner_report": owner_report(self.path("run"), "private-from-nothing")})
        results = self.results("owner-report", context)
        self.assertEqual(self.failed(results), [])
        self.assertIn("the private skip says why", [r.assertion for r in results])

    def test_a_missing_event_policy_passes_as_crit_9_allows(self):
        context = self.context("public", {"owner_report": owner_report(self.path("run"), "event-policy-api-cannot-create")})
        self.assertEqual(self.failed(self.results("owner-report", context)), [])

    def test_a_stopped_run_fails(self):
        context = self.context("public", {"owner_report": owner_report(self.path("run"), "wrong-account")})
        failed = self.failed(self.results("owner-report", context))
        self.assertIn("the first run's report has no failed item", [assertion for assertion, _ in failed])

    def test_a_missing_input_fails(self):
        results = self.results("owner-report", self.context("public"))
        self.assertEqual([r.passed for r in results], [False])
        self.assertIn("owner_report.txt", results[0].detail)


class OwnerStateAndRerun(ProbeCase):
    def test_the_target_state_passes_with_bypass_actors_hidden_and_is_remembered(self):
        self.with_github(agent_view(self.path("gh.json"), PUBLIC, target_rulesets(), owner_probes.RULES_IN_EFFECT))
        context = self.context("public")
        results = self.results("owner-state", context)
        self.assertEqual(self.failed(results), [])
        self.assertEqual(sorted(context.recall("rulesets_after_first_run")["updated_at"]), ["9001", "9002", "9003"])

    def test_a_drifted_ruleset_an_extra_one_and_a_lapsed_rule_fail(self):
        rulesets = target_rulesets(checks=())
        rulesets.append(ow.as_github({"name": "legacy", "target": "branch", "enforcement": "active",
                                      "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
                                      "rules": [{"type": "deletion"}]}, 77))
        self.with_github(agent_view(self.path("gh.json"), PUBLIC, rulesets, ("deletion", "non_fast_forward"),
                                    settings=dict(target_state.TARGET_SETTINGS, allow_merge_commit=True)))
        failed = [assertion for assertion, _ in self.failed(self.results("owner-state", self.context("public")))]
        self.assertEqual(failed, ["the Gate ruleset matches the target", "no other ruleset applies to main",
                                  "Gate's and Merge's rules are in effect on main",
                                  "the merge settings the agent can read match the target"])

    def snapshot(self, context, updated_at, taken_at=None):
        context.remember("rulesets_after_first_run", {"taken_at": time.time() - 60 if taken_at is None else taken_at,
                                                      "updated_at": updated_at})

    def test_a_rerun_that_wrote_nothing_passes_and_one_that_wrote_fails(self):
        self.with_github(agent_view(self.path("gh.json"), PUBLIC, target_rulesets(), owner_probes.RULES_IN_EFFECT))
        context = self.context("public", {"owner_rerun": owner_report(self.path("quiet"), "rerun-at-target")})
        self.snapshot(context, dict((str(r["id"]), r["updated_at"]) for r in target_rulesets()))
        self.assertEqual(self.failed(self.results("owner-rerun", context)), [])
        noisy = self.context("public", {"owner_rerun": owner_report(self.path("noisy"), "drifted-ruleset-and-settings")})
        self.snapshot(noisy, {"9001": "earlier"})
        failed = [assertion for assertion, _ in self.failed(self.results("owner-rerun", noisy))]
        self.assertIn("the rerun's report sets and removes nothing", failed)
        self.assertIn("the rerun left every ruleset's updated_at unchanged", failed)

    def test_a_rerun_that_still_misses_the_event_policy_fails(self):
        self.with_github(agent_view(self.path("gh.json"), PUBLIC, target_rulesets(), owner_probes.RULES_IN_EFFECT))
        context = self.context("public", {"owner_rerun": owner_report(self.path("run"), "event-policy-api-cannot-create")})
        self.snapshot(context, dict((str(r["id"]), r["updated_at"]) for r in target_rulesets()))
        failed = [assertion for assertion, _ in self.failed(self.results("owner-rerun", context))]
        self.assertIn("the rerun's report reports pull_request_target 事件策略 as 已就位", failed)
        self.assertIn("the rerun's report writes nothing and finds everything in place", failed)

    def test_a_snapshot_taken_after_the_rerun_fails(self):
        self.with_github(agent_view(self.path("gh.json"), PUBLIC, target_rulesets(), owner_probes.RULES_IN_EFFECT))
        context = self.context("public", {"owner_rerun": owner_report(self.path("run"), "rerun-at-target")})
        self.snapshot(context, dict((str(r["id"]), r["updated_at"]) for r in target_rulesets()), taken_at=time.time() + 60)
        failed = [assertion for assertion, _ in self.failed(self.results("owner-rerun", context))]
        self.assertEqual(failed, ["the ruleset snapshot was taken before the rerun"])

    def test_a_rerun_without_the_first_snapshot_fails(self):
        self.with_github(agent_view(self.path("gh.json"), PUBLIC, target_rulesets(), owner_probes.RULES_IN_EFFECT))
        context = self.context("public", {"owner_rerun": owner_report(self.path("run"), "rerun-at-target")})
        results = self.results("owner-rerun", context)
        self.assertEqual([r.passed for r in results], [False])


class PrivateSecret(ProbeCase):
    RESPONSE = (
        "== PATCH repos/Habit130/governance-sandbox-private security_and_analysis\n"
        '{"message":"Secret scanning is not available for this repository.","status":"422"}\n'
        "gh: Secret scanning is not available for this repository. (HTTP 422)\n"
        "exit=1\n"
        "== GET repos/Habit130/governance-sandbox-private\n"
        '{"security_and_analysis":{"secret_scanning":{"status":"disabled"}},"visibility":"private"}\n'
    )

    def test_gitHubs_refusal_is_recorded_and_secret_protection_stays_off(self):
        results = self.results("owner-private-secret", self.context("private", {"secret_response": self.RESPONSE}))
        self.assertEqual(self.failed(results), [])
        self.assertIn("Secret scanning is not available", results[1].detail)

    def test_secret_protection_turned_on_fails(self):
        text = self.RESPONSE.replace('"secret_scanning":{"status":"disabled"}', '"secret_scanning":{"status":"enabled"}')
        failed = self.failed(self.results("owner-private-secret", self.context("private", {"secret_response": text})))
        self.assertEqual([assertion for assertion, _ in failed], ["secret scanning and push protection stay off on the private sandbox"])


class Comment(unittest.TestCase):
    def test_it_names_the_commit_the_sandbox_pr_and_counts_the_assertions(self):
        state = {"commit": COMMIT, "sandbox": PUBLIC, "visibility": "public", "sandbox_pr": 4, "sandbox_head": "d" * 40}
        text = live.comment(state, [("owner-state", probes.Result("a | b", True, "x")),
                                    ("owner-rerun", probes.Result("c", False, "y\nz"))])
        self.assertIn("## Live check at %s" % COMMIT, text)
        self.assertIn("- **Commit**: `%s`, this PR's head when the check ran." % COMMIT, text)
        self.assertIn("%s#4 at `%s`" % (PUBLIC, "d" * 40), text)
        self.assertIn("- **Result**: 1 of 2 assertions failed.", text)
        self.assertIn("| owner-rerun | c | Fail | y z |", text)
        self.assertIn("| owner-state | a \\| b | Pass | x |", text)


class HabitsCommands(support.TempDirCase):
    def run_line(self, line, recording):
        home = ms.make_home(self.path("home"))
        scratch = self.path("scratch")
        env = ms.machine_env(home, scratch, gh_recording=recording)
        self.assertTrue(line.startswith("/bin/bash -c '") and line.endswith("'"))
        result = subprocess.run(["/bin/bash", "-c", line[len("/bin/bash -c '"):-1]], env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, stdin=subprocess.DEVNULL)
        return result, environment.read_log(scratch), scratch

    def test_the_sandbox_command_creates_a_missing_sandbox_reports_an_existing_one_and_invites_the_agent(self):
        description = "Sandbox for agent-repo-governance live checks; not a governed repository."
        recording = self.path("gh.json")
        with open(recording, "w") as handle:
            json.dump({"tool": "gh", "calls": [
                ow.call(["repo", "view", PUBLIC, "--json", "nameWithOwner"], "", 1,
                        "GraphQL: Could not resolve to a Repository with the name 'Habit130/governance-sandbox'.\n"),
                ow.call(["repo", "create", PUBLIC, "--public", "--description", description],
                        "https://github.com/%s\n" % PUBLIC),
                ow.ok(["repo", "view", PRIVATE, "--json", "nameWithOwner"], {"nameWithOwner": PRIVATE}),
                ow.ok(["api", "--method", "PUT", "repos/%s/collaborators/Habit098" % PUBLIC], {"id": 1}),
                ow.call(["api", "--method", "PUT", "repos/%s/collaborators/Habit098" % PRIVATE], ""),
            ]}, handle)
        result, log, scratch = self.run_line(live.sandbox_command(), recording)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "已创建：%s（public）" % PUBLIC,
            "已邀请：Habit098 以 write 权限加入 %s（已是协作者时无需再接受）" % PUBLIC,
            "已存在：%s，未重新创建" % PRIVATE,
            "已邀请：Habit098 以 write 权限加入 %s（已是协作者时无需再接受）" % PRIVATE,
        ])
        self.assertEqual([entry["recorded"] for entry in log], [True] * 5)
        self.assertFalse(any(entry["args"][:2] == ["repo", "delete"] for entry in log))
        self.assertFalse(ms.ghm_called(scratch))
        self.assertIn('export GH_CONFIG_DIR="$HOME/.config/gh-maintainer"', live.sandbox_command())

    def test_the_private_secret_command_parses_under_bash_and_names_the_private_sandbox(self):
        (_, _, line), = owner_probes.secret_commands(probes.Context(PRIVATE, "private", "main", {}, COMMIT, 1, "/x"))
        self.assertTrue(line.startswith("/bin/bash -c '") and line.endswith("'"))
        self.assertEqual(subprocess.run(["/bin/bash", "-n", "-c", line[len("/bin/bash -c '"):-1]]).returncode, 0)
        self.assertIn("r=%s;" % PRIVATE, line)
        self.assertIn('export GH_CONFIG_DIR="$HOME/.config/gh-maintainer"', line)

    def test_the_rerun_probe_hands_habit_the_one_owner_script_command_and_the_runner_the_first(self):
        from govlib import owner

        context = probes.Context(PUBLIC, "public", "main", {}, COMMIT, 1, "/x")
        (name, _, line), = probes.registered()["owner-rerun"].commands(context)
        self.assertEqual((name, line), ("owner_rerun", owner.command(PUBLIC)))
        self.assertEqual(probes.registered()["owner-report"].commands(context), [])
        self.assertEqual(live.OWNER_REPORT, "owner_report")


if __name__ == "__main__":
    unittest.main()
