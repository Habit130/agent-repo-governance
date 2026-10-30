"""The preconditions (#44 §6.1): checked by script, reported together, with habit's one checklist.

The harness comes first, and a harness other than Claude Code or OpenCode stops the run before
any other step (`harness.py`). Then every other item is checked and reported in this order,
each `pass`, `fail`, `habit` (a step on habit's checklist), `agent` (the agent's own next step:
accepting habit's invitation) or `not checked` (an earlier item it needs failed):

- directory: a git checkout whose `origin` is a GitHub repository;
- repository: owned by the maintainer account, not an organization, and its default branch
  has a commit;
- private: a private repository stops with the reason, failing closed until #53;
- collaborator: the agent account has write permission, read from its own permission;
- machine check: the installed machine check passes against the machine home;
- machine skill set: every relied-on skill is a managed skill in the installed state;
- versions: the store has a released version, and the record is no newer than it;
- review bots: their connection is on habit's checklist, since the agent can't read it.

Nothing here writes.
"""

import json
import os
import subprocess
import sys

from govlib import AGENT, MAINTAINER, GovernError, checkout, github, harness, store as stores

ITEMS = ("directory", "repository", "private", "collaborator", "machine check", "machine skill set", "versions", "review bots")
INSTALLED_STATE = (".agents", "governance", "installed.json")
MACHINE_ENTRY = (".agents", "governance", "machine", "scripts", "machine.py")
READY = "with the ready command in Habit130/agent-repo-governance's machine/ready.sh"


class Run(object):
    def __init__(self):
        self.items, self.checklist = [], []

    def add(self, item, status, detail, **extra):
        entry = {"item": item, "status": status, "detail": detail}
        entry.update(extra)
        self.items.append(entry)

    def ask(self, step, detail, command=None):
        entry = {"step": step, "detail": detail}
        if command:
            entry["command"] = command
        self.checklist.append(entry)


def invite_command(repository):
    """habit's invite, run in habit's own terminal, where the `ghm` alias is defined."""
    return "ghm api --method PUT repos/%s/collaborators/%s -f permission=push" % (repository, AGENT)


def machine_check(home, env=None):
    """(exit code, failing lines) of the installed machine check run against the home."""
    entry = os.path.join(home, *MACHINE_ENTRY)
    if not os.path.isfile(entry):
        return None, ["the installed machine check, ~/%s, isn't there" % "/".join(MACHINE_ENTRY)]
    try:
        result = subprocess.run(
            [sys.executable, entry, "check", "--home", home],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, [str(error)]
    out = result.stdout.decode("utf-8", "replace")
    lines = [line for line in out.splitlines() if line.startswith("[失败]") or line.startswith("拒绝")]
    return result.returncode, lines


def installed_skills(home):
    """The managed skills' names in the installed state, or None with the reason."""
    path = os.path.join(home, *INSTALLED_STATE)
    try:
        with open(path) as handle:
            state = json.load(handle)
        return sorted(state["skills"]), ""
    except (OSError, ValueError, KeyError, TypeError) as error:
        return None, "the installed state ~/%s can't be read: %s" % ("/".join(INSTALLED_STATE), error)


def _repository_items(run, gh, repository):
    """The repository's own facts; the repository's JSON, or None when it can't be read."""
    response = gh.get("repos/%s" % repository)
    if not response.ok:
        run.add("repository", "fail", "the agent account can't read %s: %s" % (repository, response.message))
        run.add("private", "not checked", "the repository can't be read")
        return None
    data = response.data
    owner = data.get("owner") or {}
    problems = []
    if owner.get("type") != "User" or owner.get("login") != MAINTAINER:
        problems.append(
            "it is owned by %s %s, not by the maintainer account %s"
            % ((owner.get("type") or "an unknown account").lower(), owner.get("login"), MAINTAINER)
        )
    branch = data.get("default_branch")
    if not gh.get(github.branch_path(repository, branch)).ok:
        problems.append("its default branch %s has no commit" % branch)
    if problems:
        run.add("repository", "fail", "; ".join(problems))
    else:
        run.add("repository", "pass", "owned by %s, default branch %s with a commit" % (MAINTAINER, branch))
    if data.get("private"):
        run.add(
            "private",
            "fail",
            "the repository is private; until the private-repository reads arrive (#53), "
            "a private repository stops the run, failing closed",
        )
    else:
        run.add("private", "pass", "the repository is public")
    return data


def _collaborator_item(run, gh, repository, data):
    permissions = data.get("permissions") or {}
    if permissions.get("push") or permissions.get("maintain") or permissions.get("admin"):
        run.add("collaborator", "pass", "the agent account %s has write permission" % AGENT)
        return
    invitations = gh.get("user/repository_invitations?per_page=100")
    pending = [
        item for item in (invitations.data or []) if ((item.get("repository") or {}).get("full_name") or "") == repository
    ] if invitations.ok else []
    if pending:
        run.add(
            "collaborator",
            "agent",
            "habit's invitation is pending; the agent accepts it with `govern.py accept-invitation`",
            invitation=pending[0]["id"],
        )
        return
    run.add("collaborator", "habit", "the agent account %s has no write permission and no pending invitation" % AGENT)
    run.ask(
        "invite",
        "invite the agent account as a write collaborator, in habit's own terminal; the agent then accepts",
        invite_command(repository),
    )


def _machine_items(run, home, env):
    code, lines = machine_check(home, env)
    if code == 0:
        run.add("machine check", "pass", "the machine check passes against %s" % home)
    else:
        run.add("machine check", "fail", "the machine check exits %s: %s" % (code, " | ".join(lines) or "no report"))
        run.ask("install", "fix the machine check's failures, running the install %s if they need it" % READY)
    return code


def _skill_item(run, home, manifest):
    names, reason = installed_skills(home)
    if names is None:
        run.add("machine skill set", "fail", reason)
        return
    missing = sorted(set(manifest["relied_on_skills"]) - set(names))
    if missing:
        run.add("machine skill set", "fail", "relied-on skills missing from the machine skill set: %s" % ", ".join(missing))
        run.ask("install", "run the install %s, so the machine skill set holds every relied-on skill" % READY)
    else:
        run.add("machine skill set", "pass", "all %d relied-on skills are managed skills" % len(manifest["relied_on_skills"]))


def run(worktree, home, store_root, env=None):
    """The preconditions' facts; exit code 0 when no item failed, 1 otherwise, 2 for a refused harness."""
    judged = harness.require(env)

    result = Run()
    gh = github.GitHub(env)
    root = checkout.toplevel(worktree)
    repository = data = None
    if root is None:
        result.add("directory", "fail", "%s isn't inside a git checkout" % os.path.realpath(worktree))
    else:
        try:
            repository = checkout.repository(root)
            result.add("directory", "pass", "a checkout whose origin is %s on GitHub" % repository)
        except GovernError as error:
            result.add("directory", "fail", str(error))
    if repository:
        data = _repository_items(result, gh, repository)
    else:
        result.add("repository", "not checked", "the directory names no GitHub repository")
        result.add("private", "not checked", "the directory names no GitHub repository")
    if data is not None:
        _collaborator_item(result, gh, repository, data)
    else:
        result.add("collaborator", "not checked", "the repository can't be read")

    _machine_items(result, home, env)

    source = stores.Store(store_root)
    try:
        installed = source.installed_version()
        manifest = source.manifest(installed) if installed is not None else None
    except GovernError as error:
        installed = manifest = None
        result.add("machine skill set", "not checked", "the installed store can't be read")
        result.add("versions", "fail", "the installed store can't be read: %s" % error)
    else:
        if manifest is None:
            result.add("machine skill set", "not checked", "the installed store has no released version")
            result.add("versions", "fail", "the installed template store has no released version, so nothing can be written")
            result.ask("install", "run the install %s, from a commit whose store has a released version" % READY)
        else:
            _skill_item(result, home, manifest)
            found = checkout.read_record(root) if root else {"present": False}
            if found.get("parses") and found["version"] > installed:
                result.add(
                    "versions",
                    "fail",
                    "the record is at version %d, newer than the installed version %d" % (found["version"], installed),
                )
                result.ask("install", "run the install %s, so the machine has the record's version" % READY)
            else:
                result.add("versions", "pass", "installed version %d; the record is no newer" % installed)

    result.add("review bots", "habit", "the agent can't read Bugbot's or the Codex review bot's connection")
    private = bool(data and data.get("private"))
    result.ask(
        "review bots",
        "connect Bugbot (the Cursor GitHub App's repository access) and the Codex review bot (its connector's "
        "repository list) to %s%s" % (repository or "the repository", "; on a private repository, both apps' access to it" if private else ""),
    )

    order = dict((item, index) for index, item in enumerate(ITEMS))
    result.items.sort(key=lambda entry: order[entry["item"]])
    steps = []
    for entry in result.checklist:
        if entry not in steps:
            steps.append(entry)
    failed = any(entry["status"] == "fail" for entry in result.items)
    facts = {
        "harness": judged,
        "repository": repository,
        "items": result.items,
        "checklist": steps,
        "passed": not failed,
    }
    return facts, 1 if failed else 0
