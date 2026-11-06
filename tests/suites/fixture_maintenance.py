"""Controlled real-Git maintenance dispatch for #115 (diagnosis #99 / PR #114).

Git's setup commit really dispatches `git maintenance` through GIT_EXEC_PATH.
This test adapter substitutes only its scheduling: the selected child starts a
worker, acknowledges readiness, and returns to commit. A socket holds that worker
until the complete baseline is captured. It then runs real automatic commit-graph
maintenance with a forced documented trigger, independent of sampled-object hashes
and version-dependent default thresholds. All protocol/trace files stay outside
the measured repository. Timeouts bound failures; none supplies ordering.
"""

import json
import os
import shlex
import socket
import subprocess
import sys


def install(root, real_git, selected):
    """Return a test-local exec path and listening socket, with no config writes."""
    bindir = os.path.join(root, "git-exec")
    os.makedirs(bindir)
    address = os.path.join(root, "maintenance.sock")
    server = socket.socket(socket.AF_UNIX)
    server.bind(address)
    server.listen(4)
    server.settimeout(10)
    entry = os.path.join(bindir, "git")
    with open(entry, "w") as handle:
        handle.write("#!/bin/sh\nexec %s %s %s %s %s \"$@\"\n" % tuple(
            shlex.quote(value) for value in (sys.executable, os.path.abspath(__file__), real_git, address, selected)))
    os.chmod(entry, 0o755)
    return bindir, server


def dispatch(real_git, address, selected, args):
    if (args[:3] != ["maintenance", "run", "--auto"] or
            os.path.realpath(os.getcwd()) != os.path.join(os.path.dirname(address), "tally")):
        os.execv(real_git, [real_git] + args)
    message = subprocess.check_output([real_git, "log", "-1", "--format=%s"], universal_newlines=True).strip()
    # Log every actual dispatch, including the nonselected setup commit.
    with open(address + ".dispatch", "a") as handle:
        handle.write(json.dumps({"commit": message, "args": args}) + "\n")
    if message != selected:
        return
    worker = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--worker", real_git, address],
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        if worker.stdout.read(1) != b"R":
            raise AssertionError("maintenance worker did not acknowledge readiness")
    finally:
        worker.stdout.close()


def worker(real_git, address):
    with socket.socket(socket.AF_UNIX) as channel:
        channel.settimeout(10)
        channel.connect(address)
        print("R", end="", flush=True)
        if channel.recv(1) != b"G":
            return
        result = subprocess.run([real_git, "-c", "maintenance.commit-graph.auto=-1",
                                 "maintenance", "run", "--auto", "--no-detach", "--task=commit-graph"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        channel.sendall(json.dumps({"exit": result.returncode, "stderr": result.stderr.decode()}).encode())


if __name__ == "__main__":
    if sys.argv[1] == "--worker":
        worker(*sys.argv[2:])
    else:
        dispatch(*sys.argv[1:4], sys.argv[4:])
