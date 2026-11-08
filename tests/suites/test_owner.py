"""The owner script (#44 §7, #41 §7): Seam D, against the stand-in GitHub only.

Each case under `tests/fixtures/owner/cases/` renders version 1 into the tally sample with the
case's record, serves the case's GitHub state through the stand-in `gh`, runs the rendered
`.github/governance/owner.sh` the way the owner-script command does, and checks the exit code, every
write with its exact body, and every report line (`owner_support.py` gives the case format).
The `ghm` tripwire sits first on the path, so no case can reach the maintainer account.
"""

import ast
import json
import os
import re
import subprocess
import tempfile
import unittest

import machine_support as ms
import owner_support as ow
import support
from standins import environment

TEMPLATE = os.path.join(support.REAL_STORE, "1", "templates", "dot-github", "governance", "owner.sh")
NOT_A_TOKEN = "gho_seamDsentinel0000000000000000000000"


def embedded_program(text):
    """The Python program owner.sh feeds to the interpreter: the body of its one quoted heredoc."""
    match = re.search(r"(?m)^exec /usr/bin/python3 -I - \"\$here\" \"\$@\" <<'PY'\n(.*?)^PY\n", text, re.S)
    if not match:
        raise AssertionError("owner.sh has no `<<'PY'` heredoc fed to /usr/bin/python3")
    return match.group(1)


class OwnerCase(support.TempDirCase):
    def run_case(self, case, extra_env=None):
        root = tempfile.mkdtemp(dir=self.tmp)
        worktree, head = ow.prepare(root, case)
        recording = ow.recording(case, head, os.path.join(root, "gh.json"))
        env, home, scratch = ow.owner_env(root, recording, extra=extra_env)
        code, out, err = ow.run_owner(os.path.join(worktree, *ow.SCRIPT.split("/")), env)
        log = environment.read_log(scratch)
        return {"code": code, "out": out, "err": err, "log": log, "scratch": scratch, "worktree": worktree}

    def assert_safe(self, result):
        self.assertFalse(ms.ghm_called(result["scratch"]), "the owner script called ghm")
        unrecorded = [entry["args"] for entry in result["log"] if not entry["recorded"]]
        self.assertEqual(unrecorded, [], result["out"] + result["err"])
        self.assertFalse(any(entry["args"][:2] == ["auth", "token"] for entry in result["log"]))
        self.assertNotIn(NOT_A_TOKEN, result["out"] + result["err"])
        self.assertEqual(result["err"], "")


class SeamD(OwnerCase):
    """Filled below: one test per case file."""


def _add_case(name):
    def test(self):
        case = ow.load_case(name)
        result = self.run_case(case)
        self.assert_safe(result)
        expected = [(write[0], write[1]) for write in case.get("writes", [])]
        self.assertEqual(ow.writes(result["log"]), expected, result["out"])
        self.assertEqual([list(line) for line in ow.report_lines(result["out"])], case["report"], result["out"])
        self.assertEqual(result["code"], case["exit"], result["out"])

    test.__doc__ = "owner case %s" % name
    setattr(SeamD, "test_" + re.sub(r"[^A-Za-z0-9]+", "_", name), test)


for _file in sorted(os.listdir(ow.CASES)):
    _add_case(_file[: -len(".json")])


class Report(OwnerCase):
    def test_a_rerun_at_target_state_says_it_wrote_nothing(self):
        result = self.run_case(ow.load_case("rerun-at-target"))
        self.assertEqual(result["out"].splitlines()[-1], "写入 0 项；全部已就位，本次未改动 GitHub")

    def test_a_run_from_nothing_counts_its_writes(self):
        case = ow.load_case("public-from-nothing")
        result = self.run_case(case)
        changed = [line for line in ow.report_lines(result["out"]) if line[0] in ("已设置", "已移除")]
        self.assertEqual(result["out"].splitlines()[-1], "写入 %d 项；全部就位" % len(changed))
        self.assertGreaterEqual(len(changed), len(case["writes"]))

    def test_the_account_line_names_the_gh_configuration_and_no_credential(self):
        result = self.run_case(ow.load_case("rerun-at-target"))
        line = [line for line in result["out"].splitlines() if line.startswith("[通过] 账户：")][0]
        self.assertIn("gh 以所有者 Habit130 身份操作 Habit130/tally", line)
        self.assertIn("gh 配置：", line)

    def test_a_token_variable_stops_the_run_before_any_read_and_is_never_printed(self):
        result = self.run_case(ow.load_case("rerun-at-target"))
        env, _, scratch = ow.owner_env(self.path("again"), self.path("gh.json"))
        env["GH_TOKEN"] = NOT_A_TOKEN
        code, out, err = ow.run_owner(os.path.join(result["worktree"], *ow.SCRIPT.split("/")), env)
        self.assertEqual(code, 2, out)
        self.assertIn("设置了 GH_TOKEN", out)
        self.assertNotIn(NOT_A_TOKEN, out + err)
        self.assertEqual(environment.read_log(scratch), [])

    def test_the_wrong_account_and_a_stale_copy_read_and_never_write(self):
        for name in ("wrong-account", "not-the-default-branch-head", "modified-copy"):
            result = self.run_case(ow.load_case(name))
            self.assertEqual(result["code"], 2, result["out"])
            self.assertEqual(ow.writes(result["log"]), [], name)
            self.assertIn("未写入任何内容", result["out"], name)


class VersionTwoPermissions(OwnerCase):
    """#122: preserve the existing default while disabling Actions approval, at Seam D."""

    def test_success_requires_the_post_write_permission_readback(self):
        with open(os.path.join(support.FIXTURES, "owner", "v2-workflow-postcondition.json")) as handle:
            rows = json.load(handle)["cases"]
        for row in rows:
            with self.subTest(case=row["name"]):
                case = ow.load_case("rerun-at-target")
                case["version"] = 2
                case["github"] = {"workflow": {
                    "default_workflow_permissions": row["default"], "can_approve_pull_request_reviews": True,
                }}
                if "error" in row:
                    case["github"]["workflow_after_error"] = row["error"]
                else:
                    case["github"]["workflow_after"] = row["after"]
                case["writes"] = [["PUT", "actions/permissions/workflow", {
                    "default_workflow_permissions": row["default"], "can_approve_pull_request_reviews": False,
                }]]
                result = self.run_case(case)
                self.assert_safe(result)
                self.assertEqual(result["code"], row["exit"], result["out"])
                self.assertEqual(ow.writes(result["log"]), [("PUT", "actions/permissions/workflow")])
                permission_calls = [entry["args"] for entry in result["log"]
                                    if "repos/Habit130/tally/actions/permissions/workflow" in entry["args"]]
                self.assertEqual(permission_calls, [ow.api("/actions/permissions/workflow"),
                                                   ow.write_args("PUT", "/actions/permissions/workflow"),
                                                   ow.api("/actions/permissions/workflow")])
                self.assertEqual(("已设置", "Actions 不能创建或批准 PR") in ow.report_lines(result["out"]), row["exit"] == 0)
                self.assertTrue(result["out"].splitlines()[-1].startswith("写入 1 项；"), result["out"])

    def test_disabling_approval_preserves_read_default(self):
        case = ow.load_case("rerun-at-target")
        case["version"] = 2
        case["github"] = {"workflow": {
            "default_workflow_permissions": "read", "can_approve_pull_request_reviews": True,
        }}
        case["writes"] = [["PUT", "actions/permissions/workflow", {
            "default_workflow_permissions": "read", "can_approve_pull_request_reviews": False,
        }]]
        result = self.run_case(case)
        self.assert_safe(result)
        self.assertEqual(result["code"], 0, result["out"])
        self.assertEqual(ow.writes(result["log"]), [("PUT", "actions/permissions/workflow")])

    def test_an_invalid_permission_read_fails_without_writing(self):
        case = ow.load_case("rerun-at-target")
        case["version"] = 2
        case["github"] = {"workflow_response": {
            "default_workflow_permissions": "admin", "can_approve_pull_request_reviews": False,
        }}
        result = self.run_case(case)
        self.assert_safe(result)
        self.assertEqual(result["code"], 1, result["out"])
        self.assertEqual(ow.writes(result["log"]), [])
        self.assertIn(("未通过", "Actions 不能创建或批准 PR"), ow.report_lines(result["out"]))

    def test_both_defaults_disabled_approval_and_invalid_responses(self):
        with open(os.path.join(support.FIXTURES, "owner", "v2-workflow-permissions.json")) as handle:
            fixture = json.load(handle)
        for valid, states in ((True, fixture["valid"]), (False, fixture["invalid"])):
            for state in states:
                with self.subTest(valid=valid, state=state):
                    case = ow.load_case("rerun-at-target")
                    case["version"] = 2
                    response = dict(state, unrelated_setting="preserved") if valid else state
                    case["github"] = {"workflow_response": response}
                    if valid and state["can_approve_pull_request_reviews"]:
                        case["writes"] = [["PUT", "actions/permissions/workflow", {
                            "default_workflow_permissions": state["default_workflow_permissions"],
                            "can_approve_pull_request_reviews": False,
                        }]]
                    result = self.run_case(case)
                    self.assert_safe(result)
                    self.assertEqual(result["code"], 0 if valid else 1, result["out"])
                    self.assertEqual(ow.writes(result["log"]), [(w[0], w[1]) for w in case["writes"]])

    def test_failed_write_can_be_retried_and_its_result_needs_no_further_write(self):
        case = ow.load_case("rerun-at-target")
        case["version"] = 2
        case["github"] = {"workflow": {
            "default_workflow_permissions": "write", "can_approve_pull_request_reviews": True,
        }}
        case["writes"] = [["PUT", "actions/permissions/workflow", {
            "default_workflow_permissions": "write", "can_approve_pull_request_reviews": False,
        }]]
        case["answers"] = {"PUT actions/permissions/workflow": {"status": 503, "message": "Unavailable"}}
        failed = self.run_case(case)
        self.assert_safe(failed)
        self.assertEqual(failed["code"], 1, failed["out"])
        self.assertNotIn(("已设置", "Actions 不能创建或批准 PR"), ow.report_lines(failed["out"]))
        del case["answers"]
        recovered = self.run_case(case)
        self.assert_safe(recovered)
        self.assertEqual(recovered["code"], 0, recovered["out"])
        case["github"]["workflow"]["can_approve_pull_request_reviews"] = False
        case["writes"] = []
        rerun = self.run_case(case)
        self.assert_safe(rerun)
        self.assertEqual(rerun["code"], 0, rerun["out"])
        self.assertEqual(ow.writes(rerun["log"]), [])

    def test_unreadable_permissions_do_not_write_a_guessed_value(self):
        case = ow.load_case("rerun-at-target")
        case["version"] = 2
        case["github"] = {"failing_reads": {"actions/permissions/workflow": 503}}
        result = self.run_case(case)
        self.assert_safe(result)
        self.assertNotEqual(result["code"], 0, result["out"])
        self.assertEqual(ow.writes(result["log"]), [])


class VersionTwoApplication(OwnerCase):
    def test_checkout_only_allowlist_and_existing_record_need_no_new_setup(self):
        case = ow.load_case("rerun-at-target")
        case.update(version=2)
        case["github"] = {
            "actions": {"allowed_actions": "selected"},
            "selected_actions": {"github_owned_allowed": False, "patterns_allowed": ["actions/checkout@*"]},
        }
        result = self.run_case(case)
        self.assert_safe(result)
        self.assertEqual(result["code"], 0, result["out"])
        self.assertEqual(ow.writes(result["log"]), [])


class Program(unittest.TestCase):
    def test_the_entry_is_bash_3_2_with_the_notice_on_line_two(self):
        text = support.read_text(TEMPLATE)
        lines = text.split("\n")
        self.assertEqual(lines[0], "#!/bin/bash")
        self.assertEqual(lines[1], "# Generated by governance model version @@version@@. Only the generator changes this file.")
        self.assertEqual(support.file_mode(TEMPLATE), "100755")
        self.assertEqual(subprocess.run(["/bin/bash", "-n", TEMPLATE]).returncode, 0)

    def test_the_embedded_program_parses_as_python_3_9_and_holds_no_placeholder(self):
        program = embedded_program(support.read_text(TEMPLATE))
        ast.parse(program, filename="owner.sh's program", feature_version=(3, 9))
        self.assertNotIn("@@", program)
        self.assertEqual(support.read_text(TEMPLATE).count("@@"), 2, "only the notice's @@version@@ token")

    def program_functions(self, *names):
        tree = ast.parse(embedded_program(support.read_text(TEMPLATE)))
        nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.Assign))
                 and (getattr(node, "name", None) in names
                      or any(getattr(target, "id", None) == "UNREADABLE_FORMS" for target in getattr(node, "targets", [])))]
        namespace = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "owner.sh's program", "exec"), namespace)
        return namespace

    def test_its_ref_patterns_read_as_rubys_fnmatch_on_every_recorded_row(self):
        fnmatch = self.program_functions("_bracket", "_component", "fnmatch")["fnmatch"]
        with open(os.path.join(support.FIXTURES, "owner", "ref-patterns.json")) as handle:
            rows = json.load(handle)["cases"]
        wrong = [(pattern, string, expected) for pattern, string, expected in rows if fnmatch(pattern, string) != expected]
        self.assertEqual(wrong, [])
        self.assertGreater(len(rows), 8000)
        self.assertGreater(sum(1 for _, _, expected in rows if expected), 2000)

    def test_a_pattern_github_cant_read_leaves_the_rulesets_reach_unknown(self):
        applies_to = self.program_functions("_bracket", "_component", "fnmatch", "applies_to")["applies_to"]

        def ruleset(include, exclude=()):
            return {"target": "branch", "conditions": {"ref_name": {"include": list(include), "exclude": list(exclude)}}}

        self.assertIsNone(applies_to(ruleset(["~ALL"], ["refs/heads/ma\\in"]), "main"))
        self.assertIsNone(applies_to(ruleset(["refs/heads/[^x]ain"]), "main"))
        self.assertIs(applies_to(ruleset(["~ALL"], ["refs/heads/[!-z]ain"]), "main"), False)
        self.assertIs(applies_to(ruleset(["refs/heads/[!-z]ain"]), "main"), True)
        self.assertIs(applies_to({"target": "tag", "conditions": {"ref_name": {"include": ["\\"]}}}, "main"), False)

    def test_it_imports_the_gate_scripts_parser_and_adds_no_file(self):
        program = embedded_program(support.read_text(TEMPLATE))
        self.assertIn("sys.dont_write_bytecode = True\nGOVERNANCE = sys.argv[1]\nsys.path.insert(0, GOVERNANCE)\n", program)
        self.assertIn("\nimport gate  # noqa: E402\n", program)
        self.assertIn("gate.parse_record(", program)


class OwnerCommand(support.TempDirCase):
    def command(self, repository=ow.REPOSITORY):
        code, facts = support.govern(["owner-command", "--repository", repository])
        self.assertEqual(code, 0, facts)
        return facts["command"]

    def test_it_is_one_bash_line_and_build_md_quotes_its_form(self):
        line = self.command("OWNER/NAME")
        self.assertTrue(line.startswith("/bin/bash -c '") and line.endswith("'"))
        self.assertEqual(subprocess.run(["/bin/bash", "-n", "-c", line[len("/bin/bash -c '"):-1]]).returncode, 0)
        self.assertIn(line, support.read_text(os.path.join(support.REPO, "docs", "agents", "build.md")))
        self.assertIn('GH_CONFIG_DIR="$HOME/.config/gh-maintainer"', line)
        self.assertNotIn("ghm", line)

    def test_it_refuses_anything_but_owner_slash_name(self):
        for bad in ("tally", "Habit130/tally;rm -rf ~", "Habit130/tally.git", "Habit130/'x'"):
            code, facts = support.govern(["owner-command", "--repository", bad])
            self.assertEqual(code, 2, bad)

    @unittest.skipUnless(os.path.exists("/usr/bin/python3"), "owner.sh runs /usr/bin/python3, as on macOS")
    def test_it_runs_origins_default_branch_head_from_a_removed_temporary_checkout(self):
        case = ow.load_case("rerun-at-target")
        worktree, head = ow.prepare(self.tmp, case)
        bare = self.path("origin.git")
        subprocess.run(["git", "clone", "-q", "--bare", worktree, bare], check=True, env=support.isolated_env())
        # Local work that origin doesn't hold, which the command must not run.
        support.git(worktree, "commit", "-q", "--allow-empty", "-m", "local only")
        config = self.path("gitconfig")
        with open(config, "w") as handle:
            handle.write('[url "file://%s"]\n\tinsteadOf = https://github.com/%s.git\n' % (bare, ow.REPOSITORY))
        recording = ow.recording(case, head, self.path("gh.json"))
        env, home, scratch = ow.owner_env(self.tmp, recording, extra={"GIT_CONFIG_GLOBAL": config})
        env["GH_TOKEN"] = NOT_A_TOKEN
        result = subprocess.run(["/bin/bash", "-c", self.command()[len("/bin/bash -c '"):-1]], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                                stdin=subprocess.DEVNULL)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("gh 配置：~/.config/gh-maintainer", result.stdout)
        self.assertIn("[通过] 副本：%s 是 main 的最新提交" % head[:12], result.stdout)
        self.assertNotIn(NOT_A_TOKEN, result.stdout + result.stderr)
        self.assertEqual(ow.writes(environment.read_log(scratch)), [])
        self.assertEqual(os.listdir(os.path.join(home, "tmp")), [], "the temporary checkout was not removed")
        self.assertFalse(ms.ghm_called(scratch))


if __name__ == "__main__":
    unittest.main()
