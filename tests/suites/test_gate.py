"""The governance gate (#41 §8): Seam 1, the gate's verdict, plus its workflow and its entry.

Seam 1's input is the author, the body, the default branch's record and git objects for the
merge-base and the head; its output is pass or fail plus one line per failed rule. Each case
under `tests/fixtures/gate/cases/` builds a repository under the system temporary directory:

- the default branch starts from `base.json`'s tree with `record.yml` as the record, then
  takes the case's `default` commits;
- the head branches from the commit `branch_from` names and takes the case's `head` commits;
- a commit's `files` map paths to content, or to null for a deletion;
- `{name}` in the body becomes that commit's SHA.

`expected` names the failed rules in order, by the label each failure line starts with, and
whether the PR is a pure revert. The gate script loads from version 1's store.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import materialized
import parsers
import support
from standins import environment

gate = parsers.gate
FIXTURES = os.path.join(support.FIXTURES, "gate")
CASES = os.path.join(FIXTURES, "cases")
RECORD = ".github/governance/record.yml"
WORKFLOW = ".github/workflows/governance-gate.yml"
SCRIPT = ".github/governance/gate.py"


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def apply(repo, files, message):
    """Apply a commit's file map to the working tree and commit it; return the SHA."""
    for path, content in files.items():
        full = os.path.join(repo, *path.split("/"))
        if content is None:
            os.remove(full)
        else:
            support.write_tree(repo, {path: content})
    support.git(repo, "add", "-A")
    support.git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return support.git(repo, "rev-parse", "HEAD").strip()


def build(root, case):
    """The case's repository: (repo, the default branch's head, the PR's head, SHAs by commit name)."""
    repo = support.init_repo(tempfile.mkdtemp(prefix="repo-", dir=root))
    base = load(os.path.join(FIXTURES, "base.json"))["files"]
    files = dict(base, **{RECORD: support.read_text(os.path.join(FIXTURES, "record.yml"))})
    shas = {"base": apply(repo, files, "base")}
    for commit in case["default"]:
        shas[commit["name"]] = apply(repo, commit["files"], commit["name"])
    default_head = support.git(repo, "rev-parse", "HEAD").strip()
    support.git(repo, "checkout", "-q", "-b", "pr", shas[case["branch_from"]])
    for commit in case["head"]:
        shas[commit["name"]] = apply(repo, commit["files"], commit["name"])
    head = support.git(repo, "rev-parse", "HEAD").strip()
    support.git(repo, "checkout", "-q", "main")
    return repo, default_head, head, shas


def body_of(case, shas):
    body = case["body"]
    for name, sha in shas.items():
        body = body.replace("{%s}" % name, sha)
    return body


class GateCase(support.TempDirCase):
    def setUp(self):
        super(GateCase, self).setUp()
        patcher = mock.patch.dict(os.environ, support.isolated_env())
        patcher.start()
        self.addCleanup(patcher.stop)

    def judge(self, name):
        case = load(os.path.join(CASES, name + ".json"))
        repo, default_head, head, shas = build(self.tmp, case)
        result = gate.verdict(repo, case["author"], case["owner"], body_of(case, shas), default_head, head)
        return case, result


class SeamOne(GateCase):
    """Filled below: one test per case file."""


def _add_case(name):
    def test(self):
        case, result = self.judge(name)
        rules = [line.split(":", 1)[0] for line in result["failures"]]
        got = {"passed": result["passed"], "rules": rules, "pure_revert": result["pure_revert"]}
        self.assertEqual(got, case["expected"], result["failures"])

    test.__doc__ = "gate case %s" % name
    setattr(SeamOne, "test_" + re.sub(r"[^A-Za-z0-9]+", "_", name), test)


for _file in sorted(os.listdir(CASES)):
    _add_case(_file[: -len(".json")])


class FailureLines(GateCase):
    """Each failure is one plain English line naming its fix."""

    def failures(self, name):
        _, result = self.judge(name)
        for line in result["failures"]:
            self.assertNotIn("\n", line)
            self.assertIn(" Fix: ", line)
        return result["failures"]

    def test_an_outside_author_is_told_outside_prs_are_re_landed(self):
        (line,) = self.failures("outside-author")
        self.assertIn("someone-else", line)
        self.assertIn("outside PRs are re-landed", line)

    def test_a_bad_reverts_line_names_the_squash_commit_or_deletion(self):
        for name in ("reverts-malformed", "reverts-off-default-branch", "reverts-unknown-sha", "reverts-doubled"):
            line = self.failures(name)[0]
            self.assertTrue(line.startswith("Pure revert: "), line)
            self.assertIn("name the squash commit or delete the line", line)

    def test_the_floor_line_names_the_floor_the_path_and_the_tier_to_declare(self):
        (line,) = self.failures("rename-out-of-sensitive-path")
        self.assertIn('"src/auth/token.ts"', line)
        self.assertNotIn('"src/token.ts"', line)
        self.assertIn("high floor", line)
        self.assertIn("`Risk: high — <reason>`", line)

    def test_each_risk_line_problem_has_its_own_line(self):
        self.assertIn("no `Risk:` line", self.failures("risk-missing")[0])
        self.assertIn("more than one `Risk:` line", self.failures("risk-doubled")[0])
        self.assertIn("malformed", self.failures("risk-malformed")[0])


class Patterns(unittest.TestCase):
    """#44 §4's pattern rules: root-relative, case-sensitive, `*` in one segment, `**` across any."""

    def test_double_star_matches_any_number_of_segments_none_included(self):
        for path in ("AGENTS.md", "a/AGENTS.md", "a/b/c/AGENTS.md"):
            self.assertTrue(gate.matches("**/AGENTS.md", path), path)
        self.assertTrue(gate.matches("docs/agents/**", "docs/agents/a/b.md"))
        self.assertTrue(gate.matches("deploy/**/secret*.env", "deploy/secret.env"))
        self.assertTrue(gate.matches("deploy/**/secret*.env", "deploy/a/b/secret-prod.env"))

    def test_single_star_stays_within_one_segment(self):
        self.assertTrue(gate.matches("src/*.ts", "src/a.ts"))
        self.assertFalse(gate.matches("src/*.ts", "src/a/b.ts"))
        self.assertTrue(gate.matches("src/*", "src/a"))
        self.assertFalse(gate.matches("src/*", "src/a/b"))
        self.assertFalse(gate.matches("src/*", "src"))
        self.assertTrue(gate.matches("src/a**b", "src/axxb"))
        self.assertFalse(gate.matches("src/a**b", "src/a/b"))

    def test_patterns_are_root_relative_and_case_sensitive(self):
        self.assertFalse(gate.matches("opencode.json", "a/opencode.json"))
        self.assertFalse(gate.matches("**/AGENTS.md", "agents.md"))
        self.assertFalse(gate.matches("**/AGENTS.md", "AGENTS.md.stored"))

    def test_nothing_else_is_special(self):
        self.assertTrue(gate.matches("src/?/config.json", "src/?/config.json"))
        self.assertFalse(gate.matches("src/?/config.json", "src/a/config.json"))
        self.assertTrue(gate.matches("src/{a,b}/[slug].ts", "src/{a,b}/[slug].ts"))
        self.assertFalse(gate.matches("src/{a,b}/[slug].ts", "src/a/s.ts"))
        self.assertFalse(gate.matches("src.ts", "srcxts"))


class RenderedGate(support.TempDirCase):
    """The workflow and the script as version 1 renders them into tally."""

    def setUp(self):
        super(RenderedGate, self).setUp()
        self.worktree, _ = materialized.render_version_one(self.tmp)

    def text(self, path):
        return support.read_text(os.path.join(self.worktree, *path.split("/")))


class Workflow(RenderedGate):
    def test_it_runs_on_pull_request_target_into_the_default_branch_on_pushes_and_body_edits(self):
        workflow = self.text(WORKFLOW)
        self.assertIn(
            "on:\n  pull_request_target:\n    types: [opened, edited, synchronize, reopened]\n"
            "    branches:\n      - \"main\"\n",
            workflow,
        )
        self.assertEqual(re.findall(r"(?m)^  ([a-z_]+):$", workflow.split("\npermissions:")[0]), ["pull_request_target"])

    def test_its_job_is_governance_gate_and_its_permissions_are_exact(self):
        workflow = self.text(WORKFLOW)
        self.assertIn("\njobs:\n  governance-gate:\n    name: governance-gate\n", workflow)
        self.assertIn("\npermissions:\n  contents: read\n  pull-requests: read\n  checks: write\n\n", workflow)
        self.assertEqual(workflow.count("permissions:"), 1)

    def test_no_step_checks_out_or_executes_the_prs_tree(self):
        workflow = self.text(WORKFLOW)
        steps = workflow.split("\n    steps:\n")[1]
        uses = re.findall(r"(?m)^ +(?:- )?uses: (\S+)", steps)
        self.assertEqual(len(uses), 1)
        self.assertRegex(uses[0], r"^actions/checkout@[0-9a-f]{40}$")
        # The checkout takes the default branch, which pull_request_target gives it, and no other ref.
        self.assertIsNone(re.search(r"(?m)^ +(ref|repository|path|allow-unsafe-pr-checkout):", steps))
        self.assertIn("persist-credentials: false", steps)
        runs = re.findall(r"(?m)^ +(?:- )?run:(.*)$", steps)
        self.assertEqual(runs, [" python3 .github/governance/gate.py --post-check"])
        # The only expressions read the run's token and the PR number; none feeds a `run:`.
        self.assertEqual(
            sorted(set(re.findall(r"\$\{\{(.*?)\}\}", workflow))),
            [" github.event.pull_request.number ", " github.token "],
        )

    def test_the_script_it_runs_is_rendered_beside_the_record(self):
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, *SCRIPT.split("/"))))
        self.assertTrue(os.path.isfile(os.path.join(self.worktree, *RECORD.split("/"))))


class SiblingImport(RenderedGate):
    def test_a_script_beside_the_gate_imports_its_parser(self):
        directory = os.path.join(self.worktree, ".github", "governance")
        sibling = os.path.join(directory, "sibling.py")
        with open(sibling, "w") as handle:
            handle.write(
                "import json, sys\n"
                "sys.dont_write_bytecode = True\n"
                "import gate\n"
                "with open(sys.argv[1], 'rb') as handle:\n"
                "    record = gate.parse_record(handle.read())\n"
                "body = gate.parse_body('Risk: medium \\u2014 a reason\\nReverts: %s\\n' % ('a' * 40))\n"
                "print(json.dumps([record['agent_account'], body, gate.matches('**/AGENTS.md', 'x/AGENTS.md')]))\n"
            )
        code, out, err = support.run_cli(sibling, [os.path.join(directory, "record.yml")])
        self.assertEqual(code, 0, err)
        self.assertEqual(
            json.loads(out),
            ["Habit098", {"risk": {"tier": "medium", "reason": "a reason"}, "reverts": {"sha": "a" * 40}}, True],
        )
        os.remove(sibling)
        self.assertEqual(sorted(os.listdir(directory)), ["gate.py", "record.yml"])


class Entry(GateCase):
    """The script's entry, as the workflow runs it: the event, a fetch of the head, and the check run."""

    def checkout(self, case_name):
        """An origin holding the case, and a checkout of its default branch alone; (checkout, head, case)."""
        case = load(os.path.join(CASES, case_name + ".json"))
        origin, default_head, head, shas = build(self.tmp, case)
        support.git(origin, "config", "uploadpack.allowReachableSHA1InWant", "true")
        checkout = self.path("checkout")
        support.git(self.tmp, "clone", "-q", "--single-branch", "--branch", "main", origin, checkout)
        self.assertEqual(support.git(checkout, "rev-parse", "HEAD").strip(), default_head)
        return checkout, head, dict(case, body=body_of(case, shas))

    def run_entry(self, checkout, head, case, conclusion, title, summary):
        event = self.path("event.json")
        with open(event, "w") as handle:
            json.dump(
                {
                    "pull_request": {"number": 7, "head": {"sha": head}, "user": {"login": case["author"]}, "body": case["body"]},
                    "repository": {"owner": {"login": case["owner"]}},
                },
                handle,
            )
        payload = {
            "name": "governance-gate",
            "head_sha": head,
            "status": "completed",
            "conclusion": conclusion,
            "output": {"title": title, "summary": summary},
        }
        recording = self.path("gh.json")
        with open(recording, "w") as handle:
            json.dump(
                {
                    "tool": "gh",
                    "calls": [
                        {
                            "args": ["api", "--method", "POST", "repos/Habit130/tally/check-runs", "--input", "-"],
                            "stdin": json.dumps(payload, sort_keys=True),
                            "stdout": "{}\n",
                            "exit": 0,
                        }
                    ],
                },
                handle,
            )
        scratch = self.path("scratch")
        os.makedirs(scratch)
        env = environment.environment(scratch, gh_recording=recording, base=support.isolated_env())
        env.update({"GITHUB_EVENT_PATH": event, "GITHUB_REPOSITORY": "Habit130/tally"})
        result = subprocess.run(
            [sys.executable, os.path.join(parsers.GATE), "--post-check"],
            cwd=checkout,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return result, environment.read_log(scratch)

    def test_it_fetches_the_head_judges_it_and_posts_a_passing_check_run(self):
        checkout, head, case = self.checkout("high-on-high-floor")
        result, calls = self.run_entry(checkout, head, case, "success", "Passed", "Every gate rule passed.")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True])
        self.assertIn("PASS every rule", result.stdout)
        # The head's objects were fetched; its tree was never checked out.
        self.assertEqual(support.git(checkout, "rev-parse", "HEAD").strip(), support.git(checkout, "rev-parse", "main").strip())
        self.assertEqual(support.git(checkout, "status", "--porcelain"), "")

    def test_a_failing_verdict_posts_a_failing_check_run_and_exits_one(self):
        checkout, head, case = self.checkout("rename-out-of-sensitive-path")
        _, failure = self.failure_line(case)
        result, calls = self.run_entry(checkout, head, case, "failure", "Failed: 1 rule", "- " + failure)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True])
        self.assertIn("FAIL " + failure, result.stdout)

    def failure_line(self, case):
        """The rename case's one failure line, written out from #41 §8 rather than from the gate."""
        return case, (
            'Floors: the PR declares low, and these changed paths have a high floor: "src/auth/token.ts". '
            "Fix: declare `Risk: high — <reason>`; no tier goes below a floor."
        )


if __name__ == "__main__":
    unittest.main()
