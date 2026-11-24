"""The governance gate (#41 §8): Seam 1, the gate's verdict, plus its workflow and its entry.

Seam 1's input is the author, the body, the default branch's record and git objects for the
merge-base and the head; its output is pass or fail plus one line per failed rule. Each case
under `tests/fixtures/gate/cases/` builds a repository under the system temporary directory:

- the default branch starts from `base.json`'s tree with `record.yml` as the record, then
  takes the case's `default` commits;
- the head branches from the commit `branch_from` names and takes the case's `head` commits;
- a commit's `files` map paths to content, or to null for a deletion;
- `record_in`, when a case gives it, names the default commit that adds `record.yml`, and the
  first commit holds `base.json`'s tree alone, so the commits before it predate governance;
- `{name}` in the body becomes that commit's SHA.

`expected` names the failed rules in order, by the label each failure line starts with, and
whether the PR is a pure revert. The cases directly under `cases/` were written for version 1
and are judged by version 1's gate script, by version 4's and by version 5's; those under
`cases/v4/` by version 4's and by version 5's.

Version 5's entry reads the PR from GitHub, not from the event: its entry tests run the
script against a recorded `gh` that answers the PR read and takes the check run.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from itertools import permutations
from unittest import mock

import materialized
import parsers
import support
from govlib import render
from standins import environment

gate = parsers.gate
gate_v4 = parsers.load_gate(4)
gate_v5 = parsers.load_gate(5)
FIXTURES = os.path.join(support.FIXTURES, "gate")
CASES = os.path.join(FIXTURES, "cases")
V4_CASES = os.path.join(CASES, "v4")
V5_CASES = os.path.join(CASES, "v5")
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


def lookup(answer):
    """Version 5's `merged` seam: "found" is True for any commit, "none" False, "unreadable" None."""
    return {"found": lambda sha: True, "none": lambda sha: False, "unreadable": lambda sha: None}[answer]


def merged_pull(sha, branch="main"):
    return {"merged_at": "2026-11-01T00:00:00Z", "base": {"ref": branch}, "merge_commit_sha": sha}


def build(root, case):
    """The case's repository: (repo, the default branch's head, the PR's head, SHAs by commit name)."""
    repo = support.init_repo(tempfile.mkdtemp(prefix="repo-", dir=root))
    base = load(os.path.join(FIXTURES, "base.json"))["files"]
    record = {RECORD: support.read_text(os.path.join(FIXTURES, "record.yml"))}
    files = dict(base) if case.get("record_in") else dict(base, **record)
    shas = {"base": apply(repo, files, "base")}
    for commit in case["default"]:
        changes = dict(commit["files"], **record) if commit["name"] == case.get("record_in") else commit["files"]
        shas[commit["name"]] = apply(repo, changes, commit["name"])
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

    def judge(self, name, script=gate, cases=CASES):
        case = load(os.path.join(cases, name + ".json"))
        repo, default_head, head, shas = build(self.tmp, case)
        args = (repo, case["author"], case["owner"], body_of(case, shas), default_head, head)
        if script is gate_v5:
            # Version 5 also takes GitHub's word on whether a commit is a merged PR's squash commit.
            args += (lookup(case.get("merged", "found")),)
        return case, script.verdict(*args)

    def assert_verdict(self, result, expected):
        rules = [line.split(":", 1)[0] for line in result["failures"]]
        observed = {"passed": result["passed"], "rules": rules, "pure_revert": result["pure_revert"]}
        self.assertEqual(observed, expected, result["failures"])


class SeamOne(GateCase):
    """Filled below: one test per case file and gate script that judges it."""


def _add_case(name, label, script, cases):
    def test(self):
        case, result = self.judge(name, script, cases)
        self.assert_verdict(result, case["expected"])

    test.__doc__ = "gate case %s, judged by version %s" % (name, label[1:])
    setattr(SeamOne, "test_%s_%s" % (label, re.sub(r"[^A-Za-z0-9]+", "_", name)), test)


def _case_names(directory):
    return [name[: -len(".json")] for name in sorted(os.listdir(directory)) if name.endswith(".json")]


for _name in _case_names(CASES):
    _add_case(_name, "v1", gate, CASES)
    _add_case(_name, "v4", gate_v4, CASES)
    _add_case(_name, "v5", gate_v5, CASES)
for _name in _case_names(V4_CASES):
    _add_case(_name, "v4", gate_v4, V4_CASES)
    _add_case(_name, "v5", gate_v5, V4_CASES)
for _name in _case_names(V5_CASES):
    _add_case(_name, "v5", gate_v5, V5_CASES)


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

    def test_v5_reverts_requires_the_commit_objects_own_id(self):
        case = load(os.path.join(CASES, "risk-missing.json"))
        expected = load(os.path.join(FIXTURES, "reverts-object-identity.json"))["expected_rules"]
        repo, default_head, head, shas = build(self.tmp, case)
        root = shas["base"]
        support.git(repo, "tag", "-a", "root-tag", "-m", "Tag the root commit", root)
        objects = {
            "commit": root,
            "tree": support.git(repo, "rev-parse", root + "^{tree}").strip(),
            "tag": support.git(repo, "rev-parse", "refs/tags/root-tag").strip(),
        }
        for kind, sha in objects.items():
            with self.subTest(kind=kind):
                body = case["body"] + "Reverts: " + sha
                result = gate_v5.verdict(
                    repo, case["author"], case["owner"], body, default_head, head, lookup("found")
                )
                self.assertFalse(result["passed"])
                self.assertFalse(result["pure_revert"])
                self.assertEqual([line.split(":", 1)[0] for line in result["failures"]], expected[kind])
                if kind != "commit":
                    self.assertEqual(
                        result["failures"][1],
                        "Pure revert: `Reverts: %s` names no commit on the default branch. "
                        "Fix: name the squash commit or delete the line." % sha,
                    )

    def test_v5_valid_risk_confirms_the_squash_commit_and_rejects_its_annotated_tag(self):
        case = load(os.path.join(V5_CASES, "merged-pr-squash-commit-low.json"))
        fixture = load(os.path.join(FIXTURES, "reverts-object-identity.json"))["valid_risk"]
        repo, default_head, head, shas = build(self.tmp, case)
        squash = shas["sensitive"]
        support.git(repo, "tag", "-a", "reviewed", "-m", "Reviewed change", squash)
        tag = support.git(repo, "rev-parse", "refs/tags/reviewed").strip()
        for kind, target in (("commit", squash), ("tag", tag)):
            with self.subTest(kind=kind):
                result = gate_v5.verdict(
                    repo, case["author"], case["owner"], fixture["body"].format(target=target),
                    default_head, head, lambda sha: sha == squash,
                )
                self.assert_verdict(result, fixture["expected"][kind])

    def test_the_floor_line_names_the_floor_the_path_and_the_tier_to_declare(self):
        (line,) = self.failures("rename-out-of-sensitive-path")
        self.assertIn('"src/auth/token.ts"', line)
        self.assertNotIn('"src/token.ts"', line)
        self.assertIn("high floor", line)
        self.assertIn("`Risk: high — <reason>`", line)

    def test_version_4s_floor_line_says_a_named_commit_from_before_governance_wasnt_confirmed(self):
        for name in ("revert-before-governance-low", "revert-of-the-governing-commit"):
            case, result = self.judge(name, gate_v4, V4_CASES)
            (line,) = result["failures"]
            self.assertNotIn("\n", line)
            self.assertTrue(line.startswith("Floors: "), line)
            self.assertIn("isn't confirmed as a pure revert: its parent holds no %s, so the commit predates governance. Fix: " % RECORD, line)
            self.assertRegex(line, r"`Reverts: [0-9a-f]{40}` isn't confirmed")
        for name in ("revert-before-governance-at-floor", "revert-before-governance-plain-path"):
            self.assertEqual(self.judge(name, gate_v4, V4_CASES)[1]["failures"], [], name)
        _, result = self.judge("revert-with-resolved-conflict", gate_v4)
        self.assertNotIn("predates governance", result["failures"][0])

    def test_version_5s_floor_line_says_why_a_named_commit_wasnt_confirmed_as_a_merged_prs_squash_commit(self):
        notes = {
            "no-merged-pr-low": "GitHub shows no PR merged into the default branch whose squash commit it is.",
            "lookup-unreadable-low": "GitHub couldn't be read to confirm it is a merged PR's squash commit.",
        }
        for name, note in notes.items():
            _, result = self.judge(name, gate_v5, V5_CASES)
            (line,) = result["failures"]
            self.assertNotIn("\n", line)
            self.assertTrue(line.startswith("Floors: "), line)
            self.assertIn("isn't confirmed as a pure revert: %s Fix: " % note, line)
            self.assertRegex(line, r"`Reverts: [0-9a-f]{40}` isn't confirmed")
        for name in ("no-merged-pr-at-floor", "lookup-unreadable-at-floor", "merged-pr-squash-commit-low"):
            self.assertEqual(self.judge(name, gate_v5, V5_CASES)[1]["failures"], [], name)

    def test_a_lookup_that_raises_reads_as_unreadable_and_is_never_called_before_the_git_conditions_hold(self):
        case = load(os.path.join(V5_CASES, "merged-pr-squash-commit-low.json"))
        repo, default_head, head, shas = build(self.tmp, case)
        args = (repo, case["author"], case["owner"], body_of(case, shas), default_head, head)

        def raises(sha):
            raise OSError("no network")
        (line,) = gate_v5.verdict(*args, raises)["failures"]
        self.assertIn("GitHub couldn't be read to confirm", line)
        calls = []
        for name, cases in (("revert-with-extra-change", CASES), ("revert-before-governance-low", V4_CASES), ("low-on-plain-path", CASES)):
            other = load(os.path.join(cases, name + ".json"))
            repo, default_head, head, shas = build(self.tmp, other)
            gate_v5.verdict(repo, other["author"], other["owner"], body_of(other, shas), default_head, head, lambda sha: calls.append(sha))
        self.assertEqual(calls, [])

    def test_each_risk_line_problem_has_its_own_line(self):
        self.assertIn("no `Risk:` line", self.failures("risk-missing")[0])
        self.assertIn("more than one `Risk:` line", self.failures("risk-doubled")[0])
        self.assertIn("malformed", self.failures("risk-malformed")[0])

    def test_a_file_name_that_isnt_utf_8_is_floored_and_named_in_printable_utf_8(self):
        case = load(os.path.join(CASES, "low-on-plain-path.json"))
        repo, default_head, _, _ = build(self.tmp, case)
        # Built in git's index alone, since some file systems refuse a name that isn't UTF-8.
        blob = support.git(repo, "hash-object", "-w", "README.md").strip()
        subprocess.run(
            ["git", "-C", repo, "update-index", "-z", "--index-info"],
            input=b"100644 blob " + blob.encode("ascii") + b"\tsrc/auth/\xff\nname.ts\0",
            env=support.isolated_env(), check=True,
        )
        tree = support.git(repo, "write-tree").strip()
        head = support.git(repo, "commit-tree", tree, "-p", default_head, "-m", "odd name").strip()
        result = gate.verdict(repo, case["author"], case["owner"], case["body"], default_head, head)
        (line,) = result["failures"]
        self.assertTrue(line.startswith("Floors: "), line)
        self.assertIn('"src/auth/\\udcff\\nname.ts"', line)
        line.encode("utf-8")


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
        self.assertEqual(sorted(os.listdir(directory)), ["gate.py", "merge_watch.py", "owner.sh", "record.yml"])


class Entry(GateCase):
    """The script's entry, as the workflow runs it: the event, a fetch of the head, and the check run."""

    def checkout(self, case_name):
        """An origin holding the case, and a checkout of its default branch alone; (checkout, head, case)."""
        case = load(os.path.join(CASES, case_name + ".json"))
        origin, default_head, head, shas = build(self.tmp, case)
        support.git(origin, "config", "uploadpack.allowReachableSHA1InWant", "true")
        checkout = tempfile.mkdtemp(prefix="checkout-", dir=self.tmp)
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


class EntryVersionFive(GateCase):
    """Version 5's entry: the PR as GitHub shows it, read with `gh api repos/<repository>/pulls/<number>`."""

    checkout = Entry.checkout

    def setUp(self):
        super().setUp()
        rendered = self.path("rendered")
        confirmed = dict(materialized.tally_fixture()["confirmed"], review_bots=["codex"])
        render.render(parsers.TEMPLATES, rendered, "Habit130/tally", "main", confirmed,
                      version=5, allow_unreleased=True)
        self.script = os.path.join(rendered, SCRIPT)

    def run_entry(self, checkout, event_head, event_body, pull, post_head, conclusion, title, summary,
                  lookup_calls=(), default_branch="main"):
        """Run version 5's script; `pull` is GitHub's answer, or None when the read fails."""
        event = self.path("event.json")
        repository = {"owner": {"login": "Habit130"}}
        if default_branch is not None:
            repository["default_branch"] = default_branch
        with open(event, "w") as handle:
            json.dump(
                {
                    "pull_request": {"number": 7, "head": {"sha": event_head}, "user": {"login": "stale"}, "body": event_body},
                    "repository": repository,
                },
                handle,
            )
        payload = {
            "name": "governance-gate",
            "head_sha": post_head,
            "status": "completed",
            "conclusion": conclusion,
            "output": {"title": title, "summary": summary},
        }
        read = {"args": ["api", "repos/Habit130/tally/pulls/7"]}
        if pull is None:
            read.update({"stdout": "", "stderr": "HTTP 502", "exit": 1})
        else:
            read.update({"stdout": json.dumps(pull) + "\n", "exit": 0})
        recording = self.path("gh.json")
        with open(recording, "w") as handle:
            json.dump(
                {
                    "tool": "gh",
                    "calls": [
                        read,
                        *lookup_calls,
                        {
                            "args": ["api", "--method", "POST", "repos/Habit130/tally/check-runs", "--input", "-"],
                            "stdin": json.dumps(payload, sort_keys=True),
                            "stdout": "{}\n",
                            "exit": 0,
                        },
                    ],
                },
                handle,
            )
        scratch = tempfile.mkdtemp(prefix="scratch-", dir=self.tmp)
        env = environment.environment(scratch, gh_recording=recording, base=support.isolated_env())
        env.update({"GITHUB_EVENT_PATH": event, "GITHUB_REPOSITORY": "Habit130/tally"})
        result = subprocess.run(
            [sys.executable, self.script, "--post-check"],
            cwd=checkout,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return result, environment.read_log(scratch)

    def github(self, head, case, base="main"):
        return {"head": {"sha": head}, "body": case["body"], "user": {"login": case["author"]}, "base": {"ref": base}}

    def passes(self, name, title, conclusion="success", summary="Every gate rule passed.", returncode=0):
        checkout, head, case = self.checkout(name)
        result, calls = self.run_entry(checkout, head, "stale", self.github(head, case), head, conclusion, title, summary)
        self.assertEqual(result.returncode, returncode, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True, True])
        return result

    def test_a_pass_names_the_declared_tier_in_its_title(self):
        result = self.passes("high-on-high-floor", "Passed: declared high")
        self.assertIn("PASS every rule", result.stdout)

    def test_a_failure_with_a_valid_risk_line_names_the_count_and_the_declared_tier(self):
        _, line = Entry.failure_line(self, None)
        self.passes("rename-out-of-sensitive-path", "Failed: 1 rule, declared low", "failure", "- " + line, 1)

    def test_a_failure_without_a_valid_risk_line_says_so(self):
        _, result = self.judge("risk-missing", gate_v5)
        self.assertEqual(len(result["failures"]), 1)
        self.passes("risk-missing", "Failed: 1 rule, no valid Risk: line", "failure", "- " + result["failures"][0], 1)

    def test_a_whitespace_only_reason_posts_a_failed_risk_check(self):
        checkout, head, case = self.checkout("low-on-plain-path")
        pull = self.github(head, dict(case, body="Risk: low — \u00a0"))
        summary = ("- Risk line: The `Risk:` line is malformed. Fix: keep exactly one line "
                   "`Risk: <low|medium|high> — <reason>`, with an em dash and a reason.")
        result, calls = self.run_entry(checkout, head, case["body"], pull, head, "failure",
                                       "Failed: 1 rule, no valid Risk: line", summary)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True, True])

    def test_a_failing_event_body_is_not_judged_when_githubs_current_body_passes(self):
        checkout, head, case = self.checkout("high-on-high-floor")
        result, calls = self.run_entry(
            checkout, head, "Risk: low \u2014 stale", self.github(head, case), head, "success", "Passed: declared high",
            "Every gate rule passed.",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True, True])

    def test_a_passing_event_body_is_not_judged_when_githubs_current_body_fails(self):
        _, expected = self.judge("low-on-medium-floor", gate_v5)
        checkout, head, case = self.checkout("low-on-medium-floor")
        result, calls = self.run_entry(
            checkout, head, "Risk: medium \u2014 stale", self.github(head, case), head, "failure",
            "Failed: 1 rule, declared low", "- " + expected["failures"][0],
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True, True])

    def test_a_newer_github_head_is_fetched_judged_and_given_the_check_run(self):
        checkout, old_head, case = self.checkout("high-on-high-floor")
        origin = support.git(checkout, "remote", "get-url", "origin").strip()
        support.git(origin, "checkout", "-q", "pr")
        new_head = apply(origin, {"docs/newer.md": "newer\n"}, "newer")
        support.git(origin, "checkout", "-q", "main")
        result, calls = self.run_entry(
            checkout, old_head, case["body"], self.github(new_head, case), new_head, "success", "Passed: declared high",
            "Every gate rule passed.",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True, True])
        self.assertIn("governance-gate on %s, judged by the default branch at " % new_head, result.stdout)
        self.assertNotIn(old_head, result.stdout)

    def test_an_unreadable_pr_fails_with_one_line_and_posts_on_the_events_head(self):
        checkout, head, case = self.checkout("high-on-high-floor")
        line = "GitHub: the PR #7 couldn't be read from GitHub. Fix: rerun the gate."
        result, calls = self.run_entry(
            checkout, head, case["body"], None, head, "failure", "Failed: 1 rule, the PR couldn't be read", "- " + line
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True, True])
        self.assertEqual(
            result.stdout.splitlines()[:2],
            ["governance-gate on %s, judged by the default branch at %s" % (head, support.git(checkout, "rev-parse", "HEAD").strip()), "FAIL " + line],
        )

    def revert_entry(self, merged_calls, note, returncode, base="main", default_branch="main", tier="low"):
        """Run a pure revert's entry; merged_calls are the lookup's recorded gh calls (none for no lookup).

        The event names `main` as the repository's default branch; base is the PR's target as GitHub shows it.
        """
        checkout, head, case = self.checkout("pure-revert-low-on-sensitive-path")
        sha = re.search(r"Reverts: ([0-9a-f]{40})", case["body"]).group(1)
        case["body"] = case["body"].replace("Risk: low", "Risk: " + tier)
        pull = self.github(head, case, base)
        if note is None:
            title, conclusion, summary = "Passed: a pure revert, declared " + tier, "success", "Every gate rule passed."
        elif returncode == 0:
            title, conclusion = "Passed: declared " + tier, "success"
            summary = "Every gate rule passed.\n`Reverts: %s` isn't confirmed as a pure revert: %s" % (sha, note)
        else:
            title, conclusion = "Failed: 1 rule, declared low", "failure"
            summary = (
                '- Floors: the PR declares low, and these changed paths have a high floor: "src/auth/login.ts". '
                "`Reverts: %s` isn't confirmed as a pure revert: %s "
                "Fix: declare `Risk: high \u2014 <reason>`; no tier goes below a floor." % (sha, note)
            )
        args = ["api", "repos/Habit130/tally/commits/%s/pulls?per_page=100" % sha]
        lookup_calls = [dict(call, args=args) for call in merged_calls(sha)]
        event_head = support.git(checkout, "rev-parse", "HEAD").strip()
        result, calls = self.run_entry(checkout, event_head, "stale", pull, head, conclusion, title, summary,
                                       lookup_calls, default_branch)
        self.assertEqual(result.returncode, returncode, result.stdout + result.stderr)
        self.assertEqual([call["recorded"] for call in calls], [True] * (2 + len(lookup_calls)), result.stdout)
        return result

    def test_a_pr_without_a_reverts_line_makes_no_lookup_call(self):
        # passes() records only the PR read and the POST, so a third gh call would fail the run.
        self.passes("high-on-high-floor", "Passed: declared high")

    def test_only_a_regular_historical_record_confirms_a_governed_revert(self):
        record = support.read_text(os.path.join(FIXTURES, "record.yml"))
        path = "src/auth/notes.txt"
        histories = {
            "regular": {RECORD: record},
            "executable": {RECORD: {"content": record, "mode": "100755"}},
            "missing": {},
            "directory": {RECORD + "/notes": "notes\n"},
            "symlink": {"policy.yml": record},
        }
        for kind, files in histories.items():
            with self.subTest(kind=kind):
                repo = support.init_repo(tempfile.mkdtemp(dir=self.tmp))
                if kind == "symlink":
                    os.makedirs(os.path.join(repo, os.path.dirname(RECORD)))
                    os.symlink("../../policy.yml", os.path.join(repo, RECORD))
                apply(repo, {**files, path: "before\n"}, "historical policy")
                original = apply(repo, {path: "after\n"}, "original change")
                base = support.commit_tree(repo, {RECORD: record, path: "after\n"}, "current policy")
                support.git(repo, "checkout", "-q", "-b", "pr")
                head = apply(repo, {path: "before\n"}, "restore notes")
                support.git(repo, "checkout", "-q", "main")
                body = "Risk: high — restore the reviewed notes\nReverts: " + original
                pull = self.github(head, {"body": body, "author": "Habit098"})
                lookup_calls = []
                summary = "Every gate rule passed."
                if kind in ("regular", "executable"):
                    lookup_calls.append({"args": ["api", "repos/Habit130/tally/commits/%s/pulls?per_page=100" % original],
                                         "stdout": json.dumps([merged_pull(original)]), "exit": 0})
                    title = "Passed: a pure revert, declared high"
                else:
                    title = "Passed: declared high"
                    summary += ("\n`Reverts: %s` isn't confirmed as a pure revert: "
                                "its parent has no regular file at %s." % (original, RECORD))
                result, calls = self.run_entry(repo, base, "", pull, head, "success", title, summary, lookup_calls)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual([call["recorded"] for call in calls], [True] * (2 + len(lookup_calls)))

    def test_a_pure_revert_whose_lookup_finds_the_merged_pr_passes_as_one_and_titles_the_declared_tier(self):
        def found(sha):
            pulls = [merged_pull(sha)]
            return [{"stdout": json.dumps(pulls) + "\n", "exit": 0}]
        result = self.revert_entry(found, None, 0)
        self.assertIn("PASS a pure revert", result.stdout)

    def test_a_lookup_read_failure_leaves_the_revert_unconfirmed(self):
        def unread(sha):
            return [{"stdout": "", "stderr": "HTTP 502", "exit": 1}]
        note = "GitHub couldn't be read to confirm it is a merged PR's squash commit."
        self.assertIn(note, self.revert_entry(unread, note, 1).stdout)

    def test_incomplete_provenance_is_reported_at_and_below_the_floor(self):
        note = "GitHub couldn't be read to confirm it is a merged PR's squash commit."
        for tier, returncode in (("high", 0), ("low", 1)):
            with self.subTest(tier=tier):
                self.revert_entry(lambda sha: [{"stdout": "[{}]", "exit": 0}], note, returncode, tier=tier)

    def test_a_lookup_listing_no_matching_merged_pr_leaves_the_revert_unconfirmed(self):
        def other(sha):
            pulls = [{"merged_at": None, "base": {"ref": "main"}, "merge_commit_sha": sha},
                     merged_pull(sha, "other"), merged_pull("0" * 40)]
            return [{"stdout": json.dumps(pulls) + "\n", "exit": 0}]
        note = "GitHub shows no PR merged into the default branch whose squash commit it is."
        self.assertIn(note, self.revert_entry(other, note, 1).stdout)
        self.assertIn(note, self.revert_entry(other, note, 0, tier="high").stdout)

    def test_a_definite_match_survives_an_unreadable_association(self):
        def found(sha):
            return [{"stdout": json.dumps([None, merged_pull(sha)]), "exit": 0}]
        self.revert_entry(found, None, 0)

    def test_malformed_merge_fields_cannot_confirm_a_match_or_an_absence(self):
        note = "GitHub couldn't be read to confirm it is a merged PR's squash commit."
        for invalid in ({"merged_at": "unknown"}, {"base": {}}, {"merge_commit_sha": None}):
            with self.subTest(invalid=invalid):
                def response(sha):
                    return [{"stdout": json.dumps([{**merged_pull(sha), **invalid}]), "exit": 0}]
                self.revert_entry(response, note, 0, tier="high")

    def test_a_full_page_without_a_match_leaves_provenance_indeterminate(self):
        note = "GitHub couldn't be read to confirm it is a merged PR's squash commit."
        page = json.dumps([{"merged_at": None}] * 100)
        self.revert_entry(lambda sha: [{"stdout": page, "exit": 0}], note, 0, tier="high")

    def test_a_retargeted_pr_is_still_confirmed_against_the_default_branch_that_judges_it(self):
        # GitHub now shows the PR's target as `release`; the default branch whose checkout judges is `main`.
        def found(sha):
            pulls = [merged_pull(sha)]
            return [{"stdout": json.dumps(pulls) + "\n", "exit": 0}]
        result = self.revert_entry(found, None, 0, base="release")
        self.assertIn("PASS a pure revert", result.stdout)

    def test_a_merged_pr_into_the_prs_new_target_doesnt_confirm_it(self):
        def other(sha):
            pulls = [merged_pull(sha, "release")]
            return [{"stdout": json.dumps(pulls) + "\n", "exit": 0}]
        note = "GitHub shows no PR merged into the default branch whose squash commit it is."
        self.assertIn(note, self.revert_entry(other, note, 1, base="release").stdout)

    def test_an_event_without_the_default_branch_confirms_nothing_and_makes_no_lookup_call(self):
        note = "GitHub couldn't be read to confirm it is a merged PR's squash commit."
        self.assertIn(note, self.revert_entry(lambda sha: [], note, 1, default_branch=None).stdout)

    def test_the_workflow_is_version_fours_byte_for_byte(self):
        path = ("templates", "dot-github", "workflows", "governance-gate.yml")
        with open(os.path.join(support.REAL_STORE, "5", *path), "rb") as five, open(os.path.join(support.REAL_STORE, "4", *path), "rb") as four:
            self.assertEqual(five.read(), four.read())


class RiskReasonConsumer(unittest.TestCase):
    def test_merge_watch_judges_a_whitespace_only_risk_reason_at_high(self):
        from merge_watch_history import load_v4_case_for_v5
        from test_merge_watch import watch_v5

        case = load_v4_case_for_v5("high-missing-all.json")
        event, github = case["event"], case["github"]
        repository = event["repository"]["full_name"]
        pull, = github["repos/%s/commits/%s/pulls" % (repository, event["after"])]
        pull["body"] = "Risk: low — \u00a0"
        problems = []
        record, = watch_v5.decide(case["event_name"], event, "Habit098", github.__getitem__, problems=problems)
        self.assertEqual(problems, [])
        self.assertIn("Category: missing-review", record["body"].splitlines())
        self.assertIn("declared no readable tier (its `Risk:` line is malformed), judged at high", record["body"])
        self.assertIn("reviewer", record["body"])
        self.assertIn("lacks: bot-1, reviewer, merge-summary.", record["body"])


class GeneratedGateStates(GateCase):
    """Exercise each stored grammar from v5 against the policy's independent examples."""

    def scripts(self):
        for version in parsers.TEMPLATES.versions():
            if version >= 5:
                yield version, parsers.load_gate(version)

    def test_risk_declaration_at_each_tier(self):
        reasons = {"low": "copy edit", "medium": "CLI behavior", "high": "发布"}
        for version, script in self.scripts():
            for tier in script.TIERS:
                with self.subTest(version=version, tier=tier):
                    self.assertIn(tier, reasons, "no evidence example for risk tier " + tier)
                    reason = reasons[tier]
                    line = f"Risk: {tier} — {reason}"
                    self.assertEqual(script.parse_body(line)["risk"], {"tier": tier, "reason": reason})
                    self.assertEqual(script.parse_body(line.replace(reason, ""))["risk"], "malformed")

    def test_body_syntax_and_author(self):
        case = load(os.path.join(CASES, "low-on-plain-path.json"))
        repo, base, head, _ = build(self.tmp, case)
        for version, script in self.scripts():
            for tier in script.TIERS:
                line = f"Risk: {tier} — 改动"
                with self.subTest(version=version, tier=tier):
                    self.assertIsNotNone(script._RISK.fullmatch(line))
                    for body, state in (
                        (line, {"tier": tier, "reason": "改动"}),
                        ("Details\r\n" + line + "\r\n", {"tier": tier, "reason": "改动"}),
                        (" " + line, "missing"), ("", "missing"),
                        (line + "\n" + line, "more than one"),
                        (line.replace("—", "-"), "malformed"),
                        (line.replace("改动", "\u2003"), "malformed"),
                    ):
                        with self.subTest(body=body):
                            self.assertEqual(script.parse_body(body), {"risk": state, "reverts": None})
                            result = script.verdict(repo, case["author"], case["owner"], body, base, head, lookup("none"))
                            valid = isinstance(state, dict)
                            self.assert_verdict(result, {"passed": valid, "rules": [] if valid else ["Risk line"],
                                                         "pure_revert": False})
                    for author, expected in ((case["owner"].swapcase(), []), (case["author"].swapcase(), []),
                                             ("outside-account", ["Author"])):
                        result = script.verdict(repo, author, case["owner"], line, base, head, lookup("none"))
                        self.assert_verdict(result, {"passed": not expected, "rules": expected, "pure_revert": False})

    def test_reverts_object_and_provenance_at_each_tier(self):
        case = load(os.path.join(V5_CASES, "merged-pr-squash-commit-low.json"))
        repo, base, head, shas = build(self.tmp, case)
        squash = shas["sensitive"]
        support.git(repo, "tag", "-a", "reviewed", "-m", "Reviewed change", squash)
        tag = support.git(repo, "rev-parse", "refs/tags/reviewed").strip()
        tree = support.git(repo, "rev-parse", squash + "^{tree}").strip()
        for version, script in self.scripts():
            for tier in script.TIERS:
                risk = f"Risk: {tier} — restore the reviewed change\n"
                floors = [] if tier == "high" else ["Floors"]
                line = "Reverts: " + squash
                self.assertIsNotNone(script._REVERTS.fullmatch(line))
                for declaration, provenance, pure, failures in (
                    (line, "found", True, []), (line, "none", False, floors),
                    (line, "unreadable", False, floors), ("", "found", False, floors),
                    *(("Reverts: " + oid, "found", False, ["Pure revert"] + floors)
                      for oid in (tree, tag, "0" * 40, head, squash[:7])),
                    (line + "\n" + line, "found", False, ["Pure revert"] + floors),
                ):
                    with self.subTest(version=version, tier=tier, declaration=declaration, provenance=provenance):
                        result = script.verdict(repo, case["author"], case["owner"], risk + declaration,
                                                base, head, lookup(provenance))
                        self.assert_verdict(result, {"passed": not failures, "rules": failures, "pure_revert": pure})

    def test_record_key_evidence_from_its_grammar(self):
        # Use complete, independently specified values so a newly admitted key needs its own example.
        for version, script in self.scripts():
            top = {"version": f"version: {version}", "agent_account": "agent_account: FixtureAgent",
                   "sensitive_paths": 'sensitive_paths:\n  - pattern: "src/**"\n    floor: high',
                   "confirmed": "confirmed:\n  sensitive_paths:\n  required_checks:\n  review_bots:"}
            confirmed = {"sensitive_paths": "  sensitive_paths:", "required_checks": "  required_checks:",
                         "review_bots": "  review_bots:"}
            path = {"pattern": '  - pattern: "src/**"', "floor": "    floor: high"}
            record = "\n".join(top.values()) + "\n"
            with self.subTest(version=version):
                self.assertEqual(script.parse_record(record.encode()), {
                    "version": version, "agent_account": "FixtureAgent",
                    "sensitive_paths": [{"pattern": "src/**", "floor": "high"}],
                    "confirmed": {"sensitive_paths": [], "required_checks": [], "review_bots": []},
                })
                for keys, examples in ((script.RECORD_KEYS, top), (script.CONFIRMED_KEYS, confirmed),
                                       (script.CONFIRMED_KEYS_V3, confirmed), (script.PATH_KEYS, path)):
                    for key in keys:
                        with self.subTest(keys=keys, key=key):
                            self.assertIn(key, examples)
                            field = examples[key]
                            # Match complete lines (two levels both contain sensitive_paths).
                            needle = "\n" + field + "\n"
                            padded = "\n" + record
                            self.assertEqual(padded.count(needle), 1)
                            for replacement in (field + "\n" + field, field.replace(key + ":", "unknown:", 1)):
                                with self.assertRaises(script.RecordError):
                                    script.parse_record(padded.replace(needle, "\n" + replacement + "\n").encode())
                            omitted = padded.replace(needle, "\n").encode()
                            if key == "review_bots":
                                self.assertNotIn(key, script.parse_record(omitted)["confirmed"])
                            else:
                                with self.assertRaises(script.RecordError):
                                    script.parse_record(omitted)

                for original, invalid in (
                    (f"version: {version}", 'version: "5"'), (f"version: {version}", "version: 0"),
                    ("agent_account: FixtureAgent", 'agent_account: ""'),
                    ('pattern: "src/**"', 'pattern: ""'), ("floor: high", "floor: low"),
                    ("  required_checks:", "  required_checks: scalar"),
                    ("  review_bots:", "  review_bots: no"),
                    (top["version"] + "\n" + top["agent_account"], top["agent_account"] + "\n" + top["version"]),
                    (confirmed["required_checks"] + "\n" + confirmed["review_bots"],
                     confirmed["review_bots"] + "\n" + confirmed["required_checks"]),
                ):
                    with self.subTest(invalid=invalid), self.assertRaises(script.RecordError):
                        script.parse_record(record.replace(original, invalid).encode())

    def test_enabled_lists_and_floors(self):
        floor_paths = {"medium": "src/billing/invoice.ts", "high": "src/auth/login.ts"}
        for version, script in self.scripts():
            record = f"version: {version}\nagent_account: FixtureAgent\nsensitive_paths:\nconfirmed:\n"
            record += "  sensitive_paths:\n  required_checks:\n  review_bots:\n"
            for count in range(len(script.REVIEW_BOTS) + 1):
                for order in permutations(script.REVIEW_BOTS, count):
                    with self.subTest(version=version, order=order):
                        value = record + "".join('    - "' + bot + '"\n' for bot in order)
                        self.assertEqual(script.parse_record(value.encode())["confirmed"]["review_bots"], list(order))
                        for extra in ("unknown", *order):
                            with self.assertRaises(script.RecordError):
                                script.parse_record((value + '    - "' + extra + '"\n').encode())
            for floor in script.FLOORS:
                with self.subTest(version=version, floor=floor):
                    self.assertIn(floor, floor_paths)
                    case = load(os.path.join(CASES, "low-on-plain-path.json"))
                    case["head"][0]["files"] = {floor_paths[floor]: "changed text"}
                    repo, base, head, _ = build(self.tmp, case)
                    enough = {"medium": {"medium", "high"}, "high": {"high"}}[floor]
                    for tier in script.TIERS:
                        with self.subTest(tier=tier):
                            body = f"Risk: {tier} — edit a sensitive file"
                            result = script.verdict(repo, case["author"], case["owner"], body, base, head, lookup("none"))
                            self.assert_verdict(result, {"passed": tier in enough, "pure_revert": False,
                                                         "rules": [] if tier in enough else ["Floors"]})

    def test_revert_history_at_each_tier(self):
        histories = (
            (CASES, "pure-revert-of-older-commit", True),
            (CASES, "revert-with-resolved-conflict", False),
            (CASES, "revert-with-extra-change", False),
            (V4_CASES, "revert-before-governance-low", False),
            (V4_CASES, "revert-of-the-governing-commit", False),
        )
        for directory, name, qualifies in histories:
            case = load(os.path.join(directory, name + ".json"))
            repo, base, head, shas = build(self.tmp, case)
            declaration = body_of(case, shas).split("Reverts: ")[1].strip()
            for version, script in self.scripts():
                for tier in script.TIERS:
                    with self.subTest(version=version, tier=tier, history=name):
                        body = f"Risk: {tier} — reviewed change\nReverts: {declaration}"
                        result = script.verdict(repo, case["author"], case["owner"], body, base, head, lookup("found"))
                        at_floor = tier == "high" or (tier == "medium" and name == "revert-of-the-governing-commit")
                        rules = [] if qualifies or at_floor else ["Floors"]
                        self.assert_verdict(result, {"passed": not rules, "rules": rules, "pure_revert": qualifies})

    def test_floor_uses_both_sides_of_changes_and_highest_match(self):
        cases = {
            "add": {"src/auth/new": "text"},
            "delete": {"src/auth/token.ts": None},
            "rename from": {"src/auth/token.ts": None, "src/token.ts": "token\n"},
            "rename to": {"docs/guide.md": None, "src/auth/guide.md": "guide\n"},
            "overlap": {"src/auth/AGENTS.md": "updated"},
            "case sensitive": {"src/BILLING/new": "text"},
            "root relative": {"other/src/auth/new": "text"},
        }
        for label, files in cases.items():
            case = load(os.path.join(CASES, "low-on-plain-path.json"))
            case["head"][0]["files"] = files
            repo, base, head, _ = build(self.tmp, case)
            for version, script in self.scripts():
                for tier in script.TIERS:
                    with self.subTest(version=version, tier=tier, change=label):
                        body = f"Risk: {tier} — change a path"
                        result = script.verdict(repo, case["author"], case["owner"], body, base, head, lookup("none"))
                        rules = [] if tier == "high" or label in ("case sensitive", "root relative") else ["Floors"]
                        self.assert_verdict(result, {"passed": not rules, "rules": rules, "pure_revert": False})


if __name__ == "__main__":
    unittest.main()
