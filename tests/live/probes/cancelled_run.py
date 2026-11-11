"""One real timeout on the public sandbox's render merge (#135).

prepare plants a workflow whose push path filter is the render PR's unique marker.
Its sole job sleeps past a one-minute timeout. Later pushes leave that marker unchanged,
so the workflow cannot keep the default branch red. Keep the marker and workflow as
probe evidence. The probe reads GitHub's run, timeout annotation, Merge watch log and
six-field miss record, then closes only that verified record so another probe can run.
A pre-existing open red record stops prepare; it is never closed by this probe.
"""

import base64
import json
import os
import re

from probes import Probe, ProbeError, Result
from probes.gate import _gh
from probes import merge_watch as watch

NAME = "merge-watch-cancelled"
SETUP = "cancelled_run_setup"


def workflow(marker, branch):
    return ("name: live-cancelled-run\non:\n  push:\n    branches: [%s]\n    paths: [%s]\n"
            "permissions:\n  contents: read\njobs:\n  timeout:\n    runs-on: ubuntu-latest\n"
            "    timeout-minutes: 1\n    steps:\n      - run: sleep 120\n" % (json.dumps(branch), json.dumps(marker)))


def stage(clone, marker, branch):
    path = ".github/workflows/live-cancelled-%s.yml" % os.path.basename(marker).removesuffix(".md")
    with open(os.path.join(clone, path), "w") as handle:
        handle.write(workflow(marker, branch))
    return {"workflow": path, "marker": marker}


def _pages(context, path, field=None):
    items, page = [], 1
    while True:
        answer = context.api("%s%sper_page=100&page=%d" % (path, "&" if "?" in path else "?", page))
        batch = (answer or {}).get(field, []) if field else (answer or [])
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def preflight(context):
    issues = _pages(context, "repos/%s/issues?labels=miss&state=open" % context.repository)
    if any("Category: red-default-branch" in watch._lines(item) for item in issues):
        raise ProbeError("an open red-default-branch record would suppress this probe; resolve it before prepare")


def _content(context, path, ref):
    data = context.api("repos/%s/contents/%s?ref=%s" % (context.repository, path, ref))
    return base64.b64decode(data["content"]).decode("utf-8")


def cancelled(context):
    setup = context.recall(SETUP)
    if not setup:
        raise ProbeError("prepare this check with --probe merge-watch-cancelled first")
    pull = context.api("repos/%s/pulls/%d" % (context.repository, context.sandbox_pr))
    if not pull.get("merged"):
        raise ProbeError("habit must merge the render PR first")
    commit = pull["merge_commit_sha"]
    runs = _pages(context, "repos/%s/actions/runs?head_sha=%s" % (context.repository, commit), "workflow_runs")
    triggered = [r for r in runs if r.get("path") == setup["workflow"] and r.get("event") == "push"
                 and r.get("head_branch") == context.default_branch and r.get("head_sha") == commit]
    if len(triggered) != 1:
        raise ProbeError("expected one probe push run at %s; found %d; retry after GitHub completes it" % (commit, len(triggered)))
    run = triggered[0]
    results = [Result("the probe push run completed cancelled", run.get("status") == "completed" and run.get("conclusion") == "cancelled",
                      "%s: %s/%s" % (run.get("html_url"), run.get("status"), run.get("conclusion")))]
    jobs = _pages(context, "repos/%s/actions/runs/%s/jobs" % (context.repository, run["id"]), "jobs")
    timed_out = False
    for job in jobs:
        if job.get("name") != "timeout" or job.get("conclusion") != "cancelled":
            continue
        # The check ID is read from GitHub, never a supplied URL used for authentication.
        check_id = str(job.get("check_run_url", "")).rsplit("/", 1)[-1]
        if not check_id.isdigit():
            continue
        annotations = _pages(context, "repos/%s/check-runs/%s/annotations" % (context.repository, check_id))
        timed_out = any(re.search(r"exceeded.*(?:execution time|time limit)", item.get("message", ""), re.I) for item in annotations)
    results.append(Result("GitHub attributes cancellation to the job time limit", timed_out, "timeout annotation present: %s" % timed_out))
    observed = "Workflow %s concluded cancelled on its push-triggered run %s at commit %s." % (run.get("name"), run.get("html_url"), commit)
    title = "Miss: escape, red-default-branch in #%d" % context.sandbox_pr
    expected = ["Merged PR: #%d" % context.sandbox_pr, "Kind: escape", "Category: red-default-branch",
                "Observed: " + observed, "Found by: Merge watch", "Bug issue: none", ""]
    watch_runs = [r for r in runs if r.get("path") == watch.WORKFLOW and r.get("event") == "workflow_run"
                  and r.get("status") == "completed" and r.get("conclusion") == "success"]
    witnessed = [r["html_url"] for r in watch_runs if "MISS %s. %s" % (title, observed) in watch._outcomes(context, r)]
    results.append(Result("Merge watch's own workflow_run run reports this cancelled run", bool(witnessed), ", ".join(witnessed) or "not yet observed"))
    records = _pages(context, "repos/%s/issues?labels=miss&state=all" % context.repository)
    found = [item for item in records if item.get("title") == title and watch._lines(item) == expected
             and watch._login(item) == watch.RECORD_AUTHOR
             and [label.get("name") for label in item.get("labels", [])] == ["miss"]
             and (item.get("created_at") or "") >= (pull.get("merged_at") or "~")]
    results.append(Result("GitHub holds the exact six-field record opened by Merge watch", len(found) == 1,
                          ", ".join(item["html_url"] for item in found) or "no matching record"))
    expected_workflow = workflow(setup["marker"], context.default_branch)
    safe = (_content(context, setup["workflow"], context.default_branch) == expected_workflow
            and _content(context, setup["marker"], context.default_branch) == _content(context, setup["marker"], commit))
    results.append(Result("later pushes cannot retrigger the timeout without editing this check's unique marker", safe, setup["workflow"]))
    if not all(result.passed for result in results):
        return results
    record = found[0]
    if record.get("state") == "open":
        _gh(context, ["issue", "close", str(record["number"]), "--repo", context.repository,
                      "--comment", "Verified intentional timeout in the #135 live probe; closing this sandbox-only record to permit another check."])
    closed = context.api("repos/%s/issues/%d" % (context.repository, record["number"]))
    results.append(Result("the probe's record is closed so it cannot suppress a later probe", closed.get("state") == "closed", closed.get("html_url", "")))
    return results


PROBES = (Probe(NAME, ("public",), watch.no_commands, cancelled),)
