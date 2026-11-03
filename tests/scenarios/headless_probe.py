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
PRIMARY = REPO.parent / "agent-repo-governance"
MODEL = "xai/grok-4.7"
FIRST_PROMPT = "Call the `skill` tool with id `govern-repository`, then follow that skill's instructions exactly."
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


def as_text(value):
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else (value or "")


def call(command, cwd, env, output):
    # OpenCode v2.2.2 run/run.ts prefers PWD to process.cwd(). Keep both in sync.
    child_env = dict(env, PWD=str(cwd))
    try:
        result = subprocess.run(command, cwd=str(cwd), env=child_env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=240)
    except subprocess.TimeoutExpired as expired:
        # A timeout is a failed attempt: keep what arrived and let the assertions refuse it.
        result = subprocess.CompletedProcess(command, -1, as_text(expired.stdout), as_text(expired.stderr))
    save(output.with_suffix(".stdout"), result.stdout)
    save(output.with_suffix(".stderr"), result.stderr)
    return result


def opencode_checks(result, session, expected, skill_directory=None):
    """One named Pass/Fail per diagnostic assertion; exit 0 alone is never a Pass.

    In v2.2.5 noninteractive runs a refused permission is not an event: it warns
    `auto-rejecting` and fails the tool, so both are inspected. skill_directory is the
    first turn's selected source; without it, the turn must not touch the skill tool.
    """
    try:
        events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    except ValueError:
        return {"output is JSON events": False}
    tools = [event.get("part", {}) for event in events if event.get("type") == "tool_use"]
    skills = [tool for tool in tools if tool.get("tool") == "skill"]
    last_tool = max((index for index, event in enumerate(events) if event.get("type") == "tool_use"), default=-1)
    text = "".join(event.get("part", {}).get("text", "") for event in events[last_tool + 1:]
                   if event.get("type") == "text")
    states = [tool.get("state", {}) for tool in tools]
    checks = {
        "harness exit 0": result.returncode == 0,
        "one session ID": set(event["sessionID"] for event in events if "sessionID" in event) == {session},
        "reply after the last tool call": text.strip() == expected,
        "no error events": not any(event.get("type") in ("error", "permission") for event in events),
        "no permission refusal": "auto-rejecting" not in result.stdout + result.stderr,
        "every tool completed": all(state.get("status") == "completed" for state in states),
        "tools outside the delivery repository": not any(
            place in json.dumps(tool, ensure_ascii=False) for tool in tools for place in (str(REPO), str(PRIMARY))),
    }
    if skill_directory is None:
        checks["no skill reload"] = not skills
    else:
        state = skills[0].get("state", {}) if len(skills) == 1 else {}
        checks["skill tool called once with the ID"] = state.get("input", {}).get("id") == "govern-repository"
        checks["run-only source selected"] = state.get("metadata", {}).get("metadata", {}).get(
            "directory") == str(skill_directory)
    return checks


def stored_models(session, cwd, env, output):
    """provider/model of each stored assistant message; `--format json` events carry neither."""
    export = call(["opencode", "session", "export", "--standalone", session], cwd, env, output)
    try:
        return ["%s/%s" % (message["model"]["providerID"], message["model"]["id"])
                for message in json.loads(export.stdout)["messages"] if message["type"] == "assistant"]
    except (KeyError, TypeError, ValueError):
        return []


def report(stage, checks):
    for name, passed in checks.items():
        print("%s %s: %s" % ("Pass" if passed else "Fail", stage, name), flush=True)
    return all(checks.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("harness", choices=["claude", "opencode"])
    args = parser.parse_args()
    scratch = Path(tempfile.mkdtemp(prefix="ac52-resume-", dir=os.environ.get("AC52_PROBE_TMPDIR"))).resolve()
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
        models = call(["opencode", "models", "--standalone"], checkout, env, scratch / "models")
        if MODEL not in models.stdout.splitlines():
            save(scratch / "result.json", json.dumps({"harness": args.harness, "passed": False, "stage": "precheck"}))
            print("STOP precheck: %s not listed (exit %s)" % (MODEL, models.returncode))
            return 1
        print("Pass precheck: %s listed" % MODEL, flush=True)
        session = "ses_" + uuid.uuid4().hex[:26]
        common = ["opencode", "run", "--standalone", "--format", "json", "--model", MODEL, "--session", session]
        first = call(common + [FIRST_PROMPT], checkout, env, scratch / "first")
        print("First turn exit: %s" % first.returncode, flush=True)
        print(first.stderr, file=sys.stderr, flush=True)
        results = {"first": opencode_checks(first, session, "habit，是否继续 resume probe？\n" + str(checkout),
                                            source / "govern-repository")}
        turns = {"first": stored_models(session, checkout, env, scratch / "export-first")}
        print("First turn models: %s" % turns["first"], flush=True)
        results["first"]["every assistant message on the pinned model"] = bool(turns["first"]) and set(
            turns["first"]) == {MODEL}
        record = {"harness": args.harness, "session": session, "prompts": [FIRST_PROMPT], "models": turns,
                  "checks": results}
        if report("first", results["first"]):
            prompt = "继续 resume probe"
            second = call(common + [prompt], checkout, env, scratch / "second")
            print("Resumed turn exit: %s" % second.returncode, flush=True)
            print(second.stderr, file=sys.stderr, flush=True)
            results["second"] = opencode_checks(second, session, nonce)
            turns["second"] = stored_models(session, checkout, env, scratch / "export-second")
            print("Stored models after the second turn: %s" % turns["second"], flush=True)
            results["second"]["every assistant message on the pinned model"] = len(
                turns["second"]) > len(turns["first"]) and set(turns["second"]) == {MODEL}
            results["second"]["marker absent from the prompt"] = nonce not in prompt
            record["prompts"].append(prompt)
            report("second", results["second"])
        results["isolation"] = {"zero stand-in calls": not environment.read_log(str(scratch))}
        report("isolation", results["isolation"])
        passed = "second" in results and all(all(checks.values()) for checks in results.values())
        record["passed"] = passed
        save(scratch / "result.json", json.dumps(record, ensure_ascii=False, indent=2))
        print("PASS diagnostic assertions" if passed else "STOP diagnostic failed")
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
