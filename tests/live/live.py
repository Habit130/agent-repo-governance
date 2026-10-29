#!/usr/bin/env python3
"""The live-check runner (#44 §11, §12): real GitHub, in the sandbox repositories only.

  sandbox-command  print habit's one line that creates both sandboxes and invites the agent account
  seed             as the agent: accept a sandbox's invitation, and seed its empty default branch
  prepare          steps 1 to 4: render this checkout's PR head into a fresh sandbox branch, open the
                   sandbox PR, and hand habit the pinned merge command and each probe's commands
  probe            step 5: run the named probes and post their results on this repository's PR

Execution runs it as the agent account. habit runs only the printed commands, each one line
with Claude Code's `!` prefix. Probes plug in under `tests/live/probes/` (that package's
docstring gives their shape). Nothing here deletes a sandbox, force-pushes or writes outside
the two sandboxes and this repository's PR; results carry probe output only, never a credential.
"""

import argparse
import datetime
import json
import os
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
MAINTAINER_ENV = ("export GH_CONFIG_DIR=\"%s\"; unset GH_TOKEN GITHUB_TOKEN GH_ENTERPRISE_TOKEN GITHUB_ENTERPRISE_TOKEN; "
                  % owner.MAINTAINER_GH_CONFIG)


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
        "/bin/bash -c '" + MAINTAINER_ENV + "s=0; for spec in " + specs + "; do "
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
        run(["git", "-C", clone, "add", "-A"])
        if not run(["git", "-C", clone, "status", "--porcelain"]).stdout.strip():
            raise RunnerError("%s's %s already holds this render, so there is nothing to merge" % (repository, default_branch))
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
    print("habit's commands, in order, each with the ! prefix in Claude Code:")
    print("1. Merge the sandbox PR once its checks are green:")
    print("   ghm pr merge %d --repo %s --admin --squash --match-head-commit %s" % (number, repository, head))
    step = 2
    ctx = context(state, directory)
    for probe in chosen:
        for name, label, line in probe.commands(ctx):
            print("%d. %s (%s):" % (step, label, probe.name))
            print("   %s" % (line + (" 2>&1 | tee %s" % ctx.input_path(name) if name else "")))
            step += 1
    return 0


# Step 5.


def comment(state, results):
    """The result comment for this repository's PR: probe results only, naming the commit."""
    counted = [result for _, result in results if result.passed is not None]
    failed = [result for result in counted if not result.passed]
    lines = [
        "## Live check at %s" % state["commit"],
        "",
        "- **Commit**: `%s`, this PR's head when the check ran." % state["commit"],
        "- **Sandbox**: `%s` (%s), PR %s#%d at `%s`." % (state["sandbox"], state["visibility"], state["sandbox"],
                                                         state["sandbox_pr"], state["sandbox_head"]),
        "- **Probes**: %s." % ", ".join(sorted(set(name for name, _ in results), key=[n for n, _ in results].index)),
        "- **Result**: %s" % ("every assertion passed (%d of %d)." % (len(counted), len(counted)) if not failed
                              else "%d of %d assertions failed." % (len(failed), len(counted))),
        "",
        "| Probe | Assertion | Result | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for name, result in results:
        mark = "Pass" if result.passed else ("Not checked" if result.passed is None else "Fail")
        detail = str(result.detail).replace("|", "\\|").replace("\n", " ")
        lines.append("| %s | %s | %s | %s |" % (name, result.assertion, mark, detail))
    return "\n".join(lines) + "\n"


def cmd_probe(args):
    directory = os.path.dirname(os.path.realpath(args.state))
    with open(args.state) as handle:
        state = json.load(handle)
    chosen = chosen_probes(args.probe, state["visibility"])
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
    return 0 if all(result.passed is not False for _, result in results) else 1


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
