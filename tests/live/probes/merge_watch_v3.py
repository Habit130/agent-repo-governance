"""Merge watch's version 3 probes (#148): bot slots filled, waived and missed, each on its own probe PR.

The sandbox is rendered from version 3 with the Codex review bot and Copilot enabled, in that
order (`live.py`, `V3_REVIEW_BOTS`). Each probe opens one PR declared high, and takes the same
four steps as `merge_watch.py`'s clean probe:

1. `live.py probe` opens the PR from a `live/<probe>-<sandbox PR>-<UTC stamp>` branch, posts
   the agent's `Reviewer` status, posts any agent-account comment the probe plants, and writes
   the targets of habit's steps. It returns without waiting.
2. habit runs the printed steps: each review bot request (the Codex review bot by command,
   Copilot in the browser at Lite), and the waived probe's waiver comment.
3. `live.py probe` waits for each requested bot's completed review on the head, posts the
   version 3 Merge summary, reads every fact back and writes the target of habit's pinned
   merge. A bot that doesn't answer within its wait fails the probe as an environment
   blocker, never a pass, and nothing is requested again.
4. After habit's merge, `live.py probe` judges Merge watch's own push run on the squash
   commit and the miss records:
   - `merge-watch-v3-clean`: both bots completed, each named in its slot: no miss;
   - `merge-watch-v3-waived`: `bot-1` waived by habit's own comment on the head, Copilot in
     `bot-2`: no miss;
   - `merge-watch-v3-miss`: the Codex review bot in `bot-1`; `bot-2` "waived" on the strength
     of an agent-account comment, and the summary leaves the Reviewer out: one
     `missing-review` record lacking `bot-2` and `merge-summary`.

The status, the summaries and the agent-account waiver are this probe's data, posted as the
agent account in the public sandbox only. No agent writes a review trigger here: habit makes
every request. The probes never merge.
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

RISK = "Risk: high — one file under live-checks, written by Merge watch's version 3 live check"
CODEX_REQUEST = "@codex review"
COPILOT_LOGIN = "copilot-pull-request-reviewer[bot]"
COPILOT_CHECK = "copilot-pull-request-reviewer"
# The bots' waits (docs/agents/review.md, Review bots): no answer within one is an environment blocker.
CODEX_WAIT_SECONDS = 1800
COPILOT_WAIT_SECONDS = 900
POLL_SECONDS = 15
HABIT_WAIVER_REASON = "Merge watch's live check: the Codex review bot is left unrequested on purpose"
AGENT_WAIVER_REASON = "Merge watch's live check: an agent-account waiver, which approves nothing"

Spec = collections.namedtuple("Spec", "name bots summary habit_waiver agent_waiver lacks")

SPECS = (
    Spec("merge-watch-v3-clean", ("codex", "copilot"),
         "self-verification=clear, bot-1=clear(codex), bot-2=clear(copilot), reviewer=clear", None, None, None),
    Spec("merge-watch-v3-waived", ("copilot",),
         "self-verification=clear, bot-1=waived(codex), bot-2=clear(copilot), reviewer=clear", "bot-1", None, None),
    Spec("merge-watch-v3-miss", ("codex",),
         "self-verification=clear, bot-1=clear(codex), bot-2=waived(copilot)", None, "bot-2", "bot-2, merge-summary"),
)


def _key(spec):
    return spec.name.replace("-", "_")


def _setup_key(spec):
    return _key(spec) + "_setup"


def target(spec, what):
    """The file a habit step or the merge reads its PR and head from: `<probe>_<what>.txt`."""
    return "%s_%s.txt" % (_key(spec), what)


def waiver_line(item, head, reason):
    return "Waiver: %s at %s — %s" % (item, head, reason)


# Setup, as the agent account.


def _open_pull(context, spec):
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    branch = "live/%s-%s-%s" % (spec.name, context.sandbox_pr, stamp)
    url = "https://github.com/%s.git" % context.repository
    work = tempfile.mkdtemp(prefix="live-merge-watch-v3-")
    try:
        clone = os.path.join(work, "sandbox")
        _git(["clone", "-q", url, clone], work)
        _git(["checkout", "-q", "-b", branch, "origin/%s" % context.default_branch], clone)
        head = _commit_file(clone, "%s-%s-%s.md" % (spec.name, context.sandbox_pr, stamp),
                            "Merge watch's version 3 live check, %s, for %s.\n" % (spec.name, context.commit))
        _git(["push", "-q", url, "HEAD:refs/heads/%s" % branch], clone)
    finally:
        shutil.rmtree(work, True)
    body = "A probe PR of Merge watch's version 3 live check (`tests/live/probes/merge_watch_v3.py`).\n\n%s\n" % RISK
    opened = _gh(context, ["pr", "create", "--repo", context.repository, "--base", context.default_branch, "--head", branch,
                           "--title", "Live check: %s %s" % (spec.name, branch), "--body-file", "-"], stdin=body).strip()
    return {"pull": int(opened.rstrip("/").rsplit("/", 1)[-1]), "branch": branch, "head": head, "url": opened}


def _write_target(context, name, setup):
    with open(os.path.join(context.directory, name), "w") as handle:
        handle.write("%d %s %s\n" % (setup["pull"], setup["head"], setup.get("url", "")))


def _setup(context, spec):
    """The probe PR, its `Reviewer` status and any planted comment; each happens once, so a rerun adds nothing."""
    setup = context.recall(_setup_key(spec))
    if setup is None:
        setup = _open_pull(context, spec)
        setup["fresh"] = True
        context.remember(_setup_key(spec), setup)
        for bot in spec.bots:
            _write_target(context, target(spec, bot), setup)
        if spec.habit_waiver:
            _write_target(context, target(spec, "waiver"), setup)
    if not setup.get("reviewer"):
        _gh(context, ["api", "--method", "POST", "repos/%s/statuses/%s" % (context.repository, setup["head"]),
                      "-f", "state=success", "-f", "context=Reviewer",
                      "-f", "description=the agent's status, Merge watch's version 3 live check"])
        setup["reviewer"] = True
        context.remember(_setup_key(spec), setup)
    if spec.agent_waiver and not setup.get("agent_waiver"):
        _gh(context, ["pr", "comment", str(setup["pull"]), "--repo", context.repository, "--body-file", "-"],
            stdin=waiver_line(spec.agent_waiver, setup["head"], AGENT_WAIVER_REASON) + "\n")
        setup["agent_waiver"] = True
        context.remember(_setup_key(spec), setup)
    return setup


# The facts, as the agent account reads them.


def _comments(context, setup):
    return context.api("repos/%s/issues/%d/comments?per_page=100" % (context.repository, setup["pull"])) or []


def _copilot(context, setup):
    """Copilot's review object on the head beside its completed check run there, as a detail; None without both."""
    head = setup["head"]
    reviews = context.api("repos/%s/pulls/%d/reviews?per_page=100" % (context.repository, setup["pull"])) or []
    review = next((r for r in reviews if watch._login(r) == COPILOT_LOGIN and r.get("is_copilot_code_review") is True
                   and r.get("commit_id") == head), None)
    runs = (context.api("repos/%s/commits/%s/check-runs?check_name=%s&filter=all&per_page=100"
                        % (context.repository, head, COPILOT_CHECK)) or {}).get("check_runs") or []
    run = next((r for r in runs if r.get("name") == COPILOT_CHECK and r.get("status") == "completed"
                and r.get("conclusion") == "success"), None)
    if review is None or run is None:
        return None
    return "review %s by %s on %s, check run %s success" % (review.get("id"), COPILOT_LOGIN, head[:12], COPILOT_CHECK)


def _bot(context, setup, bot, comments=None):
    if bot == "codex":
        return watch._codex(comments if comments is not None else _comments(context, setup), setup["head"])
    return _copilot(context, setup)


def _habit_waiver(spec, setup, comments):
    expected = waiver_line(spec.habit_waiver, setup["head"], HABIT_WAIVER_REASON)
    for comment in comments:
        if watch._login(comment).lower() == MAINTAINER.lower() and watch._lines(comment)[0].rstrip() == expected:
            return "%s's comment: %s" % (MAINTAINER, expected)
    return None


def _title(head):
    return "## Merge summary: high at %s" % head[:7]


def _summary(spec, setup, comments):
    for comment in reversed(comments):
        lines = watch._lines(comment)
        if watch._login(comment).lower() == AGENT.lower() and lines[0] == _title(setup["head"]):
            line = "Required reviews: " + spec.summary
            return "%s; %s" % (lines[0], lines[1]) if lines[1:2] == [line] else None
    return None


def _fact_results(context, spec, setup):
    head, comments = setup["head"], _comments(context, setup)
    facts = [("a successful Reviewer status from the agent account", watch._reviewer(context, head))]
    facts += [("a completed review by %s" % bot, _bot(context, setup, bot, comments)) for bot in spec.bots]
    if spec.habit_waiver:
        facts.append(("habit's waiver of %s for this head" % spec.habit_waiver, _habit_waiver(spec, setup, comments)))
    facts.append(("the probe's version 3 Merge summary naming the head", _summary(spec, setup, comments)))
    return [Result("%s is on the head %s" % (name, head[:12]), detail is not None, detail or "absent") for name, detail in facts]


# Waiting, then the summary.


def _await(context, setup, bot):
    wait = CODEX_WAIT_SECONDS if bot == "codex" else COPILOT_WAIT_SECONDS
    deadline = time.time() + wait
    while not _bot(context, setup, bot):
        if time.time() > deadline:
            raise ProbeError("no completed review by %s on %s within %d seconds: an environment blocker; habit checks the "
                             "request and the bot's access, then runs `live.py probe` again" % (bot, setup["head"][:12], wait))
        time.sleep(POLL_SECONDS)


def _collect(context, spec, setup):
    """Everything but the merge: the bots' reviews, habit's waiver, the summary, and the merge target once all read."""
    head = setup["head"]
    if setup.pop("fresh", False):
        context.remember(_setup_key(spec), setup)
        return [Result("habit's steps for %s are done" % spec.name, False,
                       "not yet: habit runs the printed steps for PR #%d at %s, then run `live.py probe` again"
                       % (setup["pull"], head[:12]))]
    comments = _comments(context, setup)
    if "codex" in spec.bots and not [c for c in comments if watch._login(c).lower() == MAINTAINER.lower()
                                     and CODEX_REQUEST in (c.get("body") or "")]:
        return [Result("habit's Codex review bot request is on the probe PR", False,
                       "not yet: habit runs the printed request for PR #%d, then run `live.py probe` again" % setup["pull"])]
    if spec.habit_waiver and not _habit_waiver(spec, setup, comments):
        return [Result("habit's waiver comment is on the probe PR", False,
                       "not yet: habit runs the printed waiver comment for PR #%d at %s" % (setup["pull"], head[:12]))]
    for bot in spec.bots:
        _await(context, setup, bot)
    if _summary(spec, setup, _comments(context, setup)) is None:
        _gh(context, ["pr", "comment", str(setup["pull"]), "--repo", context.repository, "--body-file", "-"],
            stdin="%s\nRequired reviews: %s\n\nMerge watch's version 3 live check posted this as probe data on a sandbox PR.\n"
            % (_title(head), spec.summary))
    results = _fact_results(context, spec, setup)
    ready = all(result.passed for result in results)
    if ready:
        _write_target(context, target(spec, "merge"), setup)
    return results + [Result("every fact read, so the PR is ready for habit's merge", ready,
                             "READY: habit runs the printed pinned merge of PR #%d" % setup["pull"] if ready else "not ready: don't merge")]


def _missing_review(spec, setup):
    title = "Miss: process miss, missing-review in #%d" % setup["pull"]
    observed = "Merged head %s, declared high, lacks: %s." % (setup["head"], spec.lacks)
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
        for bot in spec.bots:
            path = os.path.join(context.directory, target(spec, bot))
            if bot == "codex":
                steps.append((None, "Codex review bot request, after the first `live.py probe` run opens the probe PR",
                              line.format(target=path, wait=first, action='ghm pr comment "$n" --repo %s --body "%s"'
                                          % (context.repository, CODEX_REQUEST))))
            else:
                steps.append((None, "Copilot request in the browser, at Lite, after the first `live.py probe` run",
                              line.format(target=path, wait=first, action='echo "请在浏览器打开 $u ，在 Reviewers 中请求 '
                                          'Copilot，effort 选 Lite；只请求一次"')))
        if spec.habit_waiver:
            path = os.path.join(context.directory, target(spec, "waiver"))
            reason = HABIT_WAIVER_REASON
            steps.append((None, "habit's waiver of %s on the probe PR's head" % spec.habit_waiver,
                          line.format(target=path, wait=first, action='ghm pr comment "$n" --repo %s --body "Waiver: %s at $h '
                                      '— %s"' % (context.repository, spec.habit_waiver, reason))))
        path = os.path.join(context.directory, target(spec, "merge"))
        steps.append((None, "Pinned merge of the probe PR, once a `live.py probe` run reports READY",
                      line.format(target=path, wait="先等 live.py probe 报告 READY",
                                  action='ghm pr merge "$n" --repo %s --admin --squash --match-head-commit "$h"'
                                  % context.repository)))
        return steps
    return listed


PROBES = tuple(Probe(spec.name, ("public",), commands(spec), runner(spec)) for spec in SPECS)
NAMES = tuple(spec.name for spec in SPECS)
