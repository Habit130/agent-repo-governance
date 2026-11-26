#!/usr/bin/env python3
"""habit's gate command, printed by probes/gate.py: the gate probes' setup, then the attempts.

Python 3.9 standard library plus git and gh, using the agent account's existing
environment. Imports do nothing. `--state` names the check's prepared.json. The setup
runs as `live.py probe` without `--post` ran it: the same preconditions (this checkout at
the prepared commit, clean, the sandbox PR merged at its head), then `probes.gate.setup`,
which writes the setup's state and the targets into the check directory or reads back a
completed one. A setup failure prints `setup-failed:` and a Chinese line, makes no attempt
and exits 4. The attempts take the targets' source/merge rows; subprocess arguments are
not shell text. Preserve the section/exit protocol even through the runner's tee pipeline:
0 means all attempts rejected, 2 missing targets, 3 stopped at the first success.
Preparation failures are never GitHub rejections; later reachable attempts run. Judging
never calls this entry.
"""

import argparse
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SETUP_FAILED = 4


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


def set_up(state_path):
    """The setup, as `live.py probe` without `--post` ran it: (repository, default branch, targets path)."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import live
    from probes import gate

    state, directory = live.load_prepared(state_path)
    context = live.checked_context(state, directory)
    gate.setup(context)
    return context.repository, context.default_branch, os.path.join(directory, gate.TARGETS)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="the check's prepared.json")
    args = parser.parse_args(argv)
    say("门禁探针准备中：以 agent 账号打开探针 PR 并等待门禁运行，需要几分钟")
    try:
        repository, branch, targets = set_up(args.state)
    except Exception as error:  # Every setup failure stops here, before any attempt.
        say("setup-failed: %s" % (" ".join(str(error).split()) or type(error).__name__))
        say("门禁探针的准备失败，未进行任何推送或合并尝试；把这段输出交给 agent")
        return SETUP_FAILED
    return attempts(repository, branch, targets)


def attempts(repository, default_branch, targets):
    if not os.path.isfile(targets):
        say("没有 %s：准备没有写出目标，未进行任何推送或合并尝试；把这段输出交给 agent" % targets)
        return 2
    with open(targets) as handle:
        rows = [line.split() for line in handle if line.strip()]
    for kind, commit, branch in rows:
        if kind == "source":
            source, source_branch = commit, branch
    url = "https://github.com/%s.git" % repository

    def after():
        say("== after")
        return run(["git", "ls-remote", url, "refs/heads/" + default_branch, "refs/heads/" + source_branch])

    say("== account")
    say("exit=%d" % run(["gh", "api", "user", "--jq", ".login"]))
    with tempfile.TemporaryDirectory() as directory:
        clone = os.path.join(directory, "s")
        cloned = run(["git", "clone", "-q", "--filter=blob:none", url, clone])
        git = ["git", "-C", clone]
        header = "push %s to %s" % (source, default_branch)
        say("== " + header)
        if cloned:
            never_reached(cloned, header)
        elif attempt(git + ["push", url, "%s:refs/heads/%s" % (source, default_branch)], header):
            after()
            return 3
        for branch in (default_branch, source_branch):
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
            if attempt(["gh", "api", "--method", "PUT", "repos/%s/pulls/%s/merge" % (repository, number),
                        "-f", "merge_method=squash", "-f", "sha=" + head], header):
                after()
                return 3
        return after()


if __name__ == "__main__":
    raise SystemExit(main())
