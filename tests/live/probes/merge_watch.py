"""Merge watch's probes (#41 §9, seam 4): a head with every review, and a planted miss.

`merge-watch-miss` needs no setup: the render PR is declared high and nothing reviews it, so
its merge is the planted miss, and the probe judges the record Merge watch opened for it.

`merge-watch-clean` opens one probe PR, declared high, and takes four steps:

1. `live.py probe`, after habit's render merge and owner-script run, opens the PR from a
   `live/merge-watch-<sandbox PR>-<UTC stamp>` branch, with one file under `live-checks/`,
   requests Bugbot, posts the agent's `Reviewer` status and writes `merge_watch_codex.txt`,
   the target of habit's Codex request. It returns without waiting.
2. habit runs the printed Codex review bot request. It refuses until that target exists.
3. `live.py probe` waits for Bugbot's check, retrying the request once, and for the Codex
   marker. It then posts the Merge summary, reads all four facts back from the head and
   writes `merge_watch_merge.txt`, the target of habit's pinned merge, which refuses until
   that target exists. A run that stops on a wait fails naming what came back, and sends no
   third request: a bot that doesn't answer is an environment blocker, never a reduction.
4. After habit's merge, `live.py probe --post` judges from Merge watch's own push run on the
   squash commit. Its token read the facts: a failed read counts as absent, so a run that
   records no miss and has no `UNREADABLE` line has read all four. The agent's reading only
   gates the merge.

The status and the summary are this probe's data, posted as the agent account in the sandbox
only. Only the Bugbot request writes a review trigger from the agent account. The probes never
merge. Everything reads the repository and default branch from the context, so a private
sandbox takes these probes unchanged.
"""

import datetime
import json
import os
import re
import shutil
import tempfile
import time

from machinelib import AGENT, MAINTAINER
from probes import Probe, ProbeError, Result
from probes.gate import _commit_file, _gh, _git

WORKFLOW = ".github/workflows/merge-watch.yml"
SETUP = "merge_watch_setup"
CODEX_TARGET = "merge_watch_codex.txt"
MERGE_TARGET = "merge_watch_merge.txt"
BUGBOT_REQUEST = "@cursor review"
CODEX_REQUEST = "@codex review"
BUGBOT_REQUESTS = 2  # One request and one retry.
# Measured on PRs #88, #90 and #92: Bugbot took 5 to 11 minutes, the Codex review bot 2 to 4.
BUGBOT_WAIT_SECONDS = 900
CODEX_WAIT_SECONDS = 600
RUN_WAIT_SECONDS = 600
POLL_SECONDS = 15
BUGBOT_APP = "cursor"
BUGBOT_COMPLETED = ("success", "neutral", "failure")
CODEX_LOGIN = "chatgpt-codex-connector[bot]"
RISK = "Risk: high — one file under live-checks, written by Merge watch's live check"
REVIEWS = "Required reviews: self-verification=clear, bugbot=clear, codex=clear, reviewer=clear"
RECORD_AUTHOR = "github-actions[bot]"
FIELDS = ("Merged PR", "Kind", "Category", "Observed", "Found by", "Bug issue")
_MARKER = re.compile(r"<!-- codex-review-state:v1 (\{.*?\}) -->", re.S)
_OUTCOME = re.compile(r"(?m)^\S+\s(No miss in this \w+ event\.|MISS .*?|UNREADABLE .*?|FAIL opening .*?)\s*$")
_OBSERVED = re.compile(r"^Observed: Merged head ([0-9a-f]{40}), declared high, lacks: ([a-z-]+(?:, [a-z-]+)*)\.$")


def _login(item):
    return (item.get("user") or item.get("creator") or {}).get("login") or ""


# Setup, as the agent account.


def _open_pull(context):
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    branch = "live/merge-watch-%s-%s" % (context.sandbox_pr, stamp)
    url = "https://github.com/%s.git" % context.repository
    work = tempfile.mkdtemp(prefix="live-merge-watch-")
    try:
        clone = os.path.join(work, "sandbox")
        _git(["clone", "-q", url, clone], work)
        _git(["checkout", "-q", "-b", branch, "origin/%s" % context.default_branch], clone)
        head = _commit_file(clone, "merge-watch-%s-%s.md" % (context.sandbox_pr, stamp),
                            "Merge watch's live check, the clean probe, for %s.\n" % context.commit)
        _git(["push", "-q", url, "HEAD:refs/heads/%s" % branch], clone)
    finally:
        shutil.rmtree(work, True)
    body = "A probe PR of Merge watch's live check (`tests/live/probes/merge_watch.py`).\n\n%s\n" % RISK
    opened = _gh(context, ["pr", "create", "--repo", context.repository, "--base", context.default_branch, "--head", branch,
                           "--title", "Live check: Merge watch probe %s" % branch, "--body-file", "-"], stdin=body).strip()
    return {"pull": int(opened.rstrip("/").rsplit("/", 1)[-1]), "branch": branch, "head": head}


def _request_bugbot(context, setup):
    url = _gh(context, ["pr", "comment", str(setup["pull"]), "--repo", context.repository, "--body", BUGBOT_REQUEST]).strip()
    setup.setdefault("bugbot_requests", []).append({"url": url, "at": time.time()})
    context.remember(SETUP, setup)


def _write_target(context, name, setup):
    with open(os.path.join(context.directory, name), "w") as handle:
        handle.write("%d %s\n" % (setup["pull"], setup["head"]))


def _setup(context):
    """The probe PR, its Bugbot request and its `Reviewer` status; each happens once, so a rerun adds nothing."""
    setup = context.recall(SETUP)
    if setup is None:
        setup = _open_pull(context)
        context.remember(SETUP, setup)
        _write_target(context, CODEX_TARGET, setup)
    if not setup.get("bugbot_requests"):
        _request_bugbot(context, setup)
    if not setup.get("reviewer"):
        _gh(context, ["api", "--method", "POST", "repos/%s/statuses/%s" % (context.repository, setup["head"]),
                      "-f", "state=success", "-f", "context=Reviewer", "-f", "description=the agent's status, Merge watch's live check"])
        setup["reviewer"] = True
        context.remember(SETUP, setup)
    return setup


# The four facts, as the agent account reads them.


def _comments(context, setup):
    return context.api("repos/%s/issues/%d/comments?per_page=100" % (context.repository, setup["pull"])) or []


def _bugbot(context, head):
    """Bugbot's completed check on the head, as a detail; None without one."""
    runs = (context.api("repos/%s/commits/%s/check-runs?check_name=Cursor%%20Bugbot&filter=all&per_page=100"
                        % (context.repository, head)) or {}).get("check_runs") or []
    for run in runs:
        if run.get("name") == "Cursor Bugbot" and (run.get("app") or {}).get("slug") == BUGBOT_APP \
                and run.get("status") == "completed" and run.get("conclusion") in BUGBOT_COMPLETED:
            return "Cursor Bugbot from %s, %s" % (BUGBOT_APP, run["conclusion"])
    return None


def _codex(comments, head):
    for comment in comments:
        if _login(comment) != CODEX_LOGIN:
            continue
        for match in _MARKER.finditer(comment.get("body") or ""):
            try:
                review = json.loads(match.group(1)).get("code_review") or {}
            except ValueError:
                continue
            if review.get("commit_sha") == head and review.get("status") == "completed":
                return "marker from %s, completed on %s" % (CODEX_LOGIN, head[:12])
    return None


def _reviewer(context, head):
    statuses = context.api("repos/%s/commits/%s/statuses?per_page=100" % (context.repository, head)) or []
    for status in statuses:
        if status.get("context") == "Reviewer" and _login(status).lower() == AGENT.lower():
            return "Reviewer success by %s" % AGENT if status.get("state") == "success" else None
    return None


def _title(head):
    return "## Merge summary: high at %s" % head[:7]


def _summary(comments, head):
    for comment in reversed(comments):
        lines = (comment.get("body") or "").split("\n")
        if _login(comment).lower() == AGENT.lower() and lines[0] == _title(head):
            return "%s; %s" % (lines[0], lines[1]) if lines[1:2] == [REVIEWS] else None
    return None


def _fact_results(context, setup):
    head, comments = setup["head"], _comments(context, setup)
    facts = (
        ("a completed Cursor Bugbot check", _bugbot(context, head)),
        ("a successful Reviewer status from the agent account", _reviewer(context, head)),
        ("a completed Codex marker", _codex(comments, head)),
        ("a Merge summary naming the head, every kind clear", _summary(comments, head)),
    )
    return [Result("%s is on the head %s" % (name, head[:12]), detail is not None, detail or "absent") for name, detail in facts]


# Waiting for the bots, then the summary.


def _await_bugbot(context, setup):
    while not _bugbot(context, setup["head"]):
        requests = setup["bugbot_requests"]
        if time.time() <= requests[-1]["at"] + BUGBOT_WAIT_SECONDS:
            time.sleep(POLL_SECONDS)
        elif len(requests) < BUGBOT_REQUESTS:
            _request_bugbot(context, setup)
        else:
            raise ProbeError("no completed Cursor Bugbot check on %s after %d requests (%s), each given %d seconds: an environment "
                             "blocker; habit checks Cursor's repository access" % (
                                 setup["head"][:12], len(requests), ", ".join(r["url"] for r in requests), BUGBOT_WAIT_SECONDS))


def _await_codex(context, setup):
    deadline = time.time() + CODEX_WAIT_SECONDS
    while True:
        comments = _comments(context, setup)
        if _codex(comments, setup["head"]):
            return
        if time.time() > deadline:
            said = [c.get("body") or "" for c in comments if _login(c) == CODEX_LOGIN]
            raise ProbeError("no completed Codex marker for %s within %d seconds: an environment blocker; the bot's last comment: %s" % (
                setup["head"][:12], CODEX_WAIT_SECONDS, " ".join(said[-1].split())[:300] if said else "none"))
        time.sleep(POLL_SECONDS)


def _collect(context, setup):
    """Everything but the merge: the bots' answers, the summary, and habit's merge target once all four read."""
    head = setup["head"]
    if not [c for c in _comments(context, setup) if _login(c).lower() == MAINTAINER.lower() and CODEX_REQUEST in (c.get("body") or "")]:
        return [Result("habit's Codex review bot request is on the probe PR", False,
                       "not yet: habit runs the printed Codex command, then run `live.py probe` again; PR #%d at %s" % (setup["pull"], head[:12]))]
    _await_bugbot(context, setup)
    _await_codex(context, setup)
    if _summary(_comments(context, setup), head) is None:
        _gh(context, ["pr", "comment", str(setup["pull"]), "--repo", context.repository, "--body-file", "-"],
            stdin="%s\n%s\n\nMerge watch's live check posted this as probe data on a sandbox PR.\n" % (_title(head), REVIEWS))
    results = _fact_results(context, setup)
    ready = all(result.passed for result in results)
    if ready:
        _write_target(context, MERGE_TARGET, setup)
    return results + [Result("all four facts read, so the PR is ready for habit's merge", ready,
                             "READY: habit runs the printed pinned merge of PR #%d" % setup["pull"] if ready else "not ready: don't merge")]


# Merge watch's own run.


def _outcomes(context, run):
    jobs = (context.api("repos/%s/actions/runs/%s/jobs" % (context.repository, run["id"])) or {}).get("jobs") or []
    job = next((j for j in jobs if j.get("name") == "merge-watch"), None)
    if job is None:
        return []
    code, log, _ = context.gh(["api", "--allow-escape-sequences", "repos/%s/actions/jobs/%s/logs" % (context.repository, job["id"])])
    return _OUTCOME.findall(log) if code == 0 else []


def _await_run(context, commit):
    """Merge watch's completed push run on commit and its log's outcome lines; ProbeError after RUN_WAIT_SECONDS."""
    deadline = time.time() + RUN_WAIT_SECONDS
    last = "no run yet"
    while True:
        try:
            runs = (context.api("repos/%s/actions/runs?head_sha=%s&per_page=100" % (context.repository, commit))
                    or {}).get("workflow_runs") or []
            done = sorted((r for r in runs if r.get("path") == WORKFLOW and r.get("event") == "push" and r.get("status") == "completed"),
                          key=lambda r: r["id"])
            if done:
                outcomes = _outcomes(context, done[0])
                if outcomes:
                    return done[0], outcomes
                last = "run %s's log has no outcome line" % done[0]["id"]
        except ProbeError as error:
            # A read that fails while waiting is retried until the deadline, which names it.
            last = str(error)
        if time.time() > deadline:
            raise ProbeError("no completed merge-watch push run on %s with an outcome line within %d seconds; last: %s" % (
                commit[:12], RUN_WAIT_SECONDS, last))
        time.sleep(POLL_SECONDS)


def _run_detail(run, outcomes):
    return "run %s, event %s, %s, concluded %s; log: %s" % (run["id"], run.get("event"), run.get("path"), run.get("conclusion"),
                                                            " / ".join(outcomes))


def _records(context):
    issues = context.api("repos/%s/issues?labels=miss&state=all&per_page=100" % context.repository) or []
    return [issue for issue in issues if "pull_request" not in issue]


def clean(context):
    setup = _setup(context)
    pull = context.api("repos/%s/pulls/%d" % (context.repository, setup["pull"]))
    if not pull.get("merged"):
        return _collect(context, setup) + [Result("habit merged the PR at the ready head", False, "PR #%d isn't merged yet" % setup["pull"])]
    merged_head, commit = (pull.get("head") or {}).get("sha"), pull.get("merge_commit_sha")
    results = _fact_results(context, setup)
    results.append(Result("habit merged the PR at the ready head", merged_head == setup["head"],
                          "PR #%d merged as %s, head %s" % (setup["pull"], commit, merged_head)))
    run, outcomes = _await_run(context, commit)
    results.append(Result("Merge watch's own push run on the squash commit succeeded", run.get("conclusion") == "success",
                          _run_detail(run, outcomes)))
    results.append(Result("its token read all four: the run records no missing review and no unreadable fact",
                          outcomes == ["No miss in this push event."], " / ".join(outcomes)))
    named = [issue.get("html_url") for issue in _records(context) if (issue.get("title") or "").endswith(" in #%d" % setup["pull"])]
    results.append(Result("no miss record names the PR", not named, ", ".join(named) or "none"))
    return results


def miss(context):
    pull = context.api("repos/%s/pulls/%d" % (context.repository, context.sandbox_pr))
    head = (pull.get("head") or {}).get("sha")
    run, outcomes = _await_run(context, pull.get("merge_commit_sha"))
    title = "Miss: process miss, missing-review in #%d" % context.sandbox_pr
    results = [Result("Merge watch's own push run on the render PR's squash commit reports the miss",
                      run.get("conclusion") == "success" and any(line.startswith("MISS %s. " % title) for line in outcomes),
                      _run_detail(run, outcomes))]
    observed_prefix = "Observed: Merged head %s," % head
    found = [issue for issue in _records(context) if issue.get("title") == title
             and any(line.startswith(observed_prefix) for line in (issue.get("body") or "").split("\n"))]
    if not found:
        return results + [Result("a miss record names the render PR's head", False, "no miss record titled %r names %s" % (title, head))]
    issue, lines = found[0], found[0]["body"].split("\n")
    labels = [label.get("name") for label in issue.get("labels") or []]
    observed = _OBSERVED.match(lines[3]) if len(lines) > 3 else None
    lacks = set(observed.group(2).split(", ")) if observed else set()
    return results + [
        Result("Merge watch's token opened the record during this check",
               _login(issue) == RECORD_AUTHOR and (issue.get("created_at") or "") >= (pull.get("merged_at") or "~"),
               "%s by %s at %s; the merge was at %s" % (issue.get("html_url"), _login(issue), issue.get("created_at"), pull.get("merged_at"))),
        Result("the record's only label is miss", labels == ["miss"], ", ".join(labels)),
        Result("the body opens with the six field lines, in order",
               [line.split(": ", 1)[0] for line in lines[:6]] == list(FIELDS)
               and lines[:3] == ["Merged PR: #%d" % context.sandbox_pr, "Kind: process miss", "Category: missing-review"]
               and lines[4:6] == ["Found by: Merge watch", "Bug issue: none"], " / ".join(lines[:6])),
        Result("the record names the head and lacks every review the probes didn't post",
               observed is not None and {"codex", "reviewer", "merge-summary"} <= lacks, lines[3] if len(lines) > 3 else "no Observed line"),
    ]


def habits_commands(context):
    """habit's two one-liners. `ghm` is a shell function, so both stay at the top level of habit's shell."""
    line = 'if [ -f "{target}" ]; then read -r n h < "{target}"; {action}; else echo "没有 {target}：{wait}"; fi'
    return [
        (None, "Codex review bot request, after the first `live.py probe` run opens the probe PR",
         line.format(target=os.path.join(context.directory, CODEX_TARGET), wait="先运行一次 live.py probe",
                     action='ghm pr comment "$n" --repo %s --body "%s"' % (context.repository, CODEX_REQUEST))),
        (None, "Pinned merge, of the probe PR. Don't merge until a `live.py probe` run reports ready: a new head resets all four facts",
         line.format(target=os.path.join(context.directory, MERGE_TARGET), wait="先等 live.py probe 报告 READY",
                     action='ghm pr merge "$n" --repo %s --admin --squash --match-head-commit "$h"' % context.repository)),
    ]


def no_commands(context):
    return []


PROBES = (
    Probe("merge-watch-clean", ("public", "private"), habits_commands, clean),
    Probe("merge-watch-miss", ("public", "private"), no_commands, miss),
)
