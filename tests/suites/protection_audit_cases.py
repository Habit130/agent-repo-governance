"""Offline pairs for the effective protection audit, from the record and #41's target."""

import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support
from govlib import record, render, store
from owner_support import ok
from standins import environment
from target_state import target_ruleset


BRANCH = "main"
REPO = "Habit130/tally"
RULESET_IDS = {"Gate": 41, "Merge": 42}
RECORD = ".github/governance/record.yml"
FIXTURE = Path(support.FIXTURES, "parsers", "record", "plain-scalars.yml")


def required_checks(rulesets):
    return next(rule["parameters"]["required_status_checks"] for rule in rulesets["Gate"]["rules"]
                if rule["type"] == "required_status_checks")


def protection_cases(confirmed):
    target = {name: target_ruleset(name) for name in RULESET_IDS}
    gate_check, = required_checks(target)
    products = [name for name in dict.fromkeys(confirmed) if name != gate_check["context"]]
    required_checks(target).extend({"context": name} for name in products)
    yield "target", target, None
    for name in products:
        changed = copy.deepcopy(target)
        required_checks(changed).remove({"context": name})
        yield name, changed, f"Gate #41 missing confirmed required check: {name};"
        # #296: a product check can also come from a configured publisher.
        bound = copy.deepcopy(target)
        next(check for check in required_checks(bound) if check["context"] == name)["integration_id"] = 42
        yield f"{name} with publisher", bound, None

    context, publisher = gate_check["context"], gate_check["integration_id"]
    for new_publisher in (None, publisher + 1):
        changed = copy.deepcopy(target)
        pinned = next(check for check in required_checks(changed) if check["context"] == context)
        if new_publisher is None:
            del pinned["integration_id"]
        else:
            pinned["integration_id"] = new_publisher
        yield f"{context} publisher {new_publisher}", changed, f"expected {context}@{publisher}"

    for name, detail in target.items():
        label = f"{name} #{RULESET_IDS[name]}"
        for index, rule in enumerate(detail["rules"]):
            changed = copy.deepcopy(target)
            del changed[name]["rules"][index]
            kind = rule["type"]
            yield f"{name} rule {kind}", changed, f"{label} missing {kind}"

        for field, value in (("target", "tag"), ("enforcement", "disabled")):
            changed = copy.deepcopy(target)
            changed[name][field] = value
            yield f"{name} {field}", changed, f"{label}: {field} {value} (expected {detail[field]})"

        for field, refs in (("include", ["refs/heads/elsewhere"]), ("exclude", [f"refs/heads/{BRANCH}"])):
            changed = copy.deepcopy(target)
            scope = changed[name]["conditions"]["ref_name"]
            scope[field] = refs
            yield f"{name} scope {field}", changed, f"{label} scope {json.dumps(scope, sort_keys=True)}"


def audit_command(tree, rulesets, visibility, record_bytes):
    """Project one ruleset state onto GitHub's list, detail and effective-branch responses."""
    prefix = f"repos/{REPO}"
    listed, effective = [], []
    calls = [ok(["api", "repos/{owner}/{repo}"],
                {"full_name": REPO, "default_branch": BRANCH, "visibility": visibility})]
    for name, detail in rulesets.items():
        ident = RULESET_IDS[name]
        listed.append(dict(id=ident, **{key: detail[key] for key in ("name", "target", "enforcement")}))
        calls.append(ok(["api", f"{prefix}/rulesets/{ident}"], detail))
        scope = detail["conditions"]["ref_name"]
        refs = {"~DEFAULT_BRANCH", f"refs/heads/{BRANCH}"}
        if (detail["enforcement"] == "active" and detail["target"] == "branch"
                and refs.intersection(scope["include"]) and not refs.intersection(scope["exclude"])):
            effective.extend(dict(rule, ruleset_id=ident) for rule in detail["rules"])
    pages = ["api", "--paginate", "--slurp"]
    calls.extend([
        ok(pages + [prefix + "/rulesets?includes_parents=false"], [listed]),
        ok(pages + [f"{prefix}/rules/branches/{BRANCH}"], [effective]),
        ok(["api", f"{prefix}/contents/{RECORD}?ref={BRANCH}"],
           {"encoding": "base64", "content": base64.b64encode(record_bytes).decode("ascii")}),
    ])
    with tempfile.TemporaryDirectory() as scratch:
        recording = Path(scratch, "gh.json")
        recording.write_text(json.dumps({"tool": "gh", "calls": calls}), encoding="utf-8")
        return subprocess.run([sys.executable, ".github/governance/branch_rules.py"], cwd=tree,
                              env=environment.environment(scratch, str(recording)),
                              capture_output=True, text=True)


class GeneratedProtectionAudit(unittest.TestCase):
    def test_record_and_target_facts_on_the_default_branch(self):
        templates = store.Store(support.REAL_STORE)
        confirmed = dict(record.parse(FIXTURE.read_bytes())["confirmed"], review_bots=[])
        for version in templates.versions():
            if version < 6:
                continue
            with tempfile.TemporaryDirectory() as tree:
                render.render(templates, tree, REPO, BRANCH, confirmed, version, allow_unreleased=True)
                record_bytes = Path(tree, RECORD).read_bytes()
                for fact, rulesets, missing in protection_cases(confirmed["required_checks"]):
                    for visibility in ("public", "private"):
                        with self.subTest(version=version, fact=fact, visibility=visibility):
                            run = audit_command(tree, rulesets, visibility, record_bytes)
                            self.assertEqual(run.stderr, "")
                            self.assertEqual(run.returncode, 1 if missing else 0, run.stdout)
                            self.assertEqual("Protection verified" in run.stdout, missing is None)
                            if missing:
                                self.assertIn(missing, run.stdout)
