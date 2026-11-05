#!/usr/bin/env python3
"""The live-check runner (#44 §11, §12): real GitHub, in the sandbox repositories only.

  sandbox-command  print habit's one line that creates both sandboxes and invites the agent account
  seed             as the agent: accept a sandbox's invitation, and seed its empty default branch
  prepare          steps 1 to 4: render this checkout's PR head into a fresh sandbox branch, open the
                   sandbox PR, and hand habit the pinned merge command, the owner-script command
                   and each probe's commands
  probe            step 5: run the named probes and post their results on this repository's PR
  reset            version 1's cut: open the sandbox PR that returns a sandbox to its seed, and hand
                   habit the pinned merge and the Gate ruleset's disabling
  end-to-end       version 1's cut: check the reset landed, build the head's generator as a
                   session-only plugin beside a fresh clone, and hand habit the line that starts
                   Claude Code there

Execution runs it as the agent account. habit runs only the printed steps: each command is one
line with Claude Code's `!` prefix, except `end-to-end`'s start line, which habit runs in a
terminal of their own, and `reset`'s step in the browser. Probes plug in under `tests/live/probes/` (that package's
docstring gives their shape). Nothing here deletes a sandbox, force-pushes or writes outside
the two sandboxes and this repository's PR; results carry probe output only, never a credential.
"""

import argparse
import collections
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(REPO, "generator", "govern-repository", "scripts")
for _path in (HERE, os.path.join(REPO, "tests"), SCRIPTS, os.path.join(REPO, "machine", "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import probes  # noqa: E402
from govlib import owner, storedform  # noqa: E402
from machinelib import AGENT, MAINTAINER, SANDBOXES  # noqa: E402

THIS_REPOSITORY = "Habit130/agent-repo-governance"
SEED = os.path.join(REPO, "tests", "fixtures", "repositories", "sandbox")
STORE = os.path.join(REPO, "generator", "govern-repository", "store")
GOVERN = os.path.join(SCRIPTS, "govern.py")
VERSION = 1
# Step 4 hands habit the owner-script command in every check; its report is this input.
OWNER_REPORT = "owner_report"


class RunnerError(Exception):
    """The runner stops; the message says why."""


def seed_fixture():
    with open(os.path.join(SEED, "fixture.json")) as handle:
        return json.load(handle)


def sandbox_name(visibility):
    name = seed_fixture()["repositories"][visibility]
    if name not in SANDBOXES:
        raise RunnerError("the seed names %s, which isn't one of machinelib's sandboxes" % name)
    return name


def run(args, cwd=None, stdin=None, check=True):
    result = subprocess.run(args, cwd=cwd, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    if check and result.returncode != 0:
        raise RunnerError("`%s` failed: %s" % (" ".join(args[:4]), " ".join(result.stderr.split())))
    return result


def gh_json(args):
    out = run(["gh"] + list(args)).stdout
    return json.loads(out) if out.strip() else None


# habit's command that creates the sandboxes.


def sandbox_command():
    """habit's one line: create each sandbox unless it exists, then invite the agent account.

    A personal repository has one collaborator level, which can push, so the invitation names
    no permission; GitHub reads `permission` only on organization-owned repositories. Each
    variable next to Chinese text is braced: macOS's bash 3.2 in a UTF-8 locale otherwise reads
    the next character's first byte into the name.
    """
    specs = " ".join("%s:%s" % (sandbox_name(v).split("/")[1], v) for v in ("public", "private"))
    return (
        "/bin/bash -c '" + owner.MAINTAINER_SHELL + "s=0; for spec in " + specs + "; do "
        "n=\"" + MAINTAINER + "/${spec%%:*}\"; v=\"${spec##*:}\"; "
        "if gh repo view \"$n\" --json nameWithOwner >/dev/null 2>&1; then echo \"已存在：${n}，未重新创建\"; "
        "elif gh repo create \"$n\" \"--$v\" --description \"Sandbox for agent-repo-governance live checks; not a governed repository.\" >/dev/null; "
        "then echo \"已创建：${n}（${v}）\"; else echo \"创建失败：${n}\"; s=1; continue; fi; "
        "if gh api --method PUT \"repos/$n/collaborators/" + AGENT + "\" >/dev/null; "
        "then echo \"已邀请：" + AGENT + " 以 write 权限加入 ${n}（已是协作者时无需再接受）\"; else echo \"邀请失败：${n}\"; s=1; fi; "
        "done; exit $s'"
    )


def cmd_sandbox_command(args):
    print(sandbox_command())
    return 0


# Seeding, as the agent account.


def accept_invitation(repository):
    invitations = gh_json(["api", "user/repository_invitations"]) or []
    for invitation in invitations:
        if (invitation.get("repository") or {}).get("full_name", "").lower() == repository.lower():
            run(["gh", "api", "--method", "PATCH", "user/repository_invitations/%s" % invitation["id"]])
            return "accepted the invitation to %s" % repository
    repo = run(["gh", "api", "repos/%s" % repository], check=False)
    if repo.returncode == 0 and (json.loads(repo.stdout).get("permissions") or {}).get("push"):
        return "already a write collaborator on %s" % repository
    raise RunnerError("%s has sent no invitation the agent account can see: habit runs `live.py sandbox-command`'s line first" % repository)


def cmd_seed(args):
    repository = sandbox_name(args.sandbox)
    print(accept_invitation(repository))
    branches = gh_json(["api", "repos/%s/branches" % repository]) or []
    if branches:
        print("%s already has branches (%s); seeding only ever writes an empty repository"
              % (repository, ", ".join(b["name"] for b in branches)))
        return 0
    root = tempfile.mkdtemp(prefix="sandbox-seed-")
    try:
        tree = os.path.join(root, "tree")
        os.makedirs(tree)
        storedform.materialize(os.path.join(SEED, "repo"), tree)
        branch = seed_fixture()["default_branch"]
        run(["git", "init", "-q", "-b", branch], cwd=tree)
        run(["git", "add", "-A"], cwd=tree)
        run(["git", "commit", "-q", "-m", "Seed the sandbox from agent-repo-governance's fixture"], cwd=tree)
        run(["git", "push", "-q", "https://github.com/%s.git" % repository, "HEAD:refs/heads/%s" % branch], cwd=tree)
        head = run(["git", "rev-parse", "HEAD"], cwd=tree).stdout.strip()
    finally:
        shutil.rmtree(root, True)
    print("seeded %s's %s at %s" % (repository, branch, head))
    return 0


# Steps 1 to 4.


def pr_head(number):
    return gh_json(["pr", "view", str(number), "--repo", THIS_REPOSITORY, "--json", "headRefOid,state"])


def check_directory(directory, sandbox):
    path = os.path.realpath(directory or tempfile.mkdtemp(prefix="live-check-%s-" % sandbox))
    os.makedirs(path, exist_ok=True)
    return path


def chosen_probes(names, sandbox):
    known = probes.registered()
    unknown = [name for name in names if name not in known]
    if unknown:
        raise RunnerError("unknown probes: %s (known: %s)" % (", ".join(unknown), ", ".join(known)))
    wrong = [name for name in names if sandbox not in known[name].sandboxes]
    if wrong:
        raise RunnerError("these probes don't run in the %s sandbox: %s" % (sandbox, ", ".join(wrong)))
    return [known[name] for name in names]


def context(state, directory):
    fixture = seed_fixture()
    return probes.Context(state["sandbox"], state["visibility"], fixture["default_branch"], fixture["confirmed"],
                          state["commit"], state.get("sandbox_pr"), directory)


def cmd_prepare(args):
    chosen = chosen_probes(args.probe, args.sandbox)
    commit = run(["git", "-C", REPO, "rev-parse", "HEAD"]).stdout.strip()
    if run(["git", "-C", REPO, "status", "--porcelain"]).stdout.strip():
        raise RunnerError("this checkout has uncommitted changes, so a result couldn't name the commit it ran on")
    pull = pr_head(args.pr)
    if pull["headRefOid"] != commit:
        raise RunnerError("PR #%s's head is %s, not this checkout's %s: push first" % (args.pr, pull["headRefOid"][:12], commit[:12]))
    repository, fixture = sandbox_name(args.sandbox), seed_fixture()
    directory = check_directory(args.directory, args.sandbox)
    work = tempfile.mkdtemp(prefix="live-render-")
    try:
        clone = os.path.join(work, "sandbox")
        run(["git", "clone", "-q", "https://github.com/%s.git" % repository, clone])
        default_branch = run(["git", "-C", clone, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"]).stdout.strip().split("/", 1)[1]
        if default_branch != fixture["default_branch"]:
            raise RunnerError("%s's default branch is %s, not the seed's %s" % (repository, default_branch, fixture["default_branch"]))
        stamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        branch = "live/%s-%s" % (commit[:12], stamp)
        run(["git", "-C", clone, "checkout", "-q", "-b", branch])
        confirmed = os.path.join(work, "confirmed.json")
        with open(confirmed, "w") as handle:
            json.dump(fixture["confirmed"], handle)
        rendered = run([sys.executable, GOVERN, "render", "--store", STORE, "--version", str(VERSION), "--allow-unreleased",
                        "--dest", clone, "--repository", repository, "--default-branch", default_branch,
                        "--confirmed", confirmed], check=False)
        if rendered.returncode != 0:
            raise RunnerError("rendering version %d failed: %s" % (VERSION, rendered.stdout.strip()))
        # The check's record, so a sandbox PR exists even when the sandbox already holds this render.
        record = os.path.join(clone, "live-checks", "%s.md" % branch.split("/", 1)[1])
        os.makedirs(os.path.dirname(record), exist_ok=True)
        with open(record, "w") as handle:
            handle.write("Live check of governance model version %d from %s at %s, probes: %s.\n"
                         % (VERSION, THIS_REPOSITORY, commit, ", ".join(args.probe)))
        run(["git", "-C", clone, "add", "-A"])
        run(["git", "-C", clone, "commit", "-q", "-m", "Live check: governance version %d at %s" % (VERSION, commit[:12])])
        head = run(["git", "-C", clone, "rev-parse", "HEAD"]).stdout.strip()
        run(["git", "-C", clone, "push", "-q", "origin", "HEAD:refs/heads/%s" % branch])
    finally:
        shutil.rmtree(work, True)
    body = (
        "A live check of governance model version %d from %s#%s at `%s`, opened by `tests/live/live.py prepare`.\n\n"
        "Risk: high — rewrites the sandbox's governance files, the gate workflow and the owner script among them\n"
        % (VERSION, THIS_REPOSITORY, args.pr, commit)
    )
    url = run(["gh", "pr", "create", "--repo", repository, "--base", default_branch, "--head", branch,
               "--title", "Live check: governance version %d at %s" % (VERSION, commit[:12]), "--body-file", "-"],
              stdin=body).stdout.strip()
    number = int(url.rstrip("/").split("/")[-1])
    state = {"pr": args.pr, "commit": commit, "sandbox": repository, "visibility": args.sandbox, "branch": branch,
             "sandbox_pr": number, "sandbox_head": head, "probes": args.probe}
    with open(os.path.join(directory, "prepared.json"), "w") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
    print("Opened %s from %s at %s, rendering %s." % (url, branch, head[:12], commit[:12]))
    print("Check directory: %s" % directory)
    print("")
    ctx = context(state, directory)
    print("habit's commands, in order, each with the ! prefix in Claude Code:")
    print("1. Merge the sandbox PR once its checks are green:")
    print("   ghm pr merge %d --repo %s --admin --squash --match-head-commit %s" % (number, repository, head))
    print("2. The owner-script command, after the merge:")
    print("   %s 2>&1 | tee %s" % (owner.command(repository), ctx.input_path(OWNER_REPORT)))
    step = 3
    for probe in chosen:
        for name, label, line in probe.commands(ctx):
            print("%d. %s (%s):" % (step, label, probe.name))
            print("   %s" % (line + (" 2>&1 | tee %s" % ctx.input_path(name) if name else "")))
            step += 1
    return 0


# Step 5.


def comment(state, results):
    """The result comment for this repository's PR: probe results only, naming the commit."""
    failed = [result for _, result in results if not result.passed]
    lines = [
        "## Live check at %s" % state["commit"],
        "",
        "- **Commit**: `%s`, this PR's head when the check ran." % state["commit"],
        "- **Sandbox**: `%s` (%s), PR %s#%d at `%s`." % (state["sandbox"], state["visibility"], state["sandbox"],
                                                         state["sandbox_pr"], state["sandbox_head"]),
        "- **Probes**: %s." % ", ".join(collections.OrderedDict((name, None) for name, _ in results)),
        "- **Result**: %s" % ("every assertion passed (%d of %d)." % (len(results), len(results)) if not failed
                              else "%d of %d assertions failed." % (len(failed), len(results))),
        "",
        "| Probe | Assertion | Result | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for name, result in results:
        cells = [name, result.assertion, "Pass" if result.passed else "Fail", str(result.detail)]
        lines.append("| %s |" % " | ".join(cell.replace("|", "\\|").replace("\n", " ") for cell in cells))
    return "\n".join(lines) + "\n"


def cmd_probe(args):
    directory = os.path.dirname(os.path.realpath(args.state))
    with open(args.state) as handle:
        state = json.load(handle)
    chosen = chosen_probes(args.probe, state["visibility"])
    # The probes and the target come from this checkout, so it must be the commit the results name.
    commit = run(["git", "-C", REPO, "rev-parse", "HEAD"]).stdout.strip()
    if commit != state["commit"] or run(["git", "-C", REPO, "status", "--porcelain"]).stdout.strip():
        raise RunnerError("this checkout is %s%s, not the prepared %s, so its probes couldn't speak for that commit"
                          % (commit[:12], " with uncommitted changes" if commit == state["commit"] else "", state["commit"][:12]))
    merged = gh_json(["pr", "view", str(state["sandbox_pr"]), "--repo", state["sandbox"], "--json", "state,headRefOid"])
    if merged["state"] != "MERGED" or merged["headRefOid"] != state["sandbox_head"]:
        raise RunnerError("%s#%d is %s at %s, not merged at %s" % (state["sandbox"], state["sandbox_pr"], merged["state"],
                                                                  merged["headRefOid"][:12], state["sandbox_head"][:12]))
    ctx = context(state, directory)
    results = [(probe.name, result) for probe in chosen for result in probes.run(probe, ctx)]
    text = comment(state, results)
    sys.stdout.write(text)
    if args.post:
        head = pr_head(state["pr"])["headRefOid"]
        if head != state["commit"]:
            raise RunnerError("PR #%s's head moved to %s, so these results for %s aren't posted: rerun the live check"
                              % (state["pr"], head[:12], state["commit"][:12]))
        url = run(["gh", "pr", "comment", str(state["pr"]), "--repo", THIS_REPOSITORY, "--body-file", "-"], stdin=text).stdout.strip()
        print("posted: %s" % url)
    return 0 if all(result.passed for _, result in results) else 1


# Version 1's cut (#44 §11): the end-to-end run is an Initialize of the public sandbox, so the
# sandbox returns to its seed first, and habit runs this commit's generator as in the scenarios.

PLUGIN = "cut"
SKILL_COMMAND = "/%s:govern-repository" % PLUGIN
SKILL_PATH = "generator/govern-repository"
SANDBOX_URL = "https://github.com/%s.git"
# The settings only the scenario runner sets (docs/agents/build.md); the end-to-end run sets none.
SCENARIO_SETTINGS = ("GOVERN_SCENARIO_STORE", "GOVERN_SCENARIO_HOME", "GOVERN_SCENARIO_REPOSITORY")
# A directory's instruction files that Claude Code or OpenCode would load into a session below it.
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md")


def seed_tree(work):
    """The git tree id of the materialized seed, staged in a scratch repository under work."""
    tree = os.path.join(work, "seed")
    os.makedirs(tree)
    storedform.materialize(os.path.join(SEED, "repo"), tree)
    run(["git", "init", "-q"], cwd=tree)
    run(["git", "add", "-A", "--force"], cwd=tree)
    return run(["git", "write-tree"], cwd=tree).stdout.strip()


def reset_to_seed(clone):
    """Replace every tracked file in a fresh clone with the materialized seed, staged; return the staged tree's id."""
    run(["git", "rm", "-r", "-q", "--ignore-unmatch", "--", "."], cwd=clone)
    storedform.materialize(os.path.join(SEED, "repo"), clone)
    run(["git", "add", "-A", "--force"], cwd=clone)
    return run(["git", "write-tree"], cwd=clone).stdout.strip()


def build_plugin(repo, rev, directory):
    """The session-only plugin: rev's committed generator under skills/, beside its manifest; return the skill's directory."""
    skill = os.path.join(directory, "skills", "govern-repository")
    os.makedirs(skill)
    archive = subprocess.run(["git", "-C", repo, "archive", "--format=tar", "%s:%s" % (rev, SKILL_PATH)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if archive.returncode != 0:
        raise RunnerError("`git archive` of %s at %s failed: %s" % (SKILL_PATH, rev, archive.stderr.decode("utf-8", "replace")))
    unpacked = subprocess.run(["tar", "-x", "-f", "-", "-C", skill], input=archive.stdout, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    if unpacked.returncode != 0:
        raise RunnerError("unpacking the generator failed: %s" % unpacked.stderr.decode("utf-8", "replace"))
    manifest = os.path.join(directory, ".claude-plugin", "plugin.json")
    os.makedirs(os.path.dirname(manifest))
    with open(manifest, "w") as handle:
        json.dump({"name": PLUGIN, "version": "1.0.0",
                   "description": "This commit's govern-repository, for version 1's end-to-end run only"}, handle, indent=2)
        handle.write("\n")
    return skill


def start_command(checkout, plugin):
    """habit's line: Claude Code in the end-to-end checkout, loading the plugin, with no scenario setting."""
    unset = " ".join("-u %s" % name for name in SCENARIO_SETTINGS)
    return "cd %s && env %s claude --plugin-dir %s" % (shlex.quote(checkout), unset, shlex.quote(plugin))


def instruction_files_above(path):
    """Every instruction file in path's directory or one above it, which a harness started there would load."""
    found, here = [], os.path.realpath(path)
    while True:
        found += [os.path.join(here, name) for name in INSTRUCTION_FILES if os.path.isfile(os.path.join(here, name))]
        parent = os.path.dirname(here)
        if parent == here:
            return found
        here = parent


def clone_sandbox(repository, clone):
    """Clone a sandbox afresh and return its default branch, refusing one other than the seed's."""
    run(["git", "clone", "-q", SANDBOX_URL % repository, clone])
    branch = run(["git", "-C", clone, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"]).stdout.strip().split("/", 1)[1]
    if branch != seed_fixture()["default_branch"]:
        raise RunnerError("%s's default branch is %s, not the seed's %s" % (repository, branch, seed_fixture()["default_branch"]))
    return branch


def rulesets_of(repository):
    """{name: ruleset} of a repository's rulesets, as the agent account lists them (id and enforcement included)."""
    return dict((ruleset["name"], ruleset) for ruleset in gh_json(["api", "repos/%s/rulesets" % repository]) or [])


def cmd_reset(args):
    repository = sandbox_name(args.sandbox)
    gate = rulesets_of(repository).get("Gate")
    work = tempfile.mkdtemp(prefix="sandbox-reset-")
    try:
        clone = os.path.join(work, "sandbox")
        default_branch = clone_sandbox(repository, clone)
        seed = seed_tree(work)
        if run(["git", "-C", clone, "rev-parse", "HEAD^{tree}"]).stdout.strip() == seed:
            print("%s's %s already holds the seed's tree %s: nothing to reset." % (repository, default_branch, seed))
            if gate and gate.get("enforcement") != "disabled":
                print("habit's step: disable the Gate ruleset in the browser, leaving Merge and History active:")
                print("   " + gate_step(repository, gate))
            return 0
        branch = "reset/seed-%s" % datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        run(["git", "-C", clone, "checkout", "-q", "-b", branch])
        staged = reset_to_seed(clone)
        if staged != seed:
            raise RunnerError("the reset staged the tree %s, not the seed's %s" % (staged, seed))
        run(["git", "-C", clone, "commit", "-q", "-m", "Reset the sandbox to its seed"])
        head = run(["git", "-C", clone, "rev-parse", "HEAD"]).stdout.strip()
        if run(["git", "-C", clone, "rev-parse", "HEAD^{tree}"]).stdout.strip() != seed:
            raise RunnerError("the reset commit %s doesn't hold the seed's tree %s" % (head[:12], seed))
        run(["git", "-C", clone, "push", "-q", "origin", "HEAD:refs/heads/%s" % branch])
    finally:
        shutil.rmtree(work, True)
    body = (
        "Returns the sandbox to its seed, `tests/fixtures/repositories/sandbox/` in %s, so that version 1's end-to-end "
        "run starts an Initialize. It removes every governance file and `live-checks/`. Opened by "
        "`tests/live/live.py reset`; the head's tree is the seed's `%s`.\n\n"
        "Risk: high — removes the sandbox's governance, the gate workflow, the owner script and the record among them\n"
        % (THIS_REPOSITORY, seed)
    )
    url = run(["gh", "pr", "create", "--repo", repository, "--base", default_branch, "--head", branch,
               "--title", "Reset the sandbox to its seed", "--body-file", "-"], stdin=body).stdout.strip()
    number = int(url.rstrip("/").split("/")[-1])
    print("Opened %s from %s at %s, whose tree is the seed's %s." % (url, branch, head[:12], seed[:12]))
    print("")
    print("habit's steps, in order:")
    print("1. Once the reset PR's checks pass, merge it with the ! prefix in Claude Code:")
    print("   ghm pr merge %d --repo %s --admin --squash --match-head-commit %s" % (number, repository, head))
    print("2. Then disable the Gate ruleset in the browser, leaving Merge and History active:")
    print("   " + gate_step(repository, gate))
    return 0


def gate_step(repository, gate):
    if not gate:
        return "%s has no Gate ruleset, so there is nothing to disable." % repository
    return "https://github.com/%s/settings/rules/%s : Enforcement status Disabled, then Save changes." % (repository, gate["id"])


def pushed_head(number):
    """This checkout's commit, once it is clean and PR number's head."""
    commit = run(["git", "-C", REPO, "rev-parse", "HEAD"]).stdout.strip()
    if run(["git", "-C", REPO, "status", "--porcelain"]).stdout.strip():
        raise RunnerError("this checkout has uncommitted changes, so a result couldn't name the commit it ran on")
    head = pr_head(number)["headRefOid"]
    if head != commit:
        raise RunnerError("PR #%s's head is %s, not this checkout's %s: push first" % (number, head[:12], commit[:12]))
    return commit


def identity(entry):
    return json.loads(run([sys.executable, entry, "identity"]).stdout)["identity"]


def cmd_end_to_end(args):
    commit = pushed_head(args.pr)
    repository = sandbox_name(args.sandbox)
    directory = os.path.realpath(tempfile.mkdtemp(prefix="end-to-end-"))
    try:
        state = launch(args.pr, commit, repository, directory)
    except BaseException:
        shutil.rmtree(directory, True)
        raise
    print("%s's %s is at the seed (%s), so the run is an Initialize; its rulesets are %s; the plugin's generator is %s."
          % (repository, state["default_branch"], state["sandbox_head"][:12],
             ", ".join("%s %s" % item for item in sorted(state["rulesets"].items())), state["identity"][:12]))
    print("State: %s" % os.path.join(directory, "end-to-end.json"))
    print("")
    print("habit's steps, in order:")
    print("1. In a terminal of your own, not with Claude Code's ! prefix, start Claude Code there with this commit's generator:")
    print("   %s" % start_command(state["checkout"], state["plugin"]))
    print("2. Type %s, never the bare /govern-repository, and answer its confirmation." % SKILL_COMMAND)
    print("3. Then follow that run's Builder to the end: its Codex review bot request, the Reviewer it names, the high-risk")
    print("   report, the pinned merge, saying merged in its terminal, and the owner-script command it hands over.")
    return 0


def launch(pr, commit, repository, directory):
    """The end-to-end run's checkout and plugin in directory, once every check passes; its state, also in end-to-end.json."""
    above = instruction_files_above(directory)
    if above:
        raise RunnerError("%s sits below %s, which a session there would load: set TMPDIR outside them"
                          % (directory, ", ".join(above)))
    checkout, plugin = os.path.join(directory, "checkout"), os.path.join(directory, "plugin")
    default_branch = clone_sandbox(repository, checkout)
    work = tempfile.mkdtemp(prefix="seed-tree-")
    try:
        seed = seed_tree(work)
    finally:
        shutil.rmtree(work, True)
    tree = run(["git", "-C", checkout, "rev-parse", "HEAD^{tree}"]).stdout.strip()
    if tree != seed:
        raise RunnerError("%s's %s holds the tree %s, not the seed's %s: run `live.py reset` and have habit merge it"
                          % (repository, default_branch, tree[:12], seed[:12]))
    enforcement = dict((name, ruleset.get("enforcement")) for name, ruleset in rulesets_of(repository).items())
    wanted = {"Gate": "disabled", "Merge": "active", "History": "active"}
    wrong = ["%s is %s, not %s" % (name, enforcement.get(name, "missing"), state) for name, state in sorted(wanted.items())
             if enforcement.get(name) != state]
    if wrong:
        raise RunnerError("%s's rulesets aren't as the reset leaves them (%s): habit disables only Gate, as `live.py reset` printed"
                          % (repository, "; ".join(wrong)))
    # The seed holds no record, so the run is an Initialize. The plugin is the commit's generator exported clean, so
    # its identity is the head's that the run's issue must name, whatever an ignored file in this checkout holds.
    head_identity = identity(os.path.join(build_plugin(REPO, commit, plugin), "scripts", "govern.py"))
    state = {"pr": pr, "commit": commit, "identity": head_identity, "sandbox": repository,
             "default_branch": default_branch, "sandbox_head": run(["git", "-C", checkout, "rev-parse", "HEAD"]).stdout.strip(),
             "rulesets": enforcement, "checkout": checkout, "plugin": plugin,
             "started": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    with open(os.path.join(directory, "end-to-end.json"), "w") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
    return state


def build_parser():
    parser = argparse.ArgumentParser(prog="tests/live/live.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True
    creating = commands.add_parser("sandbox-command", help="print habit's line that creates the sandboxes")
    creating.set_defaults(run=cmd_sandbox_command)
    seeding = commands.add_parser("seed", help="accept the invitation and seed an empty sandbox")
    seeding.add_argument("--sandbox", choices=("public", "private"), required=True)
    seeding.set_defaults(run=cmd_seed)
    preparing = commands.add_parser("prepare", help="steps 1 to 4")
    preparing.add_argument("--pr", type=int, required=True, help="this repository's PR whose head is checked out")
    preparing.add_argument("--sandbox", choices=("public", "private"), required=True)
    preparing.add_argument("--probe", action="append", required=True, help="a probe this check will run; repeat")
    preparing.add_argument("--directory", help="the check directory; default: a new temporary one")
    preparing.set_defaults(run=cmd_prepare)
    probing = commands.add_parser("probe", help="step 5")
    probing.add_argument("--state", required=True, help="prepared.json in the check directory")
    probing.add_argument("--probe", action="append", required=True, help="a probe to run; repeat")
    probing.add_argument("--post", action="store_true", help="post the results on this repository's PR")
    probing.set_defaults(run=cmd_probe)
    resetting = commands.add_parser("reset", help="open the sandbox PR that returns it to its seed")
    resetting.add_argument("--sandbox", choices=("public",), required=True, help="the end-to-end run uses only the public one")
    resetting.set_defaults(run=cmd_reset)
    ending = commands.add_parser("end-to-end", help="build the head's generator beside a fresh sandbox clone")
    ending.add_argument("--pr", type=int, required=True, help="this repository's PR whose head is checked out")
    ending.add_argument("--sandbox", choices=("public",), required=True, help="the end-to-end run uses only the public one")
    ending.set_defaults(run=cmd_end_to_end)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.run(args)
    except RunnerError as error:
        print("stopped: %s" % error)
        return 2


if __name__ == "__main__":
    sys.exit(main())
