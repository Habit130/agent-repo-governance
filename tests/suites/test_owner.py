"""The owner script (#44 §7, #41 §7): Seam D, against the stand-in GitHub only.

Each case under `tests/fixtures/owner/cases/` renders its version (default 1) into the tally sample with the
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


def _add_case(name, case):
    def test(self):
        result = self.run_case(case)
        self.assert_safe(result)
        expected = [(write[0], write[1]) for write in case.get("writes", [])]
        self.assertEqual(ow.writes(result["log"]), expected, result["out"])
        self.assertEqual([list(line) for line in ow.report_lines(result["out"])], case["report"], result["out"])
        self.assertEqual(result["code"], case["exit"], result["out"])
        if "accepted" in case:
            with open(os.path.join(os.path.dirname(result["scratch"]), "gh.json")) as handle:
                calls = json.load(handle)["calls"]
            accepted = [entry for entry in result["log"] if calls[entry["call"]]["exit"] == 0]
            self.assertEqual(ow.writes(accepted), [tuple(w) for w in case["accepted"]])
            self.assertIn(case["total"], result["out"].splitlines()[-1])
            for status, subject, detail in case["items"]:
                line, = (s for s in result["out"].splitlines() if s.startswith("[%s] %s：" % (status, subject)))
                self.assertIn(detail, line)

    test.__doc__ = "owner case %s" % name
    setattr(SeamD, "test_" + re.sub(r"[^A-Za-z0-9]+", "_", name), test)


for _name, _case in ow.cases():
    _add_case(_name, _case)


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

    def test_bounded_observation_never_repeats_the_permission_write(self):
        with open(os.path.join(support.FIXTURES, "owner", "v2-workflow-observation.json")) as handle:
            rows = json.load(handle)["cases"]
        for row in rows:
            with self.subTest(case=row["name"]):
                case = ow.load_case("rerun-at-target")
                case["version"] = 2
                case["github"] = {"workflow": {
                    "default_workflow_permissions": row["default"], "can_approve_pull_request_reviews": True,
                }, "workflow_after_reads": row["reads"]}
                case["writes"] = [["PUT", "actions/permissions/workflow", {
                    "default_workflow_permissions": row["default"], "can_approve_pull_request_reviews": False,
                }]]
                result = self.run_case(case)
                self.assert_safe(result)
                self.assertEqual(result["code"], row["exit"], result["out"])
                self.assertEqual(ow.writes(result["log"]), [("PUT", "actions/permissions/workflow")])
                reads = [entry for entry in result["log"] if entry["args"] == ow.api("/actions/permissions/workflow")]
                self.assertEqual(len(reads), 1 + row["observations"])
                self.assertEqual(("已设置", "Actions 不能创建或批准 PR") in ow.report_lines(result["out"]), row["exit"] == 0)
                self.assertTrue(result["out"].splitlines()[-1].startswith("写入 1 项；"), result["out"])

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
                observations = 3 if row["name"] in ("approval-still-enabled", "read-refused") else 1
                self.assertEqual(permission_calls, [ow.api("/actions/permissions/workflow"),
                                                   ow.write_args("PUT", "/actions/permissions/workflow")]
                                 + [ow.api("/actions/permissions/workflow")] * observations)
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


EVENT_POLICY_SUBJECT = "pull_request_target 事件策略"
# Version 4's sentence on what a missing event policy blocks (#169), written out here rather than read from the script.
EVENT_POLICY_CONSEQUENCE = (
    "自 2026-12-02 起，没有这条策略时 GitHub 会在此仓库拦截 pull_request_target，governance-gate 就不会报告结果，"
    "设好这条策略之前任何 PR 都无法合并"
)
EVENT_POLICY_BY_HAND = "请在 Settings → Actions → Policies 手动设一次："
EVENT_POLICY_RERUN = "设好后重新运行本脚本确认"
V4_TEMPLATE = os.path.join(support.REAL_STORE, "4", "templates", "dot-github", "governance", "owner.sh")


class VersionFourEventPolicy(OwnerCase):
    """Version 4's missing event policy says what it blocks; its private skip line is version 3's."""

    def event_policy_line(self, case):
        result = self.run_case(case)
        self.assert_safe(result)
        (detail,) = [detail for _, subject, detail in ms.lines(result["out"]) if subject == EVENT_POLICY_SUBJECT]
        return result, detail

    def test_a_missing_policy_says_what_it_blocks_with_the_manual_steps(self):
        for name in ("v4-event-policy-api-cannot-create", "v4-event-policy-unreadable"):
            result, detail = self.event_policy_line(ow.load_case(name))
            self.assertEqual(result["code"], 1, name)
            self.assertIn("[缺失] %s：" % EVENT_POLICY_SUBJECT, result["out"], name)
            self.assertIn(EVENT_POLICY_CONSEQUENCE, detail, name)
            self.assertIn(EVENT_POLICY_BY_HAND, detail, name)
            self.assertTrue(detail.endswith(EVENT_POLICY_RERUN), detail)

    def test_version_3s_missing_policy_line_stays_as_it_was(self):
        case = ow.load_case("v4-event-policy-api-cannot-create")
        case["version"] = 3
        _, detail = self.event_policy_line(case)
        self.assertNotIn("2026-12-02", detail)

    def test_every_missing_line_in_the_template_carries_the_consequence(self):
        program = embedded_program(support.read_text(V4_TEMPLATE))
        missing = [line for line in program.splitlines() if 'report.line("缺失", EVENT_POLICY_SUBJECT' in line]
        self.assertEqual(len(missing), 3, missing)
        for line in missing:
            self.assertIn("EVENT_POLICY_MISSING", line)
            self.assertNotIn("EVENT_POLICY_BY_HAND", line)

    def test_a_private_repositorys_skip_line_is_version_3s(self):
        details = []
        for version in (3, 4):
            case = ow.load_case("private-from-nothing")
            case["version"] = version
            result, detail = self.event_policy_line(case)
            self.assertIn("[已跳过] %s：" % EVENT_POLICY_SUBJECT, result["out"])
            details.append(detail)
        self.assertEqual(details[0], details[1])
        self.assertNotIn("2026-12-02", details[1])


class Program(unittest.TestCase):
    def test_supplemental_corpus_has_exact_generated_pairs_and_ruby_verdicts(self):
        from ref_patterns import generate_pairs, SEEDS

        with open(os.path.join(support.FIXTURES, "owner", "ref-patterns-generated.json")) as handle:
            fixture = json.load(handle)
        self.assertEqual(fixture["seeds"], list(SEEDS))
        self.assertEqual(fixture["oracle"]["expression"], "File.fnmatch(pattern, string, File::FNM_PATHNAME)")
        self.assertTrue(fixture["oracle"]["ruby_version"])
        rows = fixture["cases"]
        self.assertEqual([row[:2] for row in rows], generate_pairs())
        fnmatch = self.program_functions("_bracket", "_component", "fnmatch")["fnmatch"]
        for pattern, string, expected in rows:
            with self.subTest(pattern=pattern, string=string):
                self.assertIsInstance(expected, bool)
                self.assertIs(fnmatch(pattern, string), expected)

    def test_generated_pairs_are_bounded_repeatable_and_cover_pattern_families(self):
        script = os.path.join(support.REPO, "tests", "ref_patterns.py")
        code, out, err = support.run_cli(script, ["pairs"])
        self.assertEqual(code, 0, err)
        self.assertEqual(support.run_cli(script, ["pairs"]), (code, out, err))
        pairs = json.loads(out)
        self.assertGreater(len(pairs), 1000)
        self.assertLessEqual(len(pairs), 20000)
        self.assertEqual(len(pairs), len(set(tuple(pair) for pair in pairs)))
        for pattern, string in (
            ("refs/heads/[!-z]ain", "refs/heads/main"),
            ("refs/heads/[m-a]ain", "refs/heads/main"),
            ("refs/heads/[a-z]ain", "refs/heads/main"),
            ("refs/heads/**/main", "refs/heads/main"),
            ("refs/heads/**//main", "refs/heads/a//main"),
            ("refs/heads/*", "refs/heads/a/b"),
            ("refs/heads/\\*", "refs/heads/*"),
        ):
            self.assertIn([pattern, string], pairs)

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
    def assert_checkout_removed(self, temporary):
        # macOS's xcrun shims may leave this cache in TMPDIR (see machine_support.snapshot).
        # Only the exact regular file is exempt; directories, links and unknown entries fail.
        remaining = [name for name in os.listdir(temporary)
                     if not (name == "xcrun_db" and os.path.isfile(os.path.join(temporary, name))
                             and not os.path.islink(os.path.join(temporary, name)))]
        self.assertEqual(remaining, [], "the temporary checkout was not removed")

    def test_cleanup_accepts_an_empty_directory_or_only_the_os_cache(self):
        temporary = self.path("tmp")
        os.mkdir(temporary)
        self.assert_checkout_removed(temporary)
        with open(os.path.join(temporary, "xcrun_db"), "w") as handle:
            handle.write("synthetic OS tool cache\n")
        self.assert_checkout_removed(temporary)

    def test_cleanup_rejects_a_retained_checkout_with_or_without_the_os_cache(self):
        for cached in (False, True):
            with self.subTest(cached=cached):
                temporary = tempfile.mkdtemp(dir=self.tmp)
                # Keep a real owned checkout instead of removing it, as the command must do.
                checkout = support.init_repo(os.path.join(temporary, "tmp.retained"))
                if cached:
                    support.write_tree(temporary, {"xcrun_db": "synthetic OS tool cache\n"})
                with self.assertRaisesRegex(AssertionError, "the temporary checkout was not removed"):
                    self.assert_checkout_removed(temporary)
                self.assertTrue(os.path.isdir(checkout))

    def test_cleanup_rejects_unknown_entries_and_non_file_cache_names(self):
        for kind in ("unknown-file", "directory", "link"):
            with self.subTest(kind=kind):
                temporary = tempfile.mkdtemp(dir=self.tmp)
                cache = os.path.join(temporary, "xcrun_db")
                if kind == "unknown-file":
                    support.write_tree(temporary, {"xcrun_db.extra": "unknown\n"})
                elif kind == "directory":
                    os.mkdir(cache)
                else:
                    target = self.path("cache-target")
                    with open(target, "w") as handle:
                        handle.write("cache\n")
                    os.symlink(target, cache)
                with self.assertRaisesRegex(AssertionError, "the temporary checkout was not removed"):
                    self.assert_checkout_removed(temporary)

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
        self.assert_checkout_removed(os.path.join(home, "tmp"))
        self.assertFalse(ms.ghm_called(scratch))


if __name__ == "__main__":
    unittest.main()
