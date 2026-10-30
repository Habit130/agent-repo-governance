"""The governance gate's probes (#41 §8, #44 §11): its trigger, its reruns, its one source, and the rulesets with it.

Run the four together. A check takes three steps after habit's merge and owner-script run:

1. `live.py probe` without `--post` sets the check up, as the agent account, in the sandbox
   only. It opens three probe PRs from `live/gate-<sandbox PR>-<UTC stamp>-…` branches: `trigger`, with
   a good `Risk:` line and then a pushed second commit; `edit`, with a bad one that a body
   edit fixes; `failing`, whose bad line stays. Each change is one file under
   `live-checks/`. It pushes a `source` branch whose commit is in no PR, and posts the
   agent's success statuses on it for `governance-gate` and every confirmed check. After
   each step it waits for the gate's run, failing on a timeout, and reads the run, its job's
   log and the head's check runs. It remembers what it read as `gate_setup` and writes
   `gate_targets.txt` for habit's command. A later run reads them back and never sets up
   again. An attempt that stops fails its run; the next run tries afresh under new branch
   names, and `gate-trigger` names the stopped attempts.
2. habit runs `gate-rulesets`' one command, as the agent account (`gh`, never `ghm`): a
   direct push of the source commit to the default branch, a force-push of the default
    branch and of the source branch, and the merge of each probe PR at its head. The harness keeps these attempts
    with habit; the probes never push to the default branch, force-push or merge.
   The first push or merge that exits 0 stops every later attempt and exits 3. Its section
   keeps `exit=0` and prints `stop-after: <attempt>` plus Chinese advice; `== account`
   remains, and `== after` reads the refs after the stop. habit then stops as for a product
   question instead of rerunning. A failed clone, checkout or amend prints `never-reached:`;
   it is neither a success nor a rejection, and later attempts still run.
3. `live.py probe --post` judges what step 1 read, habit's output, and the refs and PRs as
    they are then. A stopped rulesets run fails each skipped attempt with the stop's reason,
    while still reading both refs and every probe PR from GitHub.

Every assertion reads GitHub's own answers. A same-name status sits only on the source
commit, so it never confounds a probe PR's head. GitHub's rejections, recorded from the
public sandbox on 2026-10-30 (`docs/agents/build.md`, The gate's live check), name each
violated rule; a merge rejection that names no required check shows the gate's result
satisfied it.
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from machinelib import AGENT
from probes import Probe, ProbeError, Result
from probes.owner import report_items

CHECK = "governance-gate"
WORKFLOW = ".github/workflows/governance-gate.yml"
EVENT = "pull_request_target"
ACTIONS_APP = 15368
GOOD_RISK = "Risk: low — one file under live-checks, written by the gate's live check"
BAD_RISK = "Risk: none — a tier the gate refuses, on purpose"
ROLES = ("trigger", "edit", "failing")
TARGETS = "gate_targets.txt"
ATTEMPTS = "gate_attempts"
WAIT_SECONDS = 600
POLL_SECONDS = 10
_JUDGED = re.compile(r"governance-gate on ([0-9a-f]{40}), judged by the default branch at ([0-9a-f]{40})")
_SECTION = re.compile(r"(?m)^== (.*)$")
_EXIT = re.compile(r"(?m)^exit=(\d+)\s*$")
_STOP = re.compile(r"(?m)^stop-after: (.+)$")


# Step 1: the setup, as the agent account.


def _git(args, cwd):
    result = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    if result.returncode != 0:
        raise ProbeError("`git %s` failed: %s" % (" ".join(args[:3]), " ".join(result.stderr.split())))
    return result.stdout.strip()


def _gh(context, args, stdin=None):
    code, out, err = context.gh(args, stdin=stdin)
    if code != 0:
        raise ProbeError("`gh %s` failed: %s" % (" ".join(args[:3]), " ".join(err.split())))
    return out


def _now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _body(risk):
    return "A probe PR of the governance gate's live check (`tests/live/probes/gate.py`).\n\n%s\n" % risk


def _commit_file(clone, name, text):
    path = os.path.join(clone, "live-checks", name)
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "w") as handle:
        handle.write(text)
    _git(["add", "-A"], clone)
    _git(["commit", "-q", "-m", "Live check: %s" % name], clone)
    return _git(["rev-parse", "HEAD"], clone)


def _check_run(item):
    return {"id": item["id"], "conclusion": item.get("conclusion"), "app_id": (item.get("app") or {}).get("id"),
            "title": (item.get("output") or {}).get("title"), "completed_at": item.get("completed_at")}


def _read_run(context, run, head):
    """What GitHub shows of one completed gate run: the run, its job, its log line and its posted check run."""
    jobs = (context.api("repos/%s/actions/runs/%s/jobs" % (context.repository, run["id"])) or {}).get("jobs") or []
    job = next((j for j in jobs if j.get("name") == CHECK), None)
    observed = {"id": run["id"], "event": run.get("event"), "path": run.get("path"), "head_sha": run.get("head_sha"),
                "conclusion": run.get("conclusion"), "created_at": run.get("created_at"), "judged": None,
                "job": None, "posted": None}
    if job is None:
        return observed
    code, log, _ = context.gh(["api", "--allow-escape-sequences", "repos/%s/actions/jobs/%s/logs" % (context.repository, job["id"])])
    match = _JUDGED.search(log) if code == 0 else None
    observed["judged"] = list(match.groups()) if match else None
    listed = context.api("repos/%s/commits/%s/check-runs?check_name=%s&filter=all&per_page=100"
                         % (context.repository, head, CHECK)) or {}
    job_run = int(str(job.get("check_run_url", "")).rstrip("/").rsplit("/", 1)[-1] or 0)
    for item in listed.get("check_runs") or []:
        if item["id"] == job_run:
            observed["job"] = _check_run(item)
        elif job.get("started_at") and job.get("completed_at") and \
                job["started_at"] <= (item.get("completed_at") or "") <= job["completed_at"]:
            observed["posted"] = _check_run(item)
    return observed


def _await_run(context, head, seen):
    """The first completed run of the gate's workflow on head that isn't in seen; ProbeError after WAIT_SECONDS.

    It reads every event's runs, so the trigger is what GitHub ran, judged by `gate-trigger`.
    """
    deadline = time.time() + WAIT_SECONDS
    while True:
        try:
            runs = (context.api("repos/%s/actions/runs?head_sha=%s&per_page=100" % (context.repository, head))
                    or {}).get("workflow_runs") or []
        except ProbeError as error:
            # A read that fails while waiting is retried until the deadline, which names it.
            runs, last = [], error
        else:
            last = None
        done = sorted((r for r in runs if r.get("path") == WORKFLOW and r["id"] not in seen and r.get("status") == "completed"),
                      key=lambda r: r["id"])
        if done:
            seen.add(done[0]["id"])
            return _read_run(context, done[0], head)
        if time.time() > deadline:
            raise ProbeError("no completed %s run on %s within %d seconds%s" % (
                CHECK, head[:12], WAIT_SECONDS, "; the last read failed: %s" % last if last else ""))
        time.sleep(POLL_SECONDS)


def _open(context, branch, risk):
    url = _gh(context, ["pr", "create", "--repo", context.repository, "--base", context.default_branch, "--head", branch,
                        "--title", "Live check: gate probe %s" % branch, "--body-file", "-"], stdin=_body(risk)).strip()
    return int(url.rstrip("/").rsplit("/", 1)[-1])


def _required(context):
    rules = context.api("repos/%s/rules/branches/%s" % (context.repository, context.default_branch)) or []
    found = []
    for rule in rules:
        if rule.get("type") == "required_status_checks":
            found.extend((rule.get("parameters") or {}).get("required_status_checks") or [])
    return found


def _act(context):
    repository, branch = context.repository, context.default_branch
    # Each attempt names its own branches: a stopped attempt's branches stay, and History blocks pushing over them.
    prefix = "live/gate-%s-%s" % (context.sandbox_pr, datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"))
    setup = {"default_head": context.api("repos/%s/commits/%s" % (repository, branch))["sha"],
             "required": _required(context), "pulls": {}}
    work = tempfile.mkdtemp(prefix="live-gate-")
    try:
        clone = os.path.join(work, "sandbox")
        url = "https://github.com/%s.git" % repository
        _git(["clone", "-q", url, clone], work)
        heads = {}
        for role in ("trigger", "edit", "failing", "source"):
            _git(["checkout", "-q", "-B", "%s-%s" % (prefix, role), "origin/%s" % branch], clone)
            heads[role] = _commit_file(clone, "gate-%s-%s.md" % (context.sandbox_pr, role),
                                       "The governance gate's live check, probe %s, for %s.\n" % (role, context.commit))
            _git(["push", "-q", url, "HEAD:refs/heads/%s-%s" % (prefix, role)], clone)
        source = heads["source"]
        for name in [CHECK] + [c for c in context.confirmed.get("required_checks") or [] if c != CHECK]:
            _gh(context, ["api", "--method", "POST", "repos/%s/statuses/%s" % (repository, source), "-f", "state=success",
                          "-f", "context=%s" % name, "-f", "description=the agent's same-name status, gate-source probe"])
        statuses = context.api("repos/%s/commits/%s/statuses?per_page=100" % (repository, source)) or []
        gate_runs = context.api("repos/%s/commits/%s/check-runs?check_name=%s&filter=all" % (repository, source, CHECK)) or {}
        setup["source"] = {"branch": "%s-source" % prefix, "commit": source,
                           "statuses": [{"context": s.get("context"), "state": s.get("state"),
                                         "creator": (s.get("creator") or {}).get("login")} for s in statuses],
                           "gate_check_runs": gate_runs.get("total_count", 0)}
        seen = set()
        for role, risk in zip(ROLES, (GOOD_RISK, BAD_RISK, BAD_RISK)):
            number = _open(context, "%s-%s" % (prefix, role), risk)
            setup["pulls"][role] = {"number": number, "branch": "%s-%s" % (prefix, role), "stages": []}
        for role in ROLES:
            setup["pulls"][role]["stages"].append({"step": "opened", "head": heads[role], "at": None,
                                                   "run": _await_run(context, heads[role], seen)})
        edit = setup["pulls"]["edit"]
        at = _now()
        _gh(context, ["pr", "edit", str(edit["number"]), "--repo", repository, "--body-file", "-"], stdin=_body(GOOD_RISK))
        edit["stages"].append({"step": "body fixed", "head": heads["edit"], "at": at,
                               "run": _await_run(context, heads["edit"], seen)})
        _git(["checkout", "-q", "%s-trigger" % prefix], clone)
        pushed = _commit_file(clone, "gate-%s-trigger-push.md" % context.sandbox_pr, "A second commit, pushed to rerun the gate.\n")
        at = _now()
        _git(["push", "-q", url, "HEAD:refs/heads/%s-trigger" % prefix], clone)
        setup["pulls"]["trigger"]["stages"].append({"step": "pushed", "head": pushed, "at": at,
                                                    "run": _await_run(context, pushed, seen)})
    finally:
        shutil.rmtree(work, True)
    return setup


def _targets(setup):
    lines = ["source %s %s" % (setup["source"]["commit"], setup["source"]["branch"])]
    for role in ROLES:
        pull = setup["pulls"][role]
        lines.append("merge %d %s" % (pull["number"], pull["stages"][-1]["head"]))
    return "\n".join(lines) + "\n"


def _attempts(count):
    return "%d earlier attempt%s stopped" % (count, "" if count == 1 else "s")


# The check directories whose setup stopped in this `live.py probe` run, with why: the other
# gate probes of the run fail with it instead of attempting again.
_STOPPED_THIS_RUN = {}


def _setup(context):
    """The setup's observations, read back once one attempt has completed; otherwise one fresh attempt per run.

    A stopped attempt fails every gate probe of its run and is recorded under `stopped`; the
    next run sets up afresh under new branch names, and `gate-trigger` names the stopped attempts.
    """
    setup = context.recall("gate_setup") or {}
    if "pulls" in setup:
        return setup
    if context.directory in _STOPPED_THIS_RUN:
        raise ProbeError(_STOPPED_THIS_RUN[context.directory])
    stopped = list(setup.get("stopped") or [])
    try:
        setup = _act(context)
    except Exception as error:  # Any failure leaves sandbox writes behind, so it is recorded.
        reason = str(error) if isinstance(error, ProbeError) else "%s: %s" % (type(error).__name__, error)
        context.remember("gate_setup", {"stopped": stopped + [reason]})
        _STOPPED_THIS_RUN[context.directory] = ("the gate probes' setup stopped: %s (%s); the next `live.py probe` run sets up afresh"
                                                % (reason, _attempts(len(stopped))))
        raise ProbeError(_STOPPED_THIS_RUN[context.directory])
    setup["stopped"] = stopped
    context.remember("gate_setup", setup)
    with open(os.path.join(context.directory, TARGETS), "w") as handle:
        handle.write(_targets(setup))
    return setup


# Step 2: habit's command.


ATTEMPTS_COMMAND = (
    "/bin/bash -c '"
    "u=https://github.com/{repository}.git; r={repository}; b={branch}; t=\"{targets}\"; "
    "if [ ! -f \"$t\" ]; then echo \"没有 ${{t}}：先运行一次不带 --post 的 live.py probe\"; exit 2; fi; "
    "d=\"$(mktemp -d)\"; trap \"rm -rf \\\"\\$d\\\"\" EXIT; "
    "after() {{ echo \"== after\"; git ls-remote \"$u\" \"refs/heads/$b\" \"refs/heads/$s\"; }}; "
    "attempt_exit() {{ echo \"exit=$1\"; if [ \"$1\" -eq 0 ]; then echo \"stop-after: $2\"; "
    "echo \"尝试已成功：$2；停止后续尝试，按产品问题停止，不要重跑命令\"; after; exit 3; fi; }}; "
    "never_reached() {{ echo \"never-reached: $2\"; echo \"准备失败，未到达 GitHub，不是拒绝\"; echo \"exit=$1\"; }}; "
    "while read -r k a z; do if [ \"$k\" = source ]; then c=$a; s=$z; fi; done < \"$t\"; "
    "echo \"== account\"; gh api user --jq .login; echo \"exit=$?\"; "
    "git clone -q --filter=blob:none \"$u\" \"$d/s\"; cloned=$?; "
    "echo \"== push $c to $b\"; if [ \"$cloned\" -eq 0 ]; then "
    "git -C \"$d/s\" push \"$u\" \"$c:refs/heads/$b\" 2>&1; attempt_exit $? \"push $c to $b\"; "
    "else never_reached \"$cloned\" \"push $c to $b\"; fi; "
    "echo \"== force-push $b\"; if [ \"$cloned\" -eq 0 ] && git -C \"$d/s\" checkout -q --detach \"origin/$b\" "
    "&& git -C \"$d/s\" commit -q --amend -m \"Live check: a force-push attempt\"; then "
    "git -C \"$d/s\" push --force \"$u\" \"HEAD:refs/heads/$b\" 2>&1; attempt_exit $? \"force-push $b\"; "
    "else never_reached $? \"force-push $b\"; fi; "
    "echo \"== force-push $s\"; if [ \"$cloned\" -eq 0 ] && git -C \"$d/s\" checkout -q --detach \"origin/$s\" "
    "&& git -C \"$d/s\" commit -q --amend -m \"Live check: a force-push attempt\"; then "
    "git -C \"$d/s\" push --force \"$u\" \"HEAD:refs/heads/$s\" 2>&1; attempt_exit $? \"force-push $s\"; "
    "else never_reached $? \"force-push $s\"; fi; "
    "while read -r k n h; do if [ \"$k\" = merge ]; then echo \"== merge $n at $h\"; "
    "gh api --method PUT \"repos/$r/pulls/$n/merge\" -f merge_method=squash -f sha=\"$h\" < /dev/null 2>&1; "
    "attempt_exit $? \"merge $n at $h\"; fi; done < \"$t\"; after'"
)


def attempts_commands(context):
    line = ATTEMPTS_COMMAND.format(repository=context.repository, branch=context.default_branch,
                                   targets=os.path.join(context.directory, TARGETS))
    return [(ATTEMPTS, "the agent's direct push, force-push and merges, as the agent account (gh), after the first "
             "`live.py probe` run, which opens the gate's probe PRs", line)]


def no_commands(context):
    return []


# Step 3: judging.


def attempts(text):
    """{header: (output, exit code or None)} from habit's command, in its order."""
    parts = _SECTION.split(text)
    found = {}
    for header, body in zip(parts[1::2], parts[2::2]):
        codes = _EXIT.findall(body)
        found[header.strip()] = (_EXIT.sub("", body).strip(), int(codes[-1]) if codes else None)
    return found


def _violations(output):
    """GitHub's rule-violation lines in a rejection: a push's `- …` lines or a merge's message."""
    lines = [line.split("remote:", 1)[-1].strip() for line in output.splitlines()]
    pushed = [line[2:].strip() for line in lines if line.startswith("- ")]
    if pushed:
        return pushed
    try:
        message = json.JSONDecoder().raw_decode(output.lstrip())[0].get("message", "")
    except (ValueError, AttributeError):
        message = ""
    return [line.strip() for line in message.splitlines()[1:] if line.strip()]


def _attempt(found, header):
    if header not in found:
        raise ProbeError("habit's gate_attempts output has no section `== %s`: rerun habit's command for it" % header)
    return found[header]


def _quote(violations):
    return "; ".join(violations) or "no rule named"


def _run_detail(run):
    return "run %s, event %s, %s, head %s, concluded %s" % (run["id"], run["event"], run["path"], (run["head_sha"] or "")[:12],
                                                          run["conclusion"])


def _from_actions(check_run, conclusion):
    return bool(check_run) and check_run["app_id"] == ACTIONS_APP and check_run["conclusion"] == conclusion


def _lands(run, head, conclusion):
    """Whether a run is the default branch's gate on head and its result landed there from GitHub Actions."""
    return (run["event"] == EVENT and run["path"] == WORKFLOW and run["head_sha"] == head and run["conclusion"] == conclusion
            and _from_actions(run["job"], conclusion) and _from_actions(run["posted"], conclusion))


def _landed_detail(run):
    job, posted = run["job"] or {}, run["posted"] or {}
    return "%s; the job's check run %s (%s) and the script's posted check run %s (%s, %r), app %s" % (
        _run_detail(run), job.get("id"), job.get("conclusion"), posted.get("id"), posted.get("conclusion"),
        posted.get("title"), posted.get("app_id"))


def _merge(found, pull):
    stage = pull["stages"][-1]
    return _attempt(found, "merge %d at %s" % (pull["number"], stage["head"]))


def _names_check(violations, name):
    return [line for line in violations if '"%s"' % name in line]


def trigger(context):
    setup = _setup(context)
    pull = setup["pulls"]["trigger"]
    opened = pull["stages"][0]
    run = opened["run"]
    results = [
        Result("the gate's run on the probe PR's head is %s from %s" % (EVENT, WORKFLOW),
               run["event"] == EVENT and run["path"] == WORKFLOW and run["head_sha"] == opened["head"],
               _run_detail(run) + ("; %s first: %s" % (_attempts(len(setup["stopped"])).replace("attempt", "setup attempt"),
                                                         " | ".join(setup["stopped"])) if setup.get("stopped") else "")),
        Result("the gate judged by the default branch's checkout", run["judged"] == [opened["head"], setup["default_head"]],
               "log: %s; the default branch was at %s" % (
                   "governance-gate on %s, judged by the default branch at %s" % tuple(run["judged"]) if run["judged"]
                   else "no judged line", setup["default_head"])),
        Result("its result lands on the head as %s check runs from GitHub Actions: the job's and the script's posted one"
               % CHECK, _lands(run, opened["head"], "success"), _landed_detail(run)),
    ]
    pinned = [c for c in setup["required"] if c.get("context") == CHECK]
    results.append(Result("the default branch requires %s from GitHub Actions only" % CHECK,
                          [c.get("integration_id") for c in pinned] == [ACTIONS_APP], json.dumps(setup["required"], sort_keys=True)))
    output, _ = _merge(context_attempts(context), pull)
    violations = _violations(output)
    results.append(Result("the agent's merge of the passing head names no required check, so the gate's result satisfies it",
                          bool(violations) and not [v for v in violations if "status check" in v], _quote(violations)))
    items, _ = report_items(context.input("owner_report"))
    status, detail = items.get("pull_request_target 事件策略", (None, "not reported"))
    if context.visibility == "public":
        results.append(Result("the owner report shows the event policy in place, for the gate's workflow only",
                              status in ("已就位", "已设置") and EVENT in detail and WORKFLOW in detail,
                              "%s：%s" % (status, detail) if status else detail))
        results.append(Result("the gate's %s run completed on the head under the policy and posted its result there" % EVENT,
                              run["conclusion"] == "success" and _from_actions(run["posted"], "success"),
                              "event %s, run %s, posted check run %s" % (run["event"], run["id"], (run["posted"] or {}).get("id"))))
    else:
        results.append(Result("the owner report skips the event policy on a private repository", status == "已跳过",
                              "%s：%s" % (status, detail) if status else detail))
    return results


def context_attempts(context):
    return attempts(context.input(ATTEMPTS))


def reruns(context):
    setup = _setup(context)
    edit, trigger_pull, failing = setup["pulls"]["edit"], setup["pulls"]["trigger"], setup["pulls"]["failing"]
    opened, fixed = edit["stages"][0], edit["stages"][-1]
    first, pushed = trigger_pull["stages"][0], trigger_pull["stages"][-1]
    results = [
        Result("a bad Risk line fails the gate on the head", _lands(opened["run"], opened["head"], "failure"),
               _landed_detail(opened["run"])),
        Result("a body edit that fixes the Risk line runs the gate again on the same head, and it passes",
               fixed["step"] == "body fixed" and fixed["head"] == opened["head"] and fixed["run"]["id"] != opened["run"]["id"]
               and (fixed["run"]["created_at"] or "") >= (fixed["at"] or "~") and _lands(fixed["run"], fixed["head"], "success"),
               "edited at %s; %s" % (fixed["at"], _landed_detail(fixed["run"]))),
        Result("a new push runs the gate again on the new head",
               pushed["step"] == "pushed" and pushed["head"] != first["head"] and (pushed["run"]["created_at"] or "") >= (pushed["at"] or "~")
               and _lands(pushed["run"], pushed["head"], "success"),
               "pushed %s at %s; %s" % (pushed["head"][:12], pushed["at"], _landed_detail(pushed["run"]))),
    ]
    found = context_attempts(context)
    control = _violations(_merge(found, failing)[0])
    results.append(Result("the agent's merge of a failing head names %s as failing" % CHECK,
                          bool([v for v in _names_check(control, CHECK) if "failing" in v]), _quote(control)))
    after = _violations(_merge(found, edit)[0])
    results.append(Result("after the body edit, the agent's merge names no required check: the earlier failure no longer counts",
                          bool(after) and not [v for v in after if "status check" in v], _quote(after)))
    return results


def source(context):
    setup = _setup(context)
    src = setup["source"]
    required = [c.get("context") for c in setup["required"]]
    unpinned = [c.get("context") for c in setup["required"] if c.get("integration_id") is None]
    ours = dict((s["context"], s["state"]) for s in reversed(src["statuses"]) if s["creator"] == AGENT)
    results = [
        Result("the source commit carries the agent's success status for every required check",
               bool(required) and all(ours.get(name) == "success" for name in required),
               "statuses by %s: %s" % (AGENT, json.dumps(ours, sort_keys=True))),
        Result("the source commit has no %s check run, so only the agent's status could satisfy it" % CHECK,
               src["gate_check_runs"] == 0, "%s check runs: %s" % (CHECK, src["gate_check_runs"])),
    ]
    output, _ = _attempt(context_attempts(context), "push %s to %s" % (src["commit"], context.default_branch))
    violations = _violations(output)
    gate = _names_check(violations, CHECK)
    results.append(Result("pushing it to %s, GitHub refuses the agent's %s status as not from the expected app" % (
        context.default_branch, CHECK), bool([v for v in gate if "not set by the expected GitHub app" in v]), _quote(violations)))
    named = [name for name in unpinned if _names_check(violations, name)]
    results.append(Result("the agent's status for a check with no app pinned counts, the control: GitHub names none of %s"
                          % ", ".join(unpinned or ["them"]), bool(unpinned) and not named,
                          "unpinned: %s; named: %s" % (", ".join(unpinned) or "none", ", ".join(named) or "none")))
    return results


def rulesets(context):
    setup = _setup(context)
    found = context_attempts(context)
    src, branch = setup["source"], context.default_branch
    account, _ = _attempt(found, "account")
    results = [Result("habit's attempts ran as the agent account", account.strip() == AGENT, "gh user: %s" % account.strip())]
    stopped = next((match.group(1) for output, _ in found.values() for match in [_STOP.search(output)] if match), None)

    def rejection(header, assertion, rejected):
        if header not in found and stopped:
            return Result(assertion, False, "skipped after %s went through; stop as for a product question" % stopped)
        output, code = _attempt(found, header)
        if any(line.startswith("never-reached: ") for line in output.splitlines()):
            return Result(assertion, False, "%s never reached GitHub: preparation failed, not a rejection" % header)
        if code == 0:
            return Result(assertion, False, "%s went through; stop as for a product question" % header)
        return Result(assertion, code is not None and rejected(output), _quote(_violations(output)))

    results.append(rejection("push %s to %s" % (src["commit"], branch), "the agent's direct push to %s is rejected" % branch,
                             lambda output: "[remote rejected]" in output and "GH013" in output))
    # The default branch's force-push meets Gate's rule; the source branch's meets History's alone.
    for ref in (branch, src["branch"]):
        results.append(rejection("force-push %s" % ref, "the agent's force-push to %s is rejected" % ref,
                                 lambda output: "Cannot force-push to this branch" in _violations(output)))
    for role in ROLES:
        pull = setup["pulls"][role]
        results.append(rejection("merge %d at %s" % (pull["number"], pull["stages"][-1]["head"]),
                                 "the agent's merge of probe PR #%d (%s) is rejected" % (pull["number"], role),
                                 lambda output: "Cannot update this protected ref." in _violations(output)))
    now = context.api("repos/%s/commits/%s" % (context.repository, branch))["sha"]
    results.append(Result("%s didn't move" % branch, now == setup["default_head"], "before %s, now %s" % (setup["default_head"], now)))
    ref = context.api("repos/%s/git/ref/heads/%s" % (context.repository, src["branch"]))
    sha = (ref.get("object") or {}).get("sha")
    results.append(Result("the force-pushed branch didn't move", sha == src["commit"], "before %s, now %s" % (src["commit"], sha)))
    merged = []
    for role in ROLES:
        number = setup["pulls"][role]["number"]
        if context.api("repos/%s/pulls/%d" % (context.repository, number)).get("merged"):
            merged.append("#%d" % number)
    results.append(Result("no probe PR merged", not merged, ", ".join(merged) or "none merged"))
    return results


PROBES = (
    Probe("gate-trigger", ("public", "private"), no_commands, trigger),
    Probe("gate-reruns", ("public", "private"), no_commands, reruns),
    Probe("gate-source", ("public", "private"), no_commands, source),
    Probe("gate-rulesets", ("public", "private"), attempts_commands, rulesets),
)
