#!/usr/bin/env python3
"""habit-only gate attempts, invoked by probes/gate.py's printed command.

Python 3.9 standard library plus git and gh, using the agent account's existing
environment. Imports do nothing. Setup and judging never call this entry.
Targets are the existing source/merge rows; subprocess arguments are not shell
text. Preserve the section/exit protocol even through the runner's tee pipeline:
0 means all attempts rejected, 2 missing targets, 3 stopped at the first success.
Preparation failures are never GitHub rejections; later reachable attempts run.
"""

import argparse
import os
import subprocess
import tempfile


def run(args):
    """Keep tool output in its protocol section, including redirected captures."""
    return subprocess.run(args, stdin=subprocess.DEVNULL, stderr=subprocess.STDOUT).returncode


def say(text):
    print(text, flush=True)


def never_reached(code, header):
    say("never-reached: " + header)
    say("准备失败，未到达 GitHub，不是拒绝")
    say("exit=%d" % code)


def attempt(args, header):
    code = run(args)
    say("exit=%d" % code)
    if code == 0:
        say("stop-after: " + header)
        say("尝试已成功：%s；停止后续尝试，按产品问题停止，不要重跑命令" % header)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--targets", required=True)
    args = parser.parse_args()
    if not os.path.isfile(args.targets):
        say("没有 %s：先运行一次不带 --post 的 live.py probe" % args.targets)
        return 2
    with open(args.targets) as handle:
        rows = [line.split() for line in handle if line.strip()]
    for kind, commit, branch in rows:
        if kind == "source":
            source, source_branch = commit, branch
    url = "https://github.com/%s.git" % args.repository

    def after():
        say("== after")
        return run(["git", "ls-remote", url, "refs/heads/" + args.branch, "refs/heads/" + source_branch])

    say("== account")
    say("exit=%d" % run(["gh", "api", "user", "--jq", ".login"]))
    with tempfile.TemporaryDirectory() as directory:
        clone = os.path.join(directory, "s")
        cloned = run(["git", "clone", "-q", "--filter=blob:none", url, clone])
        git = ["git", "-C", clone]
        header = "push %s to %s" % (source, args.branch)
        say("== " + header)
        if cloned:
            never_reached(cloned, header)
        elif attempt(git + ["push", url, "%s:refs/heads/%s" % (source, args.branch)], header):
            after()
            return 3
        for branch in (args.branch, source_branch):
            header = "force-push " + branch
            say("== " + header)
            prepared = cloned
            if not prepared:
                prepared = run(git + ["checkout", "-q", "--detach", "origin/" + branch])
            if not prepared:
                prepared = run(git + ["commit", "-q", "--amend", "-m", "Live check: a force-push attempt"])
            if prepared:
                never_reached(prepared, header)
            elif attempt(git + ["push", "--force", url, "HEAD:refs/heads/" + branch], header):
                after()
                return 3
        for kind, number, head in rows:
            if kind != "merge":
                continue
            header = "merge %s at %s" % (number, head)
            say("== " + header)
            if attempt(["gh", "api", "--method", "PUT", "repos/%s/pulls/%s/merge" % (args.repository, number),
                        "-f", "merge_method=squash", "-f", "sha=" + head], header):
                after()
                return 3
        return after()


if __name__ == "__main__":
    raise SystemExit(main())
