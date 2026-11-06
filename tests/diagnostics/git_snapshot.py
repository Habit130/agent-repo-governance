"""Bounded #99 probe; no repair and no changes to shared fixture infrastructure.

Run from any cwd with Python 3.9+. JSON records complete path/hash differences.
Unforced runs use run_case unchanged. Write controls act after run_case; threshold
controls use minimal repositories. Neither runs a generator during its action.
A control's expected rejection is not attribution of the historical CI flake.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "tests", "suites"))

import generator_support as gs
import support


def differences(before, after):
    return [{"path": path, "before": before.get(path), "after": after.get(path)}
            for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]


def rejected(before, after):
    try:
        unittest.TestCase().assertEqual(after, before, "a run changed the worktree")
    except AssertionError:
        return True
    return False


def trace_events(path):
    """Only command names and lineage, not arbitrary argv/environment values."""
    events = []
    if os.path.exists(path):
        with open(path) as handle:
            for line in handle:
                event = json.loads(line)
                if event.get("event") == "cmd_name":
                    events.append({key: event[key] for key in ("event", "sid", "name", "hierarchy") if key in event})
    return events


def probe(control):
    with tempfile.TemporaryDirectory(prefix="snapshot-99-") as root:
        trace = os.path.join(root, "trace.jsonl")
        old_trace = os.environ.get("GIT_TRACE2_EVENT")
        os.environ["GIT_TRACE2_EVENT"] = trace
        try:
            case = gs.load_case("older-record")
            if control == "idle":
                case["run"] = []
            run = gs.run_case(root, case)
            worktree = run["worktree"]
            initial_changes = differences(run["before"][0], run["after"][0])
            problems = []
            for command, (code, facts, out, err) in run["results"].items():
                expected = case["expect"].get(command, {})
                if code != expected.get("exit", 0) or err:
                    problems.append(command + ": unexpected exit/stderr")
                if "items" in expected:
                    items = dict((i["item"], i["status"]) for i in facts["items"])
                    if items != expected["items"]:
                        problems.append(command + ": unexpected item statuses")
                if "checklist" in expected:
                    if [step["step"] for step in facts["checklist"]] != expected["checklist"]:
                        problems.append(command + ": unexpected checklist")
                problems.extend(gs.subset({k: v for k, v in expected.items() if k not in ("exit", "items", "checklist")}, facts))
            if gs.writes(run["log"]) or any(not e["recorded"] for e in run["log"]):
                problems.append("unexpected stand-in call")
            home_unchanged = run["before"][1] == run["after"][1]
            before, after = run["before"][0], run["after"][0]
            action = None
            if control in ("worktree-write", "object-write", "repack"):
                before = gs.tree_snapshot(worktree)
                if control == "worktree-write":
                    action = "write diagnostic-write.txt (no generator running)"
                    with open(os.path.join(worktree, "diagnostic-write.txt"), "w") as handle:
                        handle.write("diagnostic real write\n")
                elif control == "object-write":
                    action = "git hash-object -w --stdin (no generator running)"
                    subprocess.run(["git", "-C", worktree, "hash-object", "-w", "--stdin"],
                                   input=b"diagnostic unreachable object\n", env=support.isolated_env(),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                else:
                    action = "git repack -ad (no generator running)"
                    support.git(worktree, "repack", "-ad")
                after = gs.tree_snapshot(worktree)
            return {"control": control, "action": action, "generator_changes": initial_changes,
                    "changes": differences(before, after), "snapshot_rejected": rejected(before, after),
                    "home_unchanged": home_unchanged, "problems": problems,
                    "git_commands": trace_events(trace)}
        finally:
            if old_trace is None:
                os.environ.pop("GIT_TRACE2_EVENT", None)
            else:
                os.environ["GIT_TRACE2_EVENT"] = old_trace


def threshold_probe(count):
    """One variable: one versus two real blobs in Git's sampled 17 shard.

    Use plumbing to create the initial commit without invoking auto-maintenance.
    No maintenance configuration or threshold is changed. Foreground execution
    makes the threshold observation deterministic, not the historical race.
    """
    with tempfile.TemporaryDirectory(prefix="snapshot-99-threshold-") as root:
        worktree = support.init_repo(os.path.join(root, "repo"))
        found = 0
        nonce = 0
        while found < count:
            data = ("sampled object %d\n" % nonce).encode("ascii")
            oid = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            if oid.startswith("17"):
                with open(os.path.join(worktree, "blob-%d" % found), "wb") as handle:
                    handle.write(data)
                found += 1
            nonce += 1
        support.git(worktree, "add", ".")
        tree = support.git(worktree, "write-tree").strip()
        # Fixed dates avoid accidentally adding a third sampled commit object.
        env = support.isolated_env({"GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
                                    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"})
        commit = support.git(worktree, "commit-tree", tree, "-m", "threshold control", env=env).strip()
        support.git(worktree, "update-ref", "HEAD", commit)
        before = gs.tree_snapshot(worktree)
        sampled = sorted(p for p, value in before.items() if p.startswith(".git/objects/17/") and value[0] == "file")
        if len(sampled) != count:
            raise AssertionError("control does not have the intended sampled-object count")
        trace = os.path.join(root, "trace.jsonl")
        support.git(worktree, "maintenance", "run", "--auto", "--no-detach",
                    env=support.isolated_env({"GIT_TRACE2_EVENT": trace}))
        after = gs.tree_snapshot(worktree)
        return {"control": "threshold-%d" % count, "sampled_objects": sampled,
                "action": "git maintenance run --auto --no-detach (no generator running)",
                "generator_changes": [], "changes": differences(before, after),
                "snapshot_rejected": rejected(before, after), "home_unchanged": True,
                "problems": [], "git_commands": trace_events(trace)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--commit-date", help="Pin fixture author/committer dates for a timing-independent object layout")
    parser.add_argument("--control", choices=("none", "idle", "worktree-write", "object-write", "repack", "threshold-1", "threshold-2"), default="none")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    if args.commit_date:
        os.environ["GIT_AUTHOR_DATE"] = args.commit_date
        os.environ["GIT_COMMITTER_DATE"] = args.commit_date
    case_path = os.path.join(gs.CASES, "older-record.json")
    with open(case_path, "rb") as handle:
        case_hash = hashlib.sha256(handle.read()).hexdigest()
    threshold = args.control.startswith("threshold-")
    report = {"source_head": support.git(ROOT, "rev-parse", "HEAD").strip(),
              "commit_date": args.commit_date,
              "case": "sampled-object-threshold" if threshold else "older-record",
              "case_sha256": None if threshold else case_hash,
              "os": platform.platform(), "python": sys.version,
              "git": support.git(ROOT, "--version").strip(),
              "runs": [threshold_probe(int(args.control[-1])) if threshold else probe(args.control) for _ in range(args.runs)]}
    print(json.dumps(report, indent=2))
    forced = args.control in ("worktree-write", "object-write", "repack", "threshold-2")
    return int(any(r["problems"] or not r["home_unchanged"] or
                   (forced and (not r["snapshot_rejected"] or r["generator_changes"])) or
                   (not forced and r["snapshot_rejected"]) for r in report["runs"]))


if __name__ == "__main__":
    sys.exit(main())
