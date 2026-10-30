"""The live-check runner (#44 §11, §12) offline: its probes, its result comment and habit's commands.

The live check itself runs against the sandboxes and is its own evidence. Here the owner
script's probes read reports the owner script printed in Seam D, and the agent account's view
of a sandbox through the stand-in GitHub; the gate's probes judge a recorded setup and habit's
output in the shape the public sandbox printed; habit's commands run against the stand-in with the
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
    def test_the_gate_and_owner_probes_register_in_the_one_shape(self):
        known = probes.registered()
        self.assertEqual(list(known), ["gate-trigger", "gate-reruns", "gate-source", "gate-rulesets",
                                       "owner-report", "owner-state", "owner-rerun", "owner-private-secret"])
        for name in ("gate-trigger", "gate-reruns", "gate-source", "gate-rulesets"):
            self.assertEqual(known[name].sandboxes, ("public", "private"))
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

    def test_other_rulesets_are_judged_by_rubys_fnmatch_not_by_literal_forms(self):
        def other(name, ruleset_id, include, exclude=()):
            return ow.as_github({"name": name, "target": "branch", "enforcement": "active",
                                 "conditions": {"ref_name": {"include": list(include), "exclude": list(exclude)}},
                                 "rules": [{"type": "deletion"}]}, ruleset_id)

        kept = [other("all but m branches", 81, ["~ALL"], ["refs/heads/m*"]),
                other("all but dash and z", 82, ["~ALL"], ["refs/heads/[!-z]ain"])]
        self.with_github(agent_view(self.path("kept.json"), PUBLIC, target_rulesets() + kept, owner_probes.RULES_IN_EFFECT))
        self.assertEqual(self.failed(self.results("owner-state", self.context("public"))), [])

        extra = [other("m branches", 83, ["refs/heads/m*"]), other("main anywhere", 84, ["refs/heads/**/main"])]
        self.with_github(agent_view(self.path("extra.json"), PUBLIC, target_rulesets() + extra, owner_probes.RULES_IN_EFFECT))
        failed = self.failed(self.results("owner-state", self.context("public")))
        self.assertEqual(failed, [("no other ruleset applies to main", "m branches (id 83), main anywhere (id 84)")])

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


DEFAULT_HEAD, SOURCE, SOURCE_BRANCH = "a" * 40, "5" * 40, "live/gate-3-source"
HEADS = {"trigger": "1" * 40, "pushed": "2" * 40, "edit": "3" * 40, "failing": "4" * 40}
PULLS = {"trigger": 4, "edit": 5, "failing": 6}


def gate_run(run_id, head, conclusion, created_at="2026-10-30T08:01:00Z"):
    """One gate run as the setup reads it: the run, its log's judged line, the job's and the posted check run."""
    title = "Passed" if conclusion == "success" else "Failed: 1 rule"
    return {"id": run_id, "event": "pull_request_target", "path": ".github/workflows/governance-gate.yml", "head_sha": head,
            "conclusion": conclusion, "created_at": created_at, "judged": [head, DEFAULT_HEAD],
            "job": {"id": run_id * 10, "conclusion": conclusion, "app_id": 15368, "title": None, "completed_at": created_at},
            "posted": {"id": run_id * 10 + 1, "conclusion": conclusion, "app_id": 15368, "title": title,
                       "completed_at": created_at}}


def gate_setup():
    def pull(role, stages):
        return {"number": PULLS[role], "branch": "live/gate-3-%s" % role, "stages": stages}

    return {
        "default_head": DEFAULT_HEAD,
        "required": [{"context": "governance-gate", "integration_id": 15368}, {"context": "test"}],
        "source": {"branch": SOURCE_BRANCH, "commit": SOURCE, "gate_check_runs": 0,
                   "statuses": [{"context": "test", "state": "success", "creator": "Habit098"},
                                {"context": "governance-gate", "state": "success", "creator": "Habit098"}]},
        "pulls": {
            "trigger": pull("trigger", [
                {"step": "opened", "head": HEADS["trigger"], "at": None, "run": gate_run(1, HEADS["trigger"], "success")},
                {"step": "pushed", "head": HEADS["pushed"], "at": "2026-10-30T08:04:00Z",
                 "run": gate_run(5, HEADS["pushed"], "success", "2026-10-30T08:04:02Z")}]),
            "edit": pull("edit", [
                {"step": "opened", "head": HEADS["edit"], "at": None, "run": gate_run(2, HEADS["edit"], "failure")},
                {"step": "body fixed", "head": HEADS["edit"], "at": "2026-10-30T08:03:00Z",
                 "run": gate_run(4, HEADS["edit"], "success", "2026-10-30T08:03:01Z")}]),
            "failing": pull("failing", [
                {"step": "opened", "head": HEADS["failing"], "at": None, "run": gate_run(3, HEADS["failing"], "failure")}]),
        },
    }


def merge_rejection(*violations):
    message = "Repository rule violations found\n\n%s\n\n" % "\n\n".join(violations)
    return ('{"message":%s,"documentation_url":"https://docs.github.com/rest/pulls/pulls#merge-a-pull-request","status":"405"}'
            "gh: Repository rule violations found\n\n%s\n\n (HTTP 405)\n" % (json.dumps(message), "\n\n".join(violations)))


def push_rejection(ref, *violations):
    lines = ["remote: error: GH013: Repository rule violations found for refs/heads/%s.        " % ref,
             "remote: Review all repository rules at https://github.com/%s/rules?ref=refs%%2Fheads%%2F%s        " % (PUBLIC, ref),
             "remote: "]
    for violation in violations:
        lines += ["remote: - %s        " % violation, "remote: "]
    lines += ["To https://github.com/%s.git" % PUBLIC,
              " ! [remote rejected] HEAD -> %s (push declined due to repository rule violations)" % ref,
              "error: failed to push some refs to 'https://github.com/%s.git'" % PUBLIC]
    return "\n".join(lines) + "\n"


PUSH_VIOLATIONS = ("Changes must be made through a pull request.",
                   'Required status check "governance-gate" was not set by the expected GitHub app.',
                   "Cannot update this protected ref.")
UPDATE = "Cannot update this protected ref."
FAILING = 'Required status check "governance-gate" is failing.'


def gate_attempts(push=PUSH_VIOLATIONS, edit=(UPDATE,), push_exit=1, account="Habit098"):
    """habit's command's output, in the shape the public sandbox printed on 2026-10-30."""
    sections = [("account", account + "\n", 0), ("push %s to main" % SOURCE, push_rejection("main", *push), push_exit),
                ("force-push %s" % SOURCE_BRANCH, push_rejection(SOURCE_BRANCH, "Cannot force-push to this branch"), 1),
                ("merge %d at %s" % (PULLS["trigger"], HEADS["pushed"]), merge_rejection(UPDATE), 1),
                ("merge %d at %s" % (PULLS["edit"], HEADS["edit"]), merge_rejection(*edit), 1),
                ("merge %d at %s" % (PULLS["failing"], HEADS["failing"]), merge_rejection(FAILING, UPDATE), 1)]
    text = "".join("== %s\n%sexit=%d\n" % section for section in sections)
    return text + "== after\n%s\trefs/heads/main\n%s\trefs/heads/%s\n" % (DEFAULT_HEAD, SOURCE, SOURCE_BRANCH)


def sandbox_now(path, main=DEFAULT_HEAD, branch=SOURCE, merged=()):
    """The stand-in GitHub as the agent reads the refs and probe PRs when judging."""
    calls = [ow.ok(["api", "repos/%s/commits/main" % PUBLIC], {"sha": main}),
             ow.ok(["api", "repos/%s/git/ref/heads/%s" % (PUBLIC, SOURCE_BRANCH)], {"object": {"sha": branch}})]
    calls += [ow.ok(["api", "repos/%s/pulls/%d" % (PUBLIC, n)], {"number": n, "merged": n in merged}) for n in PULLS.values()]
    with open(path, "w") as handle:
        json.dump({"tool": "gh", "calls": calls}, handle)
    return path


GATE_PROBES = ("gate-trigger", "gate-reruns", "gate-source", "gate-rulesets")


class GateProbes(ProbeCase):
    def gate_context(self, visibility="public", setup=None, attempts=None, report="public-from-nothing"):
        inputs = {"owner_report": owner_report(tempfile.mkdtemp(prefix="report-", dir=self.tmp), report)}
        if attempts is not False:
            inputs["gate_attempts"] = attempts or gate_attempts()
        context = self.context(visibility, inputs)
        context.remember("gate_setup", setup or gate_setup())
        return context

    def failed_by(self, context):
        return dict((name, [a for a, _ in self.failed(self.results(name, context))]) for name in GATE_PROBES)

    def test_a_check_where_github_behaves_as_section_8_says_passes_every_assertion(self):
        self.with_github(sandbox_now(self.path("gh.json")))
        context = self.gate_context()
        for name in GATE_PROBES:
            results = self.results(name, context)
            self.assertEqual(self.failed(results), [], name)
            self.assertGreaterEqual(len(results), 4, name)
        details = " ".join(r.detail for r in self.results("gate-rulesets", context))
        self.assertIn("Cannot force-push to this branch", details)
        self.assertIn('Required status check "governance-gate" was not set by the expected GitHub app.', details)
        trigger = dict((r.assertion, r.detail) for r in self.results("gate-trigger", context))
        self.assertIn("the job's check run 10 (success) and the script's posted check run 11", " ".join(trigger.values()))
        self.assertIn("event pull_request_target, run 1, posted check run 11",
                      trigger["the gate's pull_request_target run completed on the head under the policy and posted its result there"])

    def test_an_agent_status_github_counted_fails_the_source_probe(self):
        self.with_github(sandbox_now(self.path("gh.json")))
        counted = gate_attempts(push=("Changes must be made through a pull request.", "Cannot update this protected ref."))
        failed = self.failed_by(self.gate_context(attempts=counted))
        self.assertEqual(failed["gate-source"],
                         ["pushing it to main, GitHub refuses the agent's governance-gate status as not from the expected app"])
        self.assertEqual(failed["gate-rulesets"], [])

    def test_a_control_check_github_names_fails_the_source_probe(self):
        self.with_github(sandbox_now(self.path("gh.json")))
        both = gate_attempts(push=PUSH_VIOLATIONS + ('Required status check "test" is expected.',))
        failed = self.failed_by(self.gate_context(attempts=both))
        self.assertEqual(failed["gate-source"],
                         ["the agent's status for a check with no app pinned counts, the control: GitHub names none of test"])

    def test_an_earlier_failure_that_still_counts_after_the_body_edit_fails_the_reruns_probe(self):
        self.with_github(sandbox_now(self.path("gh.json")))
        failed = self.failed_by(self.gate_context(attempts=gate_attempts(edit=(FAILING, UPDATE))))
        self.assertEqual(failed["gate-reruns"],
                         ["after the body edit, the agent's merge names no required check: the earlier failure no longer counts"])

    def test_a_body_edit_that_ran_no_new_gate_run_fails_the_reruns_probe(self):
        self.with_github(sandbox_now(self.path("gh.json")))
        setup = gate_setup()
        fixed = setup["pulls"]["edit"]["stages"][1]
        fixed["run"] = setup["pulls"]["edit"]["stages"][0]["run"]
        failed = self.failed_by(self.gate_context(setup=setup))
        self.assertEqual(failed["gate-reruns"],
                         ["a body edit that fixes the Risk line runs the gate again on the same head, and it passes"])

    def test_a_result_from_another_app_or_another_checkout_fails_the_trigger_probe(self):
        self.with_github(sandbox_now(self.path("gh.json")))
        setup = gate_setup()
        run = setup["pulls"]["trigger"]["stages"][0]["run"]
        run["posted"]["app_id"] = 1
        run["judged"] = [HEADS["trigger"], "b" * 40]
        failed = self.failed_by(self.gate_context(setup=setup))
        self.assertEqual(failed["gate-trigger"], [
            "the gate judged by the default branch's checkout",
            "its result lands on the head as governance-gate check runs from GitHub Actions: the job's and the script's posted one",
            "the gate's pull_request_target run completed on the head under the policy and posted its result there"])

    def test_an_attempt_that_went_through_fails_the_rulesets_probe(self):
        self.with_github(sandbox_now(self.path("gh.json"), main=SOURCE, merged=(PULLS["trigger"],)))
        through = gate_attempts(push=(), push_exit=0, account="Habit130")
        failed = self.failed_by(self.gate_context(attempts=through))
        self.assertEqual(failed["gate-rulesets"], ["habit's attempts ran as the agent account",
                                                   "the agent's direct push to main is rejected", "main didn't move",
                                                   "no probe PR merged"])

    def test_a_missing_attempts_output_or_a_stopped_setup_fails_each_probe_instead_of_skipping(self):
        failed = self.failed_by(self.gate_context(attempts=False))
        for name in GATE_PROBES:
            self.assertEqual(failed[name], ["%s ran" % name], name)

    def test_a_stopped_setup_fails_its_run_is_recorded_and_the_next_run_sets_up_afresh(self):
        self.with_github(self.path("nothing.json"))
        with open(self.path("nothing.json"), "w") as handle:
            json.dump({"tool": "gh", "calls": []}, handle)
        earlier = "`gh pr create --repo` failed: Post \"https://api.github.com/graphql\": EOF"
        stopped = self.gate_context(setup={"stopped": [earlier]})
        for count, name in enumerate(GATE_PROBES, 2):
            (result,) = self.results(name, stopped)
            self.assertFalse(result.passed)
            self.assertIn("repos/%s/commits/main" % PUBLIC, result.detail)
            self.assertIn("1 earlier attempt stopped" if count == 2 else "%d earlier attempts stopped" % (count - 1), result.detail)
            self.assertEqual(len(stopped.recall("gate_setup")["stopped"]), count)
            self.assertEqual(stopped.recall("gate_setup")["stopped"][0], earlier)
        self.assertFalse(os.path.exists(os.path.join(stopped.directory, "gate_targets.txt")))

    def test_a_setup_after_stopped_attempts_names_them_in_the_trigger_probe(self):
        self.with_github(sandbox_now(self.path("gh.json")))
        setup = dict(gate_setup(), stopped=["`gh pr create --repo` failed: EOF"])
        results = self.results("gate-trigger", self.gate_context(setup=setup))
        self.assertEqual(self.failed(results), [])
        self.assertIn("1 earlier setup attempt stopped first: `gh pr create --repo` failed: EOF", results[0].detail)

    def test_a_private_check_reports_the_event_policy_skipped(self):
        self.with_github(sandbox_now(self.path("gh.json")))
        context = self.gate_context("private", report="private-from-nothing")
        results = self.results("gate-trigger", context)
        self.assertEqual(self.failed(results), [])
        self.assertIn("the owner report skips the event policy on a private repository", [r.assertion for r in results])


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


class ProbeProvenance(support.TempDirCase):
    def test_a_checkout_other_than_the_prepared_commit_stops_before_any_probe_or_post(self):
        state = self.path("prepared.json")
        with open(state, "w") as handle:
            json.dump({"pr": 1, "commit": COMMIT, "sandbox": PUBLIC, "visibility": "public", "branch": "live/x",
                       "sandbox_pr": 4, "sandbox_head": "d" * 40, "probes": ["owner-state"]}, handle)
        with mock.patch.object(live, "gh_json", side_effect=AssertionError("GitHub was read")), \
                mock.patch("sys.stdout", new_callable=lambda: open(os.devnull, "w")):
            code = live.main(["probe", "--state", state, "--probe", "owner-state", "--post"])
        self.assertEqual(code, 2)


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

    def test_the_gate_attempts_command_parses_under_bash_and_names_the_sandbox_and_the_targets(self):
        for repository, visibility in ((PUBLIC, "public"), (PRIVATE, "private")):
            context = probes.Context(repository, visibility, "main", {}, COMMIT, 7, "/check dir")
            (name, _, line), = probes.registered()["gate-rulesets"].commands(context)
            self.assertEqual(name, "gate_attempts")
            self.assertTrue(line.startswith("/bin/bash -c '") and line.endswith("'"))
            self.assertEqual(subprocess.run(["/bin/bash", "-n", "-c", line[len("/bin/bash -c '"):-1]]).returncode, 0)
            self.assertIn("u=https://github.com/%s.git; r=%s; b=main;" % (repository, repository), line)
            self.assertIn('t="/check dir/gate_targets.txt"', line)
            self.assertNotIn("ghm", line)
        for name in ("gate-trigger", "gate-reruns", "gate-source"):
            self.assertEqual(probes.registered()[name].commands(context), [])

    def test_the_gate_attempts_command_stops_without_the_setup_runs_targets(self):
        context = probes.Context(PUBLIC, "public", "main", {}, COMMIT, 7, self.path("check"))
        (_, _, line), = probes.registered()["gate-rulesets"].commands(context)
        recording = self.path("empty.json")
        with open(recording, "w") as handle:
            json.dump({"tool": "gh", "calls": []}, handle)
        result, log, scratch = self.run_line(line, recording)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("gate_targets.txt", result.stdout)
        self.assertEqual(log, [])
        self.assertFalse(ms.ghm_called(scratch))

    def test_the_rerun_probe_hands_habit_the_one_owner_script_command_and_the_runner_the_first(self):
        from govlib import owner

        context = probes.Context(PUBLIC, "public", "main", {}, COMMIT, 1, "/x")
        (name, _, line), = probes.registered()["owner-rerun"].commands(context)
        self.assertEqual((name, line), ("owner_rerun", owner.command(PUBLIC)))
        self.assertEqual(probes.registered()["owner-report"].commands(context), [])
        self.assertEqual(live.OWNER_REPORT, "owner_report")


if __name__ == "__main__":
    unittest.main()
