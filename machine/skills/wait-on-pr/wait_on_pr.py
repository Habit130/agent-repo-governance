"""A bounded, read-only GitHub wait with one local Codex Desktop notification."""

import argparse
from collections import Counter
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid


DURATIONS = {"codex": 30 * 60, "copilot": 15 * 60, "role": 24 * 3600, "merge": 24 * 3600}
MACHINE_ACCOUNT = "Habit098"
CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"


class ReadFailure(Exception):
    """A fixed diagnostic safe to include in a notice."""


class WrongAccount(ReadFailure):
    """The active GitHub login differs from the machine's agent account."""


class Replaced(Exception):
    """The original wait lost its registration during a paginated read."""


PAGE = "pageInfo { hasNextPage endCursor } nodes"
COMMENT = "id lastEditedAt"
REVIEW = "id state lastEditedAt"
THREAD = "id isResolved comments(first: 100) { %s { %s } }" % (PAGE, COMMENT)
QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) { pullRequest(number: $number) {
    id state headRefOid
    commits(last: 1) { nodes { commit { oid status { contexts { id context state } } } } }
    reviews(first: 100) { %s { %s } }
    reviewThreads(first: 100) { %s { %s } }
    comments(first: 100) { %s { %s } }
  } }
}""" % (PAGE, REVIEW, PAGE, THREAD, PAGE, COMMENT)


def snapshot(fetch, repository, number, active=lambda: True):
    def request(query, variables):
        if not active():
            raise Replaced()
        return fetch(query, variables)

    owner, repo = repository.split("/")
    pr = request(QUERY, {"owner": owner, "repo": repo, "number": number})["repository"]["pullRequest"]
    state = pr["state"]
    if state in ("MERGED", "CLOSED"):
        return {"state": state}
    if state != "OPEN":
        raise ValueError("unknown PR state")

    def nodes(parent, typename, field, selection):
        result = parent[field]
        cursors = set()
        while True:
            yield from result["nodes"]
            info = result["pageInfo"]
            if not info["hasNextPage"]:
                return
            cursor = info["endCursor"]
            if not cursor or cursor in cursors:
                raise ValueError("incomplete GitHub page")
            cursors.add(cursor)
            query = """query($id: ID!, $after: String!) {
              node(id: $id) { ... on %s { %s(first: 100, after: $after) { %s { %s } } } }
            }""" % (typename, field, PAGE, selection)
            result = request(query, {"id": parent["id"], "after": cursor})["node"][field]

    def comments(parent, typename):
        return {c["id"]: c["lastEditedAt"] for c in nodes(parent, typename, "comments", COMMENT)}

    commit, = pr["commits"]["nodes"]
    commit = commit["commit"]
    if commit["oid"] != pr["headRefOid"]:
        raise ValueError("head changed during read")
    statuses = [] if commit["status"] is None else commit["status"]["contexts"]
    return {
        "state": state, "head": commit["oid"],
        "statuses": {s["context"]: (s["id"], s["state"]) for s in statuses},
        "reviews": {r["id"]: (r["state"], r["lastEditedAt"])
                    for r in nodes(pr, "PullRequest", "reviews", REVIEW)},
        "threads": {t["id"]: (t["isResolved"], comments(t, "PullRequestReviewThread"))
                    for t in nodes(pr, "PullRequest", "reviewThreads", THREAD)},
        "comments": comments(pr, "PullRequest"),
    }


def event(baseline, current):
    if current["state"] != "OPEN":
        return current["state"].lower()
    if baseline is not None:
        if any(current[key] != baseline[key] for key in ("head", "statuses", "reviews", "threads")):
            return "change"
        if any(key not in baseline["comments"] or baseline["comments"][key] != edited
               for key, edited in current["comments"].items()):
            return "change"
    return None


class Slot:
    """One registration per chat and PR, across worktrees. Replacements never signal a PID."""

    def __init__(self, root, repo, number, thread):
        self.pr = "%s#%d" % (repo.lower(), number)
        self.thread = thread
        key = hashlib.sha256((thread + "/" + self.pr).encode()).hexdigest()
        self.directory = root / key
        self.directory.mkdir(mode=0o700, exist_ok=True)
        self.active = self.directory / "active"

    @contextmanager
    def locked(self):
        with (self.directory / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def current(self):
        try:
            return self.active.read_text()
        except FileNotFoundError:
            return ""

    def receipt(self, nonce):
        return self.directory / (nonce + ".json")

    @staticmethod
    def write(path, text):
        tmp = path.with_suffix(".tmp")
        tmp.write_text(text)
        tmp.replace(path)

    def start(self):
        with self.locked():
            nonce = str(uuid.uuid4())
            self.write(self.active, nonce)
            return nonce

    def stop(self, notice=None):
        with self.locked():
            result = "stopped"
            if notice is not None:
                if self.current() != notice or not self.receipt(notice).is_file():
                    return "late or duplicate"
                result = json.loads(self.receipt(notice).read_text())["event"]
            self.write(self.active, "")
            return result

    def deliver(self, nonce, kind, reason, failures, send):
        with self.locked():
            receipt = self.receipt(nonce)
            if self.current() != nonce or receipt.exists():
                return
            record = {"pr": self.pr, "wait": kind, "event": reason, "nonce": nonce,
                      "attempted_at": time.time(), "read_failures": dict(failures),
                      "outcome": "attempt started; result unknown"}
            self.write(receipt, json.dumps(record))
            message = "wait-on-pr %s event=%s nonce=%s" % (self.pr, reason, nonce)
            if failures:
                message += " (read failures: %s)" % ", ".join(
                    "%s x%d" % item for item in sorted(failures.items()))
            try:
                record["outcome"] = send(message)
            except subprocess.TimeoutExpired:
                record["outcome"] = "queue timeout; delivery unknown"
            except OSError:
                record["outcome"] = "queue could not run"
            self.write(receipt, json.dumps(record))


def watch(slot, kind, read, send, clock=time.monotonic, sleep=time.sleep):
    nonce = slot.start()
    next_read = clock()
    deadline = next_read + DURATIONS[kind]
    failures = Counter()
    baseline = None
    def active():
        return slot.current() == nonce

    while active():
        now = clock()
        if now >= deadline:
            slot.deliver(nonce, kind, "deadline", failures, send)
            break
        if now < next_read:
            sleep(min(2, next_read - now, deadline - now))
            continue
        next_read = now + 60
        try:
            current = read(deadline, active)
        except Replaced:
            break
        except ReadFailure as error:
            if baseline is None and isinstance(error, WrongAccount):
                raise
            failures[str(error)] += 1
            if baseline is None:
                print("Baseline unavailable (%s); retrying at the next interval." % error, flush=True)
            continue
        if clock() >= deadline or not active():
            continue
        if baseline is None:
            if failures:
                print("Recheck GitHub for activity during baseline recovery.", flush=True)
            print("Armed %s for %s in thread %s, nonce %s" % (slot.pr, kind, slot.thread, nonce), flush=True)
        reason = event(baseline, current)
        if reason:
            slot.deliver(nonce, kind, reason, failures, send)
            break
        if baseline is None:
            baseline = current
    return nonce


def github_cli(env):
    config = Path(env.get("XDG_CONFIG_HOME") or Path(env["HOME"]) / ".config") / "gh"
    override = env.get("GH_CONFIG_DIR")
    token_names = {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"}
    if token_names.intersection(env) or (override and Path(override).resolve() != config.resolve()):
        raise ValueError("use the machine agent account without authentication overrides")
    # The approved process runs an installed executable outside the worktree.
    gh = shutil.which("gh", path=os.defpath + ":/opt/homebrew/bin:/usr/local/bin")
    if gh is None:
        raise ValueError("gh unavailable in the system or Homebrew bin directories")
    return gh


def github_read(gh, repo, number, deadline, active=lambda: True):
    def api(arguments, data=None):
        if not active():
            raise Replaced()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ReadFailure("GitHub timeout")
        try:
            response = subprocess.run(
                [gh, "api", "--hostname", "github.com"] + arguments, input=data, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd="/", timeout=min(30, remaining))
        except subprocess.TimeoutExpired:
            raise ReadFailure("GitHub timeout")
        except OSError:
            raise ReadFailure("gh unavailable")
        if response.returncode:
            raise ReadFailure("gh exit %d" % response.returncode)
        return response.stdout

    if api(["user", "--jq", ".login"]).strip().casefold() != MACHINE_ACCOUNT.casefold():
        raise WrongAccount("GitHub is not using the machine agent account")

    def fetch(query, variables):
        payload = json.loads(api(["graphql", "--input", "-"], json.dumps({"query": query, "variables": variables})))
        if payload.get("errors"):
            raise ReadFailure("GitHub query failed")
        return payload["data"]

    try:
        return snapshot(fetch, repo, number, active)
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ReadFailure("incomplete GitHub response")


def private_root():
    # The sandbox and the approved terminal share this directory even with different TMPDIRs.
    root = Path("/tmp") / ("governance-wait-on-pr-%d" % os.getuid())
    root.mkdir(mode=0o700, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("wait directory is not private")
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    for action in ("read", "stop", "arm"):
        sub = subs.add_parser(action)
        sub.add_argument("repo", metavar="OWNER/REPO")
        sub.add_argument("number", type=int, metavar="PR")
        if action == "stop":
            sub.add_argument("--notice", type=uuid.UUID)
        if action == "arm":
            sub.add_argument("kind", choices=DURATIONS)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", args.repo) or args.number < 1:
        parser.error("expected OWNER/REPO and a positive PR number")

    if args.action == "read":
        facts = github_read(github_cli(os.environ), args.repo, args.number, time.monotonic() + 60)
        print("%s#%d %s" % (args.repo, args.number, facts["state"].lower()))
        return

    try:
        thread = str(uuid.UUID(os.environ.get("CODEX_THREAD_ID", "")))
    except ValueError:
        parser.error("terminal has no valid CODEX_THREAD_ID; use the current Codex wait")
    slot = Slot(private_root(), args.repo, args.number, thread)
    if args.action == "stop":
        print(slot.stop(str(args.notice) if args.notice else None))
        return

    gh = github_cli(os.environ)
    help_text = subprocess.run([CODEX, "queue", "--help"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, timeout=10)
    if help_text.returncode or not all(flag in help_text.stdout for flag in ("--thread", "--message", "--resume")):
        parser.error("bundled queue unavailable; use the current Codex wait")

    def send(message):
        result = subprocess.run([CODEX, "queue", "--thread", thread, "--message", message, "--resume"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if result.returncode:
            return "queue exit %d; delivery unknown" % result.returncode
        return "queue exited 0; resume unconfirmed"

    def read(deadline, active):
        return github_read(gh, args.repo, args.number, deadline, active)

    watch(slot, args.kind, read, send)


if __name__ == "__main__":
    try:
        main()
    except ReadFailure as error:
        sys.exit(str(error))
    except ValueError as error:
        sys.exit(str(error))
    except (OSError, subprocess.TimeoutExpired):
        sys.exit("Local waiter unavailable; use the current Codex wait.")
