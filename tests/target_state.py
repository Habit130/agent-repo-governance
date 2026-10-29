"""The GitHub target state (#41 §7) as the tests read it, written from the spec, not from the owner script.

Seam D's recorded writes (`tests/suites/owner_support.py`) and the live check's probes
(`tests/live/probes/`) both compare against it, so the owner script is checked against #41
rather than against itself.
"""

import copy
import json

# #41 §7. The GitHub Actions app's id is what GET /apps/github-actions answered on
# 2026-10-28; the admin role's actor id is the RepositoryRole id GitHub's own exported
# rulesets use for admins (github/docs at 57f571f), since no documentation states it.
ACTIONS_APP = 15368
ADMIN_ROLE = 5
RULESET_NAMES = ("Gate", "Merge", "History")
ADMIN_BYPASS = [{"actor_id": ADMIN_ROLE, "actor_type": "RepositoryRole", "bypass_mode": "always"}]


def target_ruleset(name, checks=()):
    """One of #41 §7's three rulesets, as the body the owner script sends."""
    if name == "Gate":
        required = [{"context": "governance-gate", "integration_id": ACTIONS_APP}]
        required += [{"context": check} for check in checks if check != "governance-gate"]
        return {
            "name": "Gate",
            "target": "branch",
            "enforcement": "active",
            "bypass_actors": [],
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "rules": [
                {"type": "deletion"},
                {"type": "non_fast_forward"},
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 0,
                        "dismiss_stale_reviews_on_push": False,
                        "require_code_owner_review": False,
                        "require_last_push_approval": False,
                        "required_review_thread_resolution": False,
                        "allowed_merge_methods": ["squash"],
                    },
                },
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "strict_required_status_checks_policy": False,
                        "do_not_enforce_on_create": False,
                        "required_status_checks": required,
                    },
                },
            ],
        }
    if name == "Merge":
        return {
            "name": "Merge",
            "target": "branch",
            "enforcement": "active",
            "bypass_actors": copy.deepcopy(ADMIN_BYPASS),
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "rules": [{"type": "update", "parameters": {"update_allows_fetch_and_merge": False}}],
        }
    if name == "History":
        return {
            "name": "History",
            "target": "branch",
            "enforcement": "active",
            "bypass_actors": copy.deepcopy(ADMIN_BYPASS),
            "conditions": {"ref_name": {"include": ["~ALL"], "exclude": []}},
            "rules": [{"type": "non_fast_forward"}],
        }
    raise KeyError(name)


TARGET_SETTINGS = {
    "allow_squash_merge": True,
    "allow_merge_commit": False,
    "allow_rebase_merge": False,
    "delete_branch_on_merge": True,
    "allow_auto_merge": False,
}
# #41 §7's Actions event policy, changed by habit's decision on #55's finding: on a public
# repository, pull_request_target allowed for the gate's workflow only.
GATE_WORKFLOW = ".github/workflows/governance-gate.yml"
EVENT_POLICY = {
    "name": "governance-gate",
    "enforcement": "active",
    "conditions": {"workflow_path": {"include": [GATE_WORKFLOW], "exclude": []}},
    "rules": [{"type": "restrict_action_events", "parameters": {"allowed_events": ["pull_request_target"]}}],
}
TARGET_SECURITY = {"secret_scanning": "enabled", "secret_scanning_push_protection": "enabled"}
TARGET_WORKFLOW = {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False}


def ruleset_differences(actual, body):
    """What differs between a ruleset as GitHub returns it and its target body, by the body's fields; [] when it matches.

    GitHub's extra fields and parameters don't count, lists compare in any order, and a
    boolean GitHub leaves out reads as false. A rule type the body lacks counts. GitHub hides
    bypass_actors from a non-admin, so it counts only when present.
    """
    found = []
    for key in ("name", "target", "enforcement"):
        if actual.get(key) != body[key]:
            found.append("%s is %r, not %r" % (key, actual.get(key), body[key]))
    ref_name = (actual.get("conditions") or {}).get("ref_name") or {}
    for key in ("include", "exclude"):
        if sorted(ref_name.get(key) or []) != sorted(body["conditions"]["ref_name"][key]):
            found.append("ref_name %s is %r, not %r" % (key, ref_name.get(key), body["conditions"]["ref_name"][key]))
    if "bypass_actors" in actual:
        if _actors(actual["bypass_actors"]) != _actors(body["bypass_actors"]):
            found.append("bypass_actors are %r, not %r" % (actual["bypass_actors"], body["bypass_actors"]))
    rules = dict((rule["type"], rule.get("parameters") or {}) for rule in actual.get("rules") or [])
    wanted = dict((rule["type"], rule.get("parameters") or {}) for rule in body["rules"])
    if sorted(rules) != sorted(wanted):
        found.append("rule types are %s, not %s" % (", ".join(sorted(rules)), ", ".join(sorted(wanted))))
    for kind, parameters in sorted(wanted.items()):
        got = rules.get(kind)
        if got is None:
            continue
        for key, value in sorted(parameters.items()):
            have = got.get(key, False if value is False else None)
            if key == "required_status_checks":
                same = _checks(have or []) == _checks(value)
            elif isinstance(value, list):
                same = sorted(have or []) == sorted(value)
            else:
                same = have == value
            if not same:
                found.append("%s %s is %r, not %r" % (kind, key, have, value))
    return found


def _actors(actors):
    return sorted(json.dumps([a.get("actor_id"), a.get("actor_type"), a.get("bypass_mode")]) for a in actors)


def _checks(checks):
    return sorted(json.dumps([c.get("context"), c.get("integration_id")]) for c in checks)
