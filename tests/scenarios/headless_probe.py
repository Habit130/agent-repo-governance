#!/usr/bin/env python3
"""Allocated AC-52 headless resume probe; never run by CI or against real GitHub.

The real home supplies only the harness login. Scratch holds the repository, run-only
skill source and output. A failed or refused run is evidence to stop, not a retry route.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests"))
from standins import environment


def clean_environment(scratch):
    env = environment.environment(str(scratch))
    for name in list(env):
        if name.startswith(("CLAUDE", "OPENCODE", "CODEX_", "DSH_")) or name in ("AI_AGENT", "AGENT"):
            del env[name]
    return env


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def call(command, cwd, env, output):
    # OpenCode v2.2.2 run/run.ts prefers PWD to process.cwd(). Keep both in sync.
    child_env = dict(env, PWD=str(cwd))
    result = subprocess.run(command, cwd=str(cwd), env=child_env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=240)
    save(output.with_suffix(".stdout"), result.stdout)
    save(output.with_suffix(".stderr"), result.stderr)
    return result


def opencode_result(result, session, expected):
    try:
        events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    except ValueError:
        return False
    text = "".join(event.get("part", {}).get("text", "") for event in events if event.get("type") == "text")
    ids = set(event["sessionID"] for event in events if "sessionID" in event)
    return result.returncode == 0 and ids == {session} and text.strip() == expected and not any(
        event.get("type") in ("error", "permission") for event in events)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("harness", choices=["claude", "opencode"])
    args = parser.parse_args()
    scratch = Path(tempfile.mkdtemp(prefix="ac52-resume-", dir=os.environ.get("AC52_PROBE_TMPDIR")))
    print("Evidence directory: %s" % scratch, flush=True)
    checkout = scratch / "repository"
    checkout.mkdir()
    env = clean_environment(scratch)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(checkout), env=env, check=True)
    nonce = "AC52-" + uuid.uuid4().hex
    skill = ("---\nname: govern-repository\ndescription: Probe headless resume only.\n"
             "disable-model-invocation: true\n---\n\n"
             "This is the allocated AC-52 resume probe, not the production generator. "
             "Make no tool calls or filesystem or GitHub writes. Remember the private marker " + nonce + ". "
             "In this turn, send the plain Chinese confirmation `habit，是否继续 resume probe？`, "
             "then a newline and the absolute working directory from the system environment context "
             "(not the skill directory), and end the turn. Do not reveal the marker yet. After the next user turn says "
             "`继续 resume probe`, respond with only the private marker from this skill and end.\n")
    if args.harness == "opencode":
        source = scratch / "skills"
        save(source / "govern-repository" / "SKILL.md", skill)
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps({
            "$schema": "https://opencode.ai/config.json", "skills": [str(source)]})
        session = "ses_" + uuid.uuid4().hex[:26]
        common = ["opencode", "run", "--standalone", "--format", "json", "--session", session]
        first = call(common + ["@govern-repository"], checkout, env, scratch / "first")
        print("First turn exit: %s" % first.returncode, flush=True)
        print(first.stdout, flush=True)
        print(first.stderr, file=sys.stderr, flush=True)
        if not opencode_result(first, session, "habit，是否继续 resume probe？\n" + str(checkout)):
            save(scratch / "result.json", json.dumps({"harness": args.harness, "passed": False, "stage": "first"}))
            return 1
        second = call(common + ["继续 resume probe"], checkout, env, scratch / "second")
        print("Resumed turn exit: %s" % second.returncode, flush=True)
        print(second.stdout, flush=True)
        print(second.stderr, file=sys.stderr, flush=True)
        passed = opencode_result(second, session, nonce)
        save(scratch / "result.json", json.dumps({"harness": args.harness, "session": session, "passed": passed}))
        print("PASS resume and run-only skill" if passed else "STOP resume probe failed")
        return 0 if passed else 1
    plugin = scratch / "plugin"
    save(plugin / ".claude-plugin" / "plugin.json", json.dumps({"name": "ac52-probe", "version": "0.0.1"}))
    save(plugin / "skills" / "govern-repository" / "SKILL.md", skill)
    session = str(uuid.uuid4())
    common = ["claude", "-p", "--output-format", "json", "--plugin-dir", str(plugin),
              "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
              "--tools", "Skill,Read", "--allowedTools", "Skill"]
    first = call(common + ["--session-id", session, "/ac52-probe:govern-repository"], checkout, env, scratch / "first")
    print("First turn exit: %s" % first.returncode, flush=True)
    print(first.stdout, flush=True)
    print(first.stderr, file=sys.stderr, flush=True)
    try:
        data = json.loads(first.stdout)
        passed = (first.returncode == 0 and not data.get("is_error") and
                  not data.get("permission_denials") and data.get("session_id") == session and
                  data.get("result", "").strip() == "habit，是否继续 resume probe？\n" + str(checkout))
    except ValueError:
        passed = False
    if not passed:
        save(scratch / "result.json", json.dumps({"harness": args.harness, "passed": False, "stage": "first"}))
        return 1
    second = call(common + ["--resume", session, "继续 resume probe"], checkout, env, scratch / "second")
    print("Resumed turn exit: %s" % second.returncode, flush=True)
    print(second.stdout, flush=True)
    print(second.stderr, file=sys.stderr, flush=True)
    try:
        data = json.loads(second.stdout)
        passed = (second.returncode == 0 and not data.get("is_error") and
                  not data.get("permission_denials") and data.get("session_id") == session and
                  data.get("result", "").strip() == nonce)
    except ValueError:
        passed = False
    save(scratch / "result.json", json.dumps({"harness": args.harness, "session": session, "passed": passed}))
    print("PASS resume and run-only skill" if passed else "STOP resume probe failed")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
