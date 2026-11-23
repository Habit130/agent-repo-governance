"""Public-sandbox review ladder for v4 and v5 (#183, #187, #234).

Each probe opens its own PR, collects one completed Codex review, posts a sandbox-only
Merge summary, and hands habit a pinned merge. The high probe posts the agent-account
Reviewer status; the medium probe deliberately has none. The planted miss omits the
high Reviewer requirement from both status and summary. After habit merges, the probe
judges the real push run and its exact miss records. Automatic review counts; only habit
makes a printed request when needed. Agents never merge or run the owner script.
"""

import collections
import datetime
import os
import shutil
import tempfile
import time

from machinelib import AGENT, MAINTAINER
from probes import Probe, ProbeError, Result
from probes import merge_watch as watch
from probes.gate import _commit_file, _gh, _git

CODEX_REQUEST = "@codex review"
CODEX_WAIT_SECONDS = 1800
POLL_SECONDS = 15

Spec = collections.namedtuple("Spec", "name tier reviewer summary lacks")
SPECS = (
    Spec("merge-watch-v4-high", "high", True,
         "self-verification=clear, bot-1=clear(codex), reviewer=clear", None),
    Spec("merge-watch-v4-medium", "medium", False,
         "self-verification=clear, bot-1=clear(codex)", None),
    Spec("merge-watch-v4-miss", "high", False,
         "self-verification=clear, bot-1=clear(codex)", "reviewer, merge-summary"),
)


def _key(spec):
    return spec.name.replace("-", "_")


def _setup_key(spec):
    return _key(spec) + "_setup"


def target(spec, what):
    """The file a habit step or the merge reads its PR and head from: `<probe>_<what>.txt`."""
    return "%s_%s.txt" % (_key(spec), what)


# Setup, as the agent account.


def _open_pull(context, spec):
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    branch = "live/%s-%s-%s" % (spec.name, context.sandbox_pr, stamp)
    url = "https://github.com/%s.git" % context.repository
    work = tempfile.mkdtemp(prefix="live-merge-watch-v4-")
    try:
        clone = os.path.join(work, "sandbox")
        _git(["clone", "-q", url, clone], work)
        _git(["checkout", "-q", "-b", branch, "origin/%s" % context.default_branch], clone)
        head = _commit_file(clone, "%s-%s-%s.md" % (spec.name, context.sandbox_pr, stamp),
                            "Merge watch's version %d live check, %s, for %s.\n" % (context.version, spec.name, context.commit))
        _git(["push", "-q", url, "HEAD:refs/heads/%s" % branch], clone)
    finally:
        shutil.rmtree(work, True)
    body = ("A probe PR of Merge watch's version %d live check (`tests/live/probes/merge_watch_v4.py`).\n\n"
            "Risk: %s — one sandbox live-check file\n" % (context.version, spec.tier))
    opened = _gh(context, ["pr", "create", "--repo", context.repository, "--base", context.default_branch, "--head", branch,
                           "--title", "Live check: %s %s" % (spec.name, branch), "--body-file", "-"], stdin=body).strip()
    return {"pull": int(opened.rstrip("/").rsplit("/", 1)[-1]), "branch": branch, "head": head, "url": opened}


def _write_target(context, name, setup):
    with open(os.path.join(context.directory, name), "w") as handle:
        handle.write("%d %s %s\n" % (setup["pull"], setup["head"], setup.get("url", "")))


def _setup(context, spec):
    """The probe PR, its tier-specific `Reviewer` status; each happens once, so a rerun adds nothing."""
    setup = context.recall(_setup_key(spec))
    if setup is None:
        setup = _open_pull(context, spec)
        setup["fresh"] = True
        context.remember(_setup_key(spec), setup)
        _write_target(context, target(spec, "codex"), setup)
    if spec.reviewer and not setup.get("reviewer"):
        _gh(context, ["api", "--method", "POST", "repos/%s/statuses/%s" % (context.repository, setup["head"]),
                      "-f", "state=success", "-f", "context=Reviewer",
                      "-f", "description=the agent's status, Merge watch's live check"])
        setup["reviewer"] = True
        context.remember(_setup_key(spec), setup)
    return setup


# The facts, as the agent account reads them.


def _comments(context, setup):
    return context.api("repos/%s/issues/%d/comments?per_page=100" % (context.repository, setup["pull"])) or []


def _summary_header(spec, head, version):
    title_head = head if version >= 5 else head[:7]
    lines = [f"## Merge summary: {spec.tier} at {title_head}", "Required reviews: " + spec.summary]
    if version >= 5 and spec.tier == "high":
        lines.append("Security review applies: no")  # Each probe changes one sandbox text file.
    return lines


def _summary(comments, header):
    for comment in reversed(comments):
        lines = watch._lines(comment)
        if watch._login(comment).lower() == AGENT.lower() and lines[0] == header[0]:
            actual = lines[:len(header)]
            return "; ".join(actual) if actual == header else None
    return None


def _fact_results(context, spec, setup):
    head, comments = setup["head"], _comments(context, setup)
    facts, results = [], []
    if spec.reviewer:
        facts.append(("a successful Reviewer status from the agent account", watch._reviewer(context, head)))
    else:
        statuses = context.api("repos/%s/commits/%s/statuses?per_page=100" % (context.repository, head)) or []
        present = any(status.get("context") == "Reviewer" for status in statuses)
        results.append(Result("no Reviewer status is on the probe head", not present, "present" if present else "absent"))
    facts.append(("a completed review by codex", watch._codex(comments, head)))
    header = _summary_header(spec, head, context.version)
    facts.append((f"the probe's version {context.version} Merge summary", _summary(comments, header)))
    return results + [Result("%s is on the head %s" % (name, head[:12]), detail is not None, detail or "absent") for name, detail in facts]


# Waiting, then the summary.


def _await(context, setup):
    wait = CODEX_WAIT_SECONDS
    deadline = time.time() + wait
    while not watch._codex(_comments(context, setup), setup["head"]):
        if time.time() > deadline:
            raise ProbeError("no completed review by %s on %s within %d seconds: an environment blocker; habit checks the "
                             "request and the bot's access, then runs `live.py probe` again" % ("codex", setup["head"][:12], wait))
        time.sleep(POLL_SECONDS)


def _collect(context, spec, setup):
    """Everything but the merge: the bot's review and the summary, and the merge target once all read."""
    head = setup["head"]
    if setup.pop("fresh", False):
        context.remember(_setup_key(spec), setup)
        return [Result("habit's steps for %s are done" % spec.name, False,
                       "not yet: habit runs the printed steps for PR #%d at %s, then run `live.py probe` again"
                       % (setup["pull"], head[:12]))]
    comments = _comments(context, setup)
    if not watch._codex(comments, head) and not [c for c in comments if watch._login(c).lower() == MAINTAINER.lower()
                                     and CODEX_REQUEST in (c.get("body") or "")]:
        return [Result("habit's Codex review bot request is on the probe PR", False,
                       "not yet: habit runs the printed request for PR #%d, then run `live.py probe` again" % setup["pull"])]
    _await(context, setup)
    header = _summary_header(spec, head, context.version)
    if _summary(_comments(context, setup), header) is None:
        _gh(context, ["pr", "comment", str(setup["pull"]), "--repo", context.repository, "--body-file", "-"],
            stdin="%s\n\n%sMerge watch's live check posted this as probe data on a sandbox PR.\n"
            % ("\n".join(header),
               "No session independent of the Builder looked at this change; the Codex review bot completed.\n\n"
               if spec.tier == "medium" else ""))
    results = _fact_results(context, spec, setup)
    ready = all(result.passed for result in results)
    if ready:
        _write_target(context, target(spec, "merge"), setup)
    return results + [Result("every fact read, so the PR is ready for habit's merge", ready,
                             "READY: habit runs the printed pinned merge of PR #%d" % setup["pull"] if ready else "not ready: don't merge")]


def _missing_review(spec, setup):
    title = "Miss: process miss, missing-review in #%d" % setup["pull"]
    observed = "Merged head %s, declared %s, lacks: %s." % (setup["head"], spec.tier, spec.lacks)
    return title, observed


def _judge(context, spec, setup, pull):
    commit = pull.get("merge_commit_sha")
    results = [Result("habit merged the PR at the ready head", (pull.get("head") or {}).get("sha") == setup["head"],
                      "PR #%d merged as %s, head %s" % (setup["pull"], commit, (pull.get("head") or {}).get("sha")))]
    run, outcomes = watch._await_run(context, commit)
    results.append(Result("Merge watch's own push run on the squash commit succeeded", run.get("conclusion") == "success",
                          watch._run_detail(run, outcomes)))
    named = [issue for issue in watch._records(context) if (issue.get("title") or "").endswith(" in #%d" % setup["pull"])]
    if spec.lacks is None:
        results.append(Result("the run read every fact: no missing review, no unreadable fact, no note",
                              outcomes == ["No miss in this push event."], " / ".join(outcomes)))
        results.append(Result("no miss record names the PR", not named, ", ".join(i.get("html_url") or "" for i in named) or "none"))
        return results
    title, observed = _missing_review(spec, setup)
    results.append(Result("the run reports exactly the one missing-review record, lacking %s" % spec.lacks,
                          outcomes == ["MISS %s. %s" % (title, observed)], " / ".join(outcomes)))
    expected = ["Merged PR: #%d" % setup["pull"], "Kind: process miss", "Category: missing-review", "Observed: " + observed,
                "Found by: Merge watch", "Bug issue: none", ""]
    found = [issue for issue in named if issue.get("title") == title and watch._lines(issue) == expected
             and watch._login(issue) == watch.RECORD_AUTHOR
             and [label.get("name") for label in issue.get("labels") or []] == ["miss"]
             and (issue.get("created_at") or "") >= (pull.get("merged_at") or "~")]
    results.append(Result("GitHub holds that record, opened by Merge watch's token with the six field lines",
                          len(found) == 1 and len(named) == 1, ", ".join(i.get("html_url") or "" for i in named) or "no record"))
    return results


def runner(spec):
    def run(context):
        setup = _setup(context, spec)
        pull = context.api("repos/%s/pulls/%d" % (context.repository, setup["pull"]))
        if not pull.get("merged"):
            return _collect(context, spec, setup) + [
                Result("habit merged the PR at the ready head", False, "PR #%d isn't merged yet" % setup["pull"])]
        return _fact_results(context, spec, setup) + _judge(context, spec, setup, pull)
    return run


def commands(spec):
    """habit's steps for one probe, in order. `ghm` is a shell function, so each stays at the top level of habit's shell."""
    def listed(context):
        line = 'if [ -f "{target}" ]; then read -r n h u < "{target}"; {action}; else echo "没有 {target}：{wait}"; fi'
        first = "先运行一次 live.py probe"
        steps = []
        path = os.path.join(context.directory, target(spec, "codex"))
        steps.append((None, "Codex request only if no automatic review completed on this head; after the first probe run",
                      line.format(target=path, wait=first, action='ghm pr comment "$n" --repo %s --body "%s"'
                                  % (context.repository, CODEX_REQUEST))))
        path = os.path.join(context.directory, target(spec, "merge"))
        steps.append((None, "Pinned merge of the probe PR, once a `live.py probe` run reports READY",
                      line.format(target=path, wait="先等 live.py probe 报告 READY",
                                  action='ghm pr merge "$n" --repo %s --admin --squash --match-head-commit "$h"'
                                  % context.repository)))
        return steps
    return listed


PROBES = tuple(Probe(spec.name, ("public",), commands(spec), runner(spec)) for spec in SPECS)
NAMES = tuple(spec.name for spec in SPECS)
