"""#41 §7's GitHub target state, as drift reads it: the rulesets and the readable settings.

The owner script applies the target; this module only compares what the agent account reads
with it (#44 §6.2), and Seam A checks it against `tests/target_state.py`, written from the
spec, so drift is checked against #41 rather than against itself. The Actions setting,
secret scanning, push protection and the Actions event policy are the owner script's to
check, a blind spot #25 accepts as amended by #38.
"""

import json

# GET /apps/github-actions answered this id on 2026-10-28; the admin role's actor id is the
# one GitHub's own exported rulesets use (github/docs at 57f571f).
ACTIONS_APP = 15368
ADMIN_ROLE = 5
GATE_CHECK = "governance-gate"
RULESET_NAMES = ("Gate", "Merge", "History")

SETTINGS = {
    "allow_squash_merge": True,
    "allow_merge_commit": False,
    "allow_rebase_merge": False,
    "delete_branch_on_merge": True,
    "allow_auto_merge": False,
}


def _admin_bypass():
    return [{"actor_id": ADMIN_ROLE, "actor_type": "RepositoryRole", "bypass_mode": "always"}]


def ruleset(name, checks=()):
    """One of the three rulesets, for the record's confirmed checks."""
    if name == "Gate":
        required = [{"context": GATE_CHECK, "integration_id": ACTIONS_APP}]
        required += [{"context": check} for check in checks if check != GATE_CHECK]
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
            "bypass_actors": _admin_bypass(),
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "rules": [{"type": "update", "parameters": {"update_allows_fetch_and_merge": False}}],
        }
    if name == "History":
        return {
            "name": "History",
            "target": "branch",
            "enforcement": "active",
            "bypass_actors": _admin_bypass(),
            "conditions": {"ref_name": {"include": ["~ALL"], "exclude": []}},
            "rules": [{"type": "non_fast_forward"}],
        }
    raise KeyError(name)


def _sorted(items):
    return sorted(json.dumps(item, sort_keys=True) for item in items)


def _check_keys(checks):
    return sorted(json.dumps([c.get("context"), c.get("integration_id")]) for c in checks or [])


def ruleset_differences(actual, name, checks=()):
    """How a ruleset as the agent account reads it departs from the target; [] when it doesn't.

    Only the fields the target declares count: GitHub adds its own (`required_reviewers`,
    `require_extra_approval_for_unattributed_changes`), lists compare in any order, and a
    boolean it leaves out reads as false. It returns `bypass_actors` as null to an account
    without admin, and null is unreadable, not drift.
    """
    body = ruleset(name, checks)
    found = []
    for key in ("target", "enforcement"):
        if actual.get(key) != body[key]:
            found.append("%s is %r, not %r" % (key, actual.get(key), body[key]))
    ref_name = (actual.get("conditions") or {}).get("ref_name") or {}
    for key in ("include", "exclude"):
        if sorted(ref_name.get(key) or []) != sorted(body["conditions"]["ref_name"][key]):
            found.append("ref_name %s is %r, not %r" % (key, ref_name.get(key) or [], body["conditions"]["ref_name"][key]))
    if actual.get("bypass_actors") is not None:
        actors = [{k: a.get(k) for k in ("actor_id", "actor_type", "bypass_mode")} for a in actual["bypass_actors"]]
        if _sorted(actors) != _sorted(body["bypass_actors"]):
            found.append("bypass_actors are %r, not %r" % (actors, body["bypass_actors"]))
    rules = dict((rule.get("type"), rule.get("parameters") or {}) for rule in actual.get("rules") or [])
    wanted = dict((rule["type"], rule.get("parameters") or {}) for rule in body["rules"])
    if sorted(rules) != sorted(wanted):
        found.append("rule types are %s, not %s" % (", ".join(sorted(rules)), ", ".join(sorted(wanted))))
    for kind, parameters in sorted(wanted.items()):
        if kind not in rules:
            continue
        for key, value in sorted(parameters.items()):
            have = rules[kind].get(key, False if value is False else None)
            if key == "required_status_checks":
                same = _check_keys(have) == _check_keys(value)
            elif isinstance(value, list):
                same = sorted(have or []) == sorted(value)
            else:
                same = have == value
            if not same:
                found.append("%s %s is %r, not %r" % (kind, key, have, value))
    return found


def settings_differences(repository):
    """[(setting, found, target)] for the readable settings that differ, and the unreadable ones."""
    differing, unreadable = [], []
    for key, value in sorted(SETTINGS.items()):
        if repository.get(key) is None:
            unreadable.append(key)
        elif repository[key] != value:
            differing.append({"setting": key, "found": repository[key], "target": value})
    return differing, unreadable
