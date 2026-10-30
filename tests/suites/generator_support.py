"""Seam A's inputs (#44 Testing Decisions): a fixture repository, a stand-in GitHub, a machine home and a store.

A case under `tests/fixtures/generator/cases/` is one JSON file:

- `harness`: `claude-code`, `opencode`, `codex`, `dsh`, `claude-code+codex`, `claude-code+opencode`
  or `none`: which harness variables the run's environment holds. Every other harness variable
  is removed first, so the case reads the same in any session and in CI. `extra_env` adds
  variables on top, `{home}` standing for the fixture home.
- `store`: `released` (versions 1 to 3, all released, built from version 1's real templates
  with a line added to `docs/agents/review.md` at each later version), `unreleased` (version 1
  without its change note) or `missing-skill` (`released`, relying on one more skill than the
  machine has). Each relies on the fixture home's synthetic machine skills.
- `home`: `ready`, an installed machine whose check passes, or `failing`, the same with
  `~/.claude/CLAUDE.md`'s link removed.
- `repository`: the tally sample at its first commit, then:
  - `name`: the owner/name `origin` names (default `Habit130/tally`);
  - `empty`: a checkout with no commit;
  - `governed_at`: a version rendered into it with tally's confirmed values, for the branch
    `rendered_branch` (default `main`);
  - `files`: `{path: text or null}` written or removed after that, where `<planted:TYPE>`
    becomes a credential shape built here at test time, so no committed file holds one;
  - `edits`: `[{"path", "replace": [old, new]}]` or `[{"path", "mode"}]`, applied after that;
  - `checkout_branch`: the branch `origin/HEAD` names in the checkout (default `main`).
- `github`: the agent account's view: `owner`, `private`, `default_branch`, `permissions`,
  `invitations`, `empty`, `settings`, `labels`, `pulls`, `classic_protection`,
  `rulesets_forbidden`, `failing_rulesets` (ids whose own read fails), and `rulesets`: `target` (the three as #41 §7 has them, for the
  record's checks) or a list of `{"as_target": name, "changes": {...}}` and full bodies with
  an `id`. GitHub returns `bypass_actors` as null to the agent, as it did on 2026-10-29.
- `run`: the subcommands run, in order (default `preconditions`, `mode`, `inspect`).
- `expect`: per subcommand, `exit` and a subset of the JSON it prints; for `preconditions`,
  `items` maps every item to its status and `checklist` lists the steps.
"""

import atexit
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

import machine_support as ms
import materialized
import owner_support as ow
import support
from standins import environment
from target_state import TARGET_SETTINGS, target_ruleset

CASES = os.path.join(support.FIXTURES, "generator", "cases")
TALLY_CONFIRMED = materialized.tally_fixture()["confirmed"]
RELIED_ON = [name for name in ms.MACHINE_NAMES if name != "govern-repository"]
# Each harness's own variables, as its shell's probe named them (`harness-probes.json`); the
# values are the fixture's own, since the probes recorded names only.
HARNESS_VARIABLES = {
    "claude-code": {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli", "CLAUDE_CODE_SESSION_ID": "fixture", "AI_AGENT": "fixture"},
    "opencode": {"OPENCODE": "1", "OPENCODE_SESSION_ID": "fixture", "OPENCODE_TERMINAL": "1", "AGENT": "fixture", "AI_AGENT": "fixture"},
    "codex": {"CODEX_CI": "1", "CODEX_SANDBOX": "seatbelt", "CODEX_SESSION_ID": "fixture", "CODEX_SHELL": "1",
              "CODEX_THREAD_ID": "fixture", "CODEX_VERSION": "fixture"},
    "dsh": {"DSH_HOME": "/fixture/.dsh", "DSH_PROFILE": "desktop", "DSH_PROFILE_DIR": "/fixture/.dsh/profiles/desktop",
            "DSH_SESSION_ID": "fixture", "DSH_SHELL": "1"},
}
HARNESS_PREFIXES = ("CLAUDE", "OPENCODE", "CODEX_", "DSH_", "AI_AGENT", "AGENT")
RULESET_IDS = {"Gate": 7001, "Merge": 7002, "History": 7003}

# Credential shapes, assembled here so no committed file carries one GitHub's push protection
# would block. They match the inspection's shapes and are no one's credential.
PLANTED = {
    "github-token": "gh" + "p_" + "Z" * 36,
    "private-key": "-----BEGIN " + "RSA PRIVATE KEY-----",
}

_cache = {}


def _scratch_root():
    if "root" not in _cache:
        _cache["root"] = os.path.realpath(tempfile.mkdtemp(prefix="seam-a-"))
        atexit.register(shutil.rmtree, _cache["root"], True)
    return _cache["root"]


def load_case(name):
    with open(os.path.join(CASES, name + ".json")) as handle:
        return json.load(handle)


def case_names():
    return sorted(name[: -len(".json")] for name in os.listdir(CASES) if name.endswith(".json"))


# The store.


def _change_note(version):
    urgency = "urgent" if version == 2 else "when convenient"
    return "urgency: %s\nmust-act: no\n\n版本 %d 的变更说明（Seam A 的合成版本）。\n" % (urgency, version)


def build_store(kind):
    """A synthetic template store, built once per kind."""
    key = "store-" + kind
    if key in _cache:
        return _cache[key]
    root = os.path.join(_scratch_root(), key)
    real = os.path.join(support.REAL_STORE, "1")
    versions = (1,) if kind == "unreleased" else (1, 2, 3)
    for version in versions:
        target = os.path.join(root, str(version))
        shutil.copytree(real, target)
        with open(os.path.join(target, "manifest.json")) as handle:
            manifest = json.load(handle)
        manifest["version"] = version
        manifest["relied_on_skills"] = RELIED_ON + (["gamma-missing"] if kind == "missing-skill" else [])
        with open(os.path.join(target, "manifest.json"), "w") as handle:
            json.dump(manifest, handle, indent=2)
        review = os.path.join(target, "templates", "docs", "agents", "review.md")
        with open(review, "a") as handle:
            for later in range(2, version + 1):
                handle.write("\nVersion %d of Seam A's synthetic store adds this line.\n" % later)
        if kind != "unreleased":
            with open(os.path.join(target, "change-note.md"), "w") as handle:
                handle.write(_change_note(version))
    _cache[key] = root
    return root


# The machine home.


def build_home(kind):
    """An installed fixture home, built once per kind and never changed by a case."""
    key = "home-" + kind
    if key in _cache:
        return _cache[key]
    base = os.path.join(_scratch_root(), key)
    os.makedirs(base)
    source = os.path.join(base, "source")
    ms.build_source(source)
    home = ms.ready_home(os.path.join(base, "home"))
    env = ms.machine_env(home, os.path.join(base, "install-scratch"), gh_recording=ms.write_gh_recording(os.path.join(base, "gh.json")))
    code, out, err = ms.run_machine(["install", "--source", source, "--home", home], env)
    if code != 0:
        raise AssertionError("the fixture home's install failed: %s %s" % (out, err))
    if kind == "failing":
        os.remove(os.path.join(home, ".claude", "CLAUDE.md"))
    _cache[key] = home
    return home


# The repository.


def _plant(text):
    for name, value in PLANTED.items():
        text = text.replace("<planted:%s>" % name, value)
    return text


def build_repository(root, case, store):
    spec = case.get("repository", {})
    name = spec.get("name", "Habit130/tally")
    if spec.get("empty"):
        worktree = support.init_repo(os.path.join(root, "tally"))
        support.git(worktree, "remote", "add", "origin", "https://github.com/%s.git" % name)
        return worktree
    worktree = materialized.tally_worktree(root)
    support.git(worktree, "remote", "set-url", "origin", "https://github.com/%s.git" % name)
    if spec.get("governed_at"):
        confirmed = os.path.join(root, "confirmed.json")
        with open(confirmed, "w") as handle:
            json.dump(TALLY_CONFIRMED, handle)
        code, facts = support.govern(
            ["render", "--store", store, "--version", str(spec["governed_at"]), "--dest", worktree,
             "--repository", name, "--default-branch", spec.get("rendered_branch", "main"), "--confirmed", confirmed]
        )
        if code != 0:
            raise AssertionError("rendering the fixture failed: %s" % facts)
    for path, text in sorted(spec.get("files", {}).items()):
        full = os.path.join(worktree, *path.split("/"))
        if text is None:
            os.remove(full)
            continue
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(_plant(text))
    for edit in spec.get("edits", []):
        full = os.path.join(worktree, *edit["path"].split("/"))
        if "replace" in edit:
            text = support.read_text(full)
            old, new = edit["replace"]
            if text.count(old) != 1:
                raise AssertionError("edit %r doesn't match %s exactly once" % (old, edit["path"]))
            with open(full, "w") as handle:
                handle.write(text.replace(old, new))
        if "mode" in edit:
            os.chmod(full, 0o755 if edit["mode"] == "100755" else 0o644)
    support.git(worktree, "add", "-A")
    support.git(worktree, "commit", "-q", "--allow-empty", "-m", "the fixture's state")
    branch = spec.get("checkout_branch", "main")
    support.git(worktree, "update-ref", "refs/remotes/origin/%s" % branch, "HEAD")
    support.git(worktree, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/%s" % branch)
    return worktree


# The stand-in GitHub.


def agent_view(body, ruleset_id, repository):
    """A ruleset as GET /rulesets/{id} returns it to the agent account: no bypass actors."""
    shown = ow.as_github(body, ruleset_id)
    shown["source"] = repository
    shown["bypass_actors"] = None
    shown["current_user_can_bypass"] = "never"
    return shown


def _rulesets(github, checks):
    spec = github.get("rulesets", [])
    if spec == "target":
        spec = [{"as_target": name} for name in ("Gate", "Merge", "History")]
    found = []
    for entry in spec:
        if "as_target" in entry:
            body = target_ruleset(entry["as_target"], entry.get("checks", checks))
            body.update(copy.deepcopy(entry.get("changes", {})))
            found.append((RULESET_IDS[entry["as_target"]], body))
        else:
            body = copy.deepcopy(entry)
            found.append((body.pop("id"), body))
    return found


def _applies(body, branch):
    include = body.get("conditions", {}).get("ref_name", {}).get("include", [])
    exclude = body.get("conditions", {}).get("ref_name", {}).get("exclude", [])
    names = ("~ALL", "~DEFAULT_BRANCH", branch, "refs/heads/" + branch)
    return (
        body.get("target") == "branch"
        and body.get("enforcement") == "active"
        and any(p in names for p in include)
        and not any(p in names for p in exclude)
    )


def recording(case, path):
    """The stand-in GitHub for one case, in the shapes gh printed for the agent account on 2026-10-29."""
    github = case.get("github", {})
    spec = case.get("repository", {})
    name = spec.get("name", "Habit130/tally")
    owner_login, owner_type = github.get("owner", ["Habit130", "User"])
    branch = github.get("default_branch", "main")
    checks = github.get("checks", TALLY_CONFIRMED["required_checks"])
    repo = {
        "full_name": name,
        "name": name.split("/")[1],
        "owner": {"login": owner_login, "type": owner_type},
        "private": bool(github.get("private")),
        "visibility": "private" if github.get("private") else "public",
        "default_branch": branch,
        "permissions": github.get("permissions", {"admin": False, "maintain": False, "push": True, "triage": True, "pull": True}),
        "security_and_analysis": None,
    }
    repo.update(github.get("settings", TARGET_SETTINGS))

    def api(suffix):
        return ["api", "repos/%s%s" % (name, suffix)]

    calls = [
        ow.ok(["api", "user"], {"login": "Habit098", "id": ms.AGENT_ID}),
        ow.ok(api(""), repo),
        ow.ok(["api", "user/repository_invitations?per_page=100"], github.get("invitations", [])),
        ow.ok(api("/labels?per_page=100"), github.get("labels", [])),
        ow.ok(api("/pulls?state=open&per_page=100"), github.get("pulls", [])),
    ]
    branch_path = "/branches/%s" % quote(branch, safe="")
    if github.get("empty"):
        calls.append(ow.http_error(api(branch_path), 404, "Branch not found"))
        calls.append(ow.http_error(api("/rules/branches/%s" % quote(branch, safe="")), 404, "Branch not found"))
    else:
        calls.append(ow.ok(api(branch_path), {
            "name": branch,
            "protected": bool(github.get("rulesets") or github.get("classic_protection")),
            "protection": {"enabled": bool(github.get("classic_protection")),
                           "required_status_checks": {"enforcement_level": "off", "contexts": [], "checks": []}},
        }))
    rulesets = _rulesets(github, checks)
    if github.get("rulesets_forbidden"):
        calls.append(ow.http_error(api("/rulesets?includes_parents=false&per_page=100"), 403,
                                   "Upgrade to GitHub Pro or make this repository public to enable this feature."))
    else:
        shown = [agent_view(body, ruleset_id, name) for ruleset_id, body in rulesets]
        calls.append(ow.ok(api("/rulesets?includes_parents=false&per_page=100"), [ow.listed(r) for r in shown]))
        for ruleset in shown:
            if ruleset["id"] in github.get("failing_rulesets", []):
                calls.append(ow.http_error(api("/rulesets/%d" % ruleset["id"]), 404, "Not Found"))
            else:
                calls.append(ow.ok(api("/rulesets/%d" % ruleset["id"]), ruleset))
    if not github.get("empty"):
        rules = []
        for ruleset_id, body in rulesets:
            if _applies(body, branch) and not github.get("rulesets_forbidden"):
                rules.extend({"type": rule["type"], "ruleset_source_type": "Repository", "ruleset_source": name,
                              "ruleset_id": ruleset_id} for rule in body["rules"])
        calls.append(ow.ok(api("/rules/branches/%s" % quote(branch, safe="")), rules))
    for invitation in github.get("invitations", []):
        calls.append(ow.call(["api", "--method", "PATCH", "user/repository_invitations/%d" % invitation["id"]]))
    with open(path, "w") as handle:
        json.dump({"description": "Seam A's stand-in GitHub, written by generator_support.py.", "tool": "gh", "calls": calls}, handle)
    return path


# Running a case.


def case_env(case, home, scratch, gh_recording):
    env = ms.machine_env(home, scratch, gh_recording=gh_recording)
    for variable in list(env):
        if variable.startswith(HARNESS_PREFIXES):
            del env[variable]
    for harness in case.get("harness", "claude-code").split("+"):
        env.update(HARNESS_VARIABLES.get(harness, {}))
    env.update((key, value.replace("{home}", home)) for key, value in case.get("extra_env", {}).items())
    return env


def tree_snapshot(root):
    """Every path under root, .git included, with its kind, mode and content hash."""
    found = {}
    for base, dirs, names in os.walk(root):
        for name in dirs + names:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                found[rel] = ("link", os.readlink(full))
            elif os.path.isdir(full):
                found[rel] = ("dir",)
            else:
                with open(full, "rb") as handle:
                    found[rel] = ("file", oct(os.stat(full).st_mode & 0o777), hashlib.sha256(handle.read()).hexdigest())
    return found


def run_case(root, case):
    """Run a case's subcommands; return {command: (exit, facts)}, the stand-in log and the snapshots."""
    store = build_store(case.get("store", "released"))
    home = build_home(case.get("home", "ready"))
    worktree = build_repository(root, case, store)
    scratch = os.path.join(root, "scratch")
    os.makedirs(scratch)
    gh = recording(case, os.path.join(root, "gh.json"))
    env = case_env(case, home, scratch, gh)
    before = (tree_snapshot(worktree), ms.snapshot(home))
    results = {}
    for command in case.get("run", ["preconditions", "mode", "inspect"]):
        args = [command, "--worktree", worktree]
        if command in ("preconditions", "inspect"):
            args += ["--home", home]
        if command in ("preconditions", "mode"):
            args += ["--store", store]
        result = subprocess.run([sys.executable, support.GOVERN] + args, env=env, cwd=worktree,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        try:
            facts = json.loads(result.stdout)
        except ValueError:
            raise AssertionError("%s printed no JSON (exit %d): %s %s" % (command, result.returncode, result.stdout, result.stderr))
        results[command] = (result.returncode, facts, result.stdout, result.stderr)
    after = (tree_snapshot(worktree), ms.snapshot(home))
    return {"results": results, "log": environment.read_log(scratch), "before": before, "after": after,
            "scratch": scratch, "worktree": worktree}


def writes(log):
    """Every stand-in call that isn't a read: any gh call naming a method, a body or a field."""
    found = []
    for entry in log:
        args = entry["args"]
        if entry["tool"] != "gh" or args[:1] != ["api"] or any(
            a in ("--method", "-X", "--input", "-f", "-F", "--field", "--raw-field") for a in args
        ):
            found.append(args)
    return found


def subset(expected, actual, where="facts"):
    """Problems where actual departs from expected: dicts by expected's keys, lists item by item."""
    problems = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return ["%s is %r, not a mapping" % (where, actual)]
        for key, value in expected.items():
            if key not in actual:
                problems.append("%s has no %r" % (where, key))
            else:
                problems.extend(subset(value, actual[key], "%s.%s" % (where, key)))
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return ["%s is %r, not %d items like %r" % (where, actual, len(expected), expected)]
        for index, (want, have) in enumerate(zip(expected, actual)):
            problems.extend(subset(want, have, "%s[%d]" % (where, index)))
    elif expected != actual:
        problems.append("%s is %r, not %r" % (where, actual, expected))
    return problems
