"""Replay GitHub responses against the protection command from rendered review policy."""

import base64
import json
import os
import re
import shlex
import subprocess
import tempfile
from urllib.parse import quote

import owner_support as ow
import support
from materialized_version_support import level_three_section
from standins import environment


def record_text(names):
    header = ("version: 6\nagent_account: agent\nsensitive_paths:\n"
              "confirmed:\n  sensitive_paths:\n  required_checks:\n")
    return header + "".join("    - " + json.dumps(name) + "\n" for name in names)


def replay_branch_rules(self, filename, confirmed_checks=None):
    section = level_three_section(self.text("docs/agents/review.md"), "### Checks first")
    commands = re.findall(r"`(python3 [^`]+)`", section)
    self.assertEqual(len(commands), 1, "Checks first must give the writer the read-only command")
    command = shlex.split(commands[0])
    fixtures = os.path.join(support.FIXTURES, "generator")
    with open(os.path.join(fixtures, filename)) as handle:
        fixture = json.load(handle)
    with open(os.path.join(fixtures, fixture["gate_recording"])) as handle:
        gate = json.load(handle)["ruleset"]
    branch = fixture["branch"]
    listed = [{"id": i, "name": name, "target": "branch", "enforcement": "active"}
              for i, name in ((41, "Gate"), (42, "Merge"), (51, "Other"))]
    for row in fixture["cases"]:
        for visibility in [row["visibility"]] if "visibility" in row else ["PUBLIC", "PRIVATE"]:
            with self.subTest(case=row["name"], visibility=visibility):
                rules = [dict(rule, ruleset_id=row.get("gate_rule_id", 41)) for rule in gate["rules"]]
                check_rule = next(rule for rule in rules if rule["type"] == "required_status_checks")
                if "checks_rule_id" in row:
                    check_rule["ruleset_id"] = row["checks_rule_id"]
                if "checks" in row:
                    check_rule["parameters"] = {"required_status_checks": row["checks"]}
                if "other_checks" in row:
                    rules.append({"type": "required_status_checks", "ruleset_id": 51,
                                  "parameters": {"required_status_checks": row["other_checks"]}})
                rules.append({"type": "update", "ruleset_id": row.get("merge_rule_id", 42)})
                ref = quote(branch, safe="")
                branch_read = ["api", "--paginate", "--slurp", *ow.api("/rules/branches/" + ref)[1:]]
                response = (ow.http_error(branch_read, row["http_error"], row.get("message", "Unavailable"))
                            if "http_error" in row else ow.ok(branch_read, [rules[:2], rules[2:]]))
                gate_meta = dict(listed[0], name=row.get("gate_name", "Gate"), target=row.get("gate_target", "branch"),
                                 enforcement=row.get("gate_enforcement", "active"))
                other_meta = dict(listed[2], name=row.get("other_name", "Other"))
                calls = [
                    ow.ok(["api", "repos/{owner}/{repo}"],
                          {"full_name": "Habit130/tally", "visibility": visibility.lower(), "default_branch": branch}),
                    ow.ok(["api", "--paginate", "--slurp", "repos/Habit130/tally/rulesets?includes_parents=false"],
                          [[gate_meta], [listed[1], other_meta]]),
                    response,
                    ow.ok(ow.api("/rulesets/41"), {"conditions": {"ref_name": {
                        "include": row.get("gate_scope", ["~DEFAULT_BRANCH"]), "exclude": []}}}),
                    ow.ok(ow.api("/rulesets/42"), {"conditions": {"ref_name": {
                        "include": ["~DEFAULT_BRANCH"], "exclude": []}}}),
                ]
                if "confirmed_checks" in fixture or confirmed_checks is not None:
                    names = row.get("confirmed_checks", fixture.get("confirmed_checks", confirmed_checks))
                    record_call = ow.api("/contents/.github/governance/record.yml?ref=" + ref)
                    if "record_error" in row:
                        calls.append(ow.http_error(record_call, row["record_error"], "Unavailable"))
                    else:
                        record = row.get("record_text", record_text(names))
                        encoded = base64.b64encode(record.encode("utf-8")).decode("ascii")
                        calls.append(ow.ok(record_call, {"encoding": "base64", "content": encoded}))
                root = tempfile.mkdtemp(dir=self.tmp)
                recording = os.path.join(root, "gh.json")
                with open(recording, "w") as handle:
                    json.dump({"tool": "gh", "calls": calls}, handle)
                env = environment.environment(os.path.join(root, "scratch"), recording)
                run = subprocess.run(command, cwd=self.dest, env=env, capture_output=True, text=True)
                self.assertEqual(run.stderr, "")
                self.assertEqual(run.returncode, row["exit"], run.stdout)
                self.assertIn(branch, run.stdout)
                self.assertIn(visibility.lower(), run.stdout)
                for evidence in row["evidence"]:
                    self.assertIn(evidence, run.stdout)
                self.assertEqual("Protection verified" in run.stdout, row["exit"] == 0)
