"""Seam D's inputs (#44 §7, Testing Decisions): a stand-in GitHub per case, built against the target state.

The target state comes from `tests/target_state.py`, written from #41 §7 independently of the
owner script, so the recorded writes check the script against the spec rather than against
itself. The live check's probes compare the sandbox with the same target.

A case under `tests/fixtures/owner/cases/` names a starting GitHub state and the writes and
report lines it expects:

- `visibility`: `public` or `private`. `account`: the login `gh api user` answers.
- `checkout`: `head`, `behind` (GitHub's default branch has moved on) or `modified` (a
  tracked file is changed in the working tree).
- `required_checks`: the record's confirmed required checks.
- `start`: `nothing` (a new repository's defaults) or `target` (the target state, as GitHub
  returns it, for the record's checks), then `github` overrides parts of it:
  - `settings`, `security`, `workflow`, `actions` and `selected_actions` merge into those reads;
  - `rulesets` replaces the rulesets, each a body plus `id`, or `{"as_target": "<name>"}`
    for one of the three as the target state has it, optionally with `checks` and `changes`;
  - `classic_protection`: whether the default branch has classic branch protection;
  - `rulesets_forbidden`: GitHub refuses to list rulesets, as on a private repository without Pro;
  - `failing_reads`: maps a read, `actions/permissions/workflow`, to the HTTP status GitHub fails it with;
  - `event_policy`: `none`, `target`, `unreadable`, or policies that differ from the target
    by the fields given, each with an `id`.
- `writes`: every write in order, `[method, path under repos/<repository>/, body]`, where a
  body is JSON, `{"ruleset": "<name>"}` or `{"event_policy": "target"}` for the target body,
  or absent. A write answers as GitHub would, unless `answers` maps `"<method> <path>"` to
  the HTTP error GitHub gives instead.
- `exit`, and `report`: every `[status, subject]` the report prints, in order.
"""

import copy
import json
import os
import subprocess

import machine_support as ms
import materialized
import support
from target_state import EVENT_POLICY, TARGET_SECURITY, TARGET_SETTINGS, TARGET_WORKFLOW, target_ruleset

CASES = os.path.join(support.FIXTURES, "owner", "cases")
SCRIPT = ".github/governance/owner.sh"
OWNER = "Habit130"
REPOSITORY = "Habit130/tally"
BRANCH = "main"

# A new repository's GitHub defaults, the state `start: nothing` begins from.
NEW_REPOSITORY_SETTINGS = {
    "allow_squash_merge": True,
    "allow_merge_commit": True,
    "allow_rebase_merge": True,
    "delete_branch_on_merge": False,
    "allow_auto_merge": False,
}
NEW_SECURITY = {"secret_scanning": "disabled", "secret_scanning_push_protection": "disabled"}
ACTIONS_ENABLED = {"enabled": True, "allowed_actions": "all"}
TARGET_IDS = {"Gate": 9001, "Merge": 9002, "History": 9003}
NEW_IDS = {"Gate": 9101, "Merge": 9102, "History": 9103}


def body(serializable):
    """A request body exactly as the owner script sends it on stdin."""
    return json.dumps(serializable, sort_keys=True, separators=(",", ":"))


def as_github(ruleset, ruleset_id):
    """A ruleset as GET /rulesets/{id} returns it to the owner: GitHub's own fields and order.

    It adds fields and parameters the body never sends, reverses the rules, the checks and the
    condition keys, leaves out an unpinned check's integration_id and returns `update` bare,
    the way this repository's ruleset and GitHub's exported rulesets in github/docs read
    (2026-10-28).
    """
    rules = []
    for rule in reversed(ruleset.get("rules", [])):
        shown = {"type": rule["type"]}
        if "parameters" in rule and rule["type"] != "update":
            parameters = copy.deepcopy(rule["parameters"])
            if rule["type"] == "pull_request":
                parameters["required_reviewers"] = []
                parameters["require_extra_approval_for_unattributed_changes"] = True
                parameters["dismissal_restriction"] = {"enabled": False, "allowed_actors": []}
                parameters["ignore_approvals_from_contributors"] = False
            if rule["type"] == "required_status_checks":
                parameters["required_status_checks"] = list(reversed(parameters["required_status_checks"]))
            shown["parameters"] = parameters
        rules.append(shown)
    ref_name = ruleset.get("conditions", {}).get("ref_name", {})
    return {
        "id": ruleset_id,
        "name": ruleset["name"],
        "target": ruleset["target"],
        "source_type": "Repository",
        "source": REPOSITORY,
        "enforcement": ruleset["enforcement"],
        "conditions": {"ref_name": {"exclude": ref_name.get("exclude", []), "include": ref_name.get("include", [])}},
        "rules": rules,
        "bypass_actors": copy.deepcopy(ruleset.get("bypass_actors", [])),
        "node_id": "RRS_%d" % ruleset_id,
        "created_at": "2026-10-28T01:00:00.000-04:00",
        "updated_at": "2026-10-28T01:00:00.000-04:00",
        "current_user_can_bypass": "always",
        "_links": {"self": {"href": "https://api.github.com/repos/%s/rulesets/%d" % (REPOSITORY, ruleset_id)}},
    }


def listed(ruleset):
    """A ruleset as GET /rulesets lists it: no conditions, rules or bypass actors."""
    return dict((key, ruleset[key]) for key in ("id", "name", "target", "source_type", "source", "enforcement", "node_id"))


def call(args, stdout="", exit=0, stderr="", stdin=None):
    entry = {"args": args, "stdout": stdout, "stderr": stderr, "exit": exit}
    if stdin is not None:
        entry["stdin"] = stdin
    return entry


def ok(args, value, stdin=None):
    return call(args, json.dumps(value) + "\n", stdin=stdin)


def http_error(args, status, message, stdin=None):
    reason = {403: "Forbidden", 404: "Not Found", 422: "Unprocessable Entity"}.get(status, "Error")
    out = json.dumps({"message": message, "status": str(status)})
    return call(args, out, 1, "gh: %s (HTTP %d)\n" % (message or reason, status), stdin=stdin)


def api(path):
    return ["api", "repos/%s%s" % (REPOSITORY, path)]


def write_args(method, path):
    args = ["api", "--method", method, "repos/%s%s" % (REPOSITORY, path)]
    return args if method == "DELETE" else args + ["--input", "-"]


class State(object):
    """The stand-in GitHub's state for one case, before the owner script runs."""

    def __init__(self, case, head):
        self.case = case
        self.head = head
        start = case.get("start", "nothing")
        github = case.get("github", {})
        checks = case.get("required_checks", [])
        self.private = case["visibility"] == "private"
        self.account = case.get("account", OWNER)
        self.settings = dict(TARGET_SETTINGS if start == "target" else NEW_REPOSITORY_SETTINGS, **github.get("settings", {}))
        self.security = dict(TARGET_SECURITY if start == "target" else NEW_SECURITY, **github.get("security", {}))
        self.workflow = dict(TARGET_WORKFLOW, **github.get("workflow", {}))
        self.actions = dict(ACTIONS_ENABLED, **github.get("actions", {}))
        self.selected_actions = github.get("selected_actions")
        self.classic_protection = github.get("classic_protection", False)
        self.rulesets_forbidden = github.get("rulesets_forbidden", False)
        if "rulesets" in github:
            entries = github["rulesets"]
        elif start == "target":
            entries = [{"as_target": name} for name in ("Gate", "Merge", "History")]
        else:
            entries = []
        self.rulesets = [self._ruleset(entry, checks) for entry in entries]
        self.event_policy = github.get("event_policy", "target" if start == "target" else "none")

    def _ruleset(self, entry, checks):
        if "as_target" in entry:
            ruleset = target_ruleset(entry["as_target"], entry.get("checks", checks))
            ruleset.update(copy.deepcopy(entry.get("changes", {})))
            return as_github(ruleset, entry.get("id", TARGET_IDS[entry["as_target"]]))
        ruleset = copy.deepcopy(entry)
        return as_github(ruleset, ruleset.pop("id"))

    def repository(self):
        admin = self.account == OWNER
        repo = {
            "id": 77,
            "name": "tally",
            "full_name": REPOSITORY,
            "owner": {"login": OWNER, "type": "User"},
            "private": self.private,
            "visibility": "private" if self.private else "public",
            "default_branch": BRANCH,
            "permissions": {"admin": admin, "maintain": admin, "push": True, "triage": True, "pull": True},
        }
        repo.update(self.settings)
        if admin:
            repo["security_and_analysis"] = dict((key, {"status": value}) for key, value in self.security.items())
        return repo


def written_repository(state, patch):
    repo = state.repository()
    for key, value in patch.items():
        if key == "security_and_analysis":
            for name, setting in value.items():
                repo["security_and_analysis"][name] = setting
        else:
            repo[key] = value
    return repo


def recording(case, head, path):
    """Write the stand-in recording for a case whose checkout is at head; return its path."""
    state = State(case, head)
    default_head = head if case.get("checkout", "head") != "behind" else "f" * 40
    calls = [
        ok(["api", "user"], {"login": state.account, "id": 1 if state.account == OWNER else 2}),
        ok(api(""), state.repository()),
        ok(api("/branches/%s" % BRANCH), {"name": BRANCH, "commit": {"sha": default_head}, "protected": bool(state.rulesets)}),
        ok(api("/actions/permissions"), dict(state.actions, selected_actions_url="https://api.github.com/x")),
    ]
    failing = case.get("github", {}).get("failing_reads", {})
    if "actions/permissions/workflow" in failing:
        calls.append(http_error(api("/actions/permissions/workflow"), failing["actions/permissions/workflow"], "Server Error"))
    else:
        calls.append(ok(api("/actions/permissions/workflow"), state.workflow))
    if state.rulesets_forbidden:
        message = "Upgrade to GitHub Pro or make this repository public to enable this feature."
        calls.append(http_error(api("/rulesets?includes_parents=false&per_page=100"), 403, message))
    else:
        calls.append(ok(api("/rulesets?includes_parents=false&per_page=100"), [listed(ruleset) for ruleset in state.rulesets]))
    if state.selected_actions is not None:
        calls.append(ok(api("/actions/permissions/selected-actions"), state.selected_actions))
    for ruleset in state.rulesets:
        calls.append(ok(api("/rulesets/%d" % ruleset["id"]), ruleset))
    if state.classic_protection:
        calls.append(ok(api("/branches/%s/protection" % BRANCH), {"url": "https://api.github.com/x", "enforce_admins": {"enabled": False}}))
    else:
        calls.append(http_error(api("/branches/%s/protection" % BRANCH), 404, "Branch not protected"))
    calls += event_policy_calls(state)
    for write in case.get("writes", []):
        calls.append(write_call(state, case, write))
    with open(path, "w") as handle:
        json.dump({"description": "Seam D's stand-in GitHub, written by owner_support.py.", "tool": "gh", "calls": calls}, handle)
    return path


def resolve_body(case, spec):
    if isinstance(spec, dict) and set(spec) == {"ruleset"}:
        return target_ruleset(spec["ruleset"], case.get("required_checks", []))
    if spec == {"event_policy": "target"}:
        return EVENT_POLICY
    return spec


def write_call(state, case, write):
    method, path = write[0], write[1]
    sent = resolve_body(case, write[2]) if len(write) > 2 else None
    args = write_args(method, "/" + path if path else "")
    stdin = body(sent) if sent is not None else None
    answer = case.get("answers", {}).get("%s %s" % (method, path))
    if answer is not None:
        return http_error(args, answer["status"], answer["message"], stdin=stdin)
    if method == "DELETE":
        return call(args, "", stdin=stdin)
    if path == "rulesets" and method == "POST":
        return ok(args, as_github(sent, NEW_IDS[sent["name"]]), stdin=stdin)
    if path.startswith("rulesets/") and method == "PUT":
        return ok(args, as_github(sent, int(path.split("/")[1])), stdin=stdin)
    if path == "" and method == "PATCH":
        return ok(args, written_repository(state, sent), stdin=stdin)
    if path == "actions/permissions/workflow" and method == "PUT":
        return call(args, "", stdin=stdin)
    return event_policy_write(state, args, path, method, sent, stdin)


def policy_as_github(policy, policy_id):
    """An event policy as GET /actions/policies/{id} returns it: GitHub's own fields and order."""
    shown = {
        "id": policy_id,
        "name": policy["name"],
        "target": "actions",
        "source_type": "Repository",
        "source": REPOSITORY,
        "enforcement": policy["enforcement"],
        "rules": list(reversed(copy.deepcopy(policy.get("rules", [])))),
        "node_id": "AP_%d" % policy_id,
        "created_at": "2026-10-28T01:00:00Z",
        "updated_at": "2026-10-28T01:00:00Z",
    }
    workflow_path = (policy.get("conditions") or {}).get("workflow_path") or {"include": ["~ALL"], "exclude": []}
    shown["conditions"] = {"workflow_path": {"exclude": workflow_path.get("exclude", []), "include": workflow_path["include"]}}
    return shown


EVENT_POLICY_ID = 7001
NEW_EVENT_POLICY_ID = 7101


def event_policy_calls(state):
    """The event-policy reads. `event_policy` is `none`, `target`, `unreadable` or a list of policies with ids."""
    path = api("/actions/policies?has_parents=false&per_page=100")
    if state.private:
        return []
    if state.event_policy == "unreadable":
        return [http_error(path, 404, "Not Found")]
    if state.event_policy == "none":
        policies = []
    elif state.event_policy == "target":
        policies = [policy_as_github(EVENT_POLICY, EVENT_POLICY_ID)]
    else:
        policies = [policy_as_github(dict(EVENT_POLICY, **p), p["id"]) for p in copy.deepcopy(state.event_policy)]
    listed = {"total_count": len(policies), "policies": [dict((k, p[k]) for k in ("id", "name", "target", "source_type",
                                                                                   "source", "enforcement", "node_id"))
                                                          for p in policies]}
    return [ok(path, listed)] + [ok(api("/actions/policies/%d" % p["id"]), p) for p in policies]


def event_policy_write(state, args, path, method, sent, stdin):
    if path == "actions/policies" and method == "POST":
        return ok(args, policy_as_github(sent, NEW_EVENT_POLICY_ID), stdin=stdin)
    if path.startswith("actions/policies/") and method == "PUT":
        return ok(args, policy_as_github(sent, int(path.split("/")[2])), stdin=stdin)
    raise AssertionError("no stand-in answer for the write %s %s" % (method, path))


def load_case(name):
    with open(os.path.join(CASES, name + ".json"), encoding="utf-8") as handle:
        return json.load(handle)


def prepare(root, case):
    """A tally worktree with version 1 rendered for the case's record, committed; (worktree, head)."""
    fixture = materialized.tally_fixture()
    worktree = materialized.tally_worktree(root)
    confirmed = os.path.join(root, "confirmed.json")
    with open(confirmed, "w") as handle:
        json.dump({"sensitive_paths": fixture["confirmed"]["sensitive_paths"], "required_checks": case.get("required_checks", [])}, handle)
    code, facts = support.govern(
        ["render", "--store", support.REAL_STORE, "--version", "1", "--allow-unreleased", "--dest", worktree,
         "--repository", REPOSITORY, "--default-branch", BRANCH, "--confirmed", confirmed]
    )
    if code != 0:
        raise AssertionError("rendering version 1 failed: %s" % facts)
    support.git(worktree, "add", "-A")
    support.git(worktree, "commit", "-q", "-m", "Initialize governance")
    head = support.git(worktree, "rev-parse", "HEAD").strip()
    support.git(worktree, "update-ref", "refs/remotes/origin/%s" % BRANCH, head)
    if case.get("checkout") == "modified":
        with open(os.path.join(worktree, "README.md"), "a") as handle:
            handle.write("A local change.\n")
    return worktree, head


def owner_env(root, recording_path, extra=None):
    """Seam D's environment: a throwaway home, the stand-ins first, the ghm tripwire before them."""
    home = ms.make_home(os.path.join(root, "home"))
    scratch = os.path.join(root, "scratch")
    env = ms.machine_env(home, scratch, gh_recording=recording_path, extra=extra)
    return env, home, scratch


def run_owner(script, env, cwd=None):
    result = subprocess.run(
        ["/bin/bash", script], env=env, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, stdin=subprocess.DEVNULL,
    )
    return result.returncode, result.stdout, result.stderr


def report_lines(out):
    """[(status, subject)] for every item line the report printed."""
    return [(status, subject) for status, subject, _ in ms.lines(out)]


def writes(log):
    """[(method, path under the repository)] for every write the stand-in saw."""
    found = []
    for entry in log:
        args = entry["args"]
        if args[:2] == ["api", "--method"]:
            prefix = "repos/%s" % REPOSITORY
            path = args[3][len(prefix):].lstrip("/") if args[3].startswith(prefix) else args[3]
            found.append((args[2], path))
    return found
