"""The owner script's probes (#44 §11): the state matches the target, a rerun writes nothing, and the private skip.

habit runs the owner script twice through `prepare`'s commands, which save each report as an
input. Run `live.py probe` once between the two runs: `owner-state` then remembers each
ruleset's `updated_at`, which `owner-rerun` compares after the second run.
"""

import json
import re

from probes import Probe, ProbeError, Result

import target_state

# The report's items (owner.sh), and the statuses each may end in on a first run.
FIRST_RUN = (
    ("账户", {"通过"}),
    ("副本", {"通过"}),
    ("记录", {"通过"}),
    ("Actions 可运行工作流", {"已就位"}),
    ("Gate 规则集", {"已设置", "已就位"}),
    ("Merge 规则集", {"已设置", "已就位"}),
    ("History 规则集", {"已设置", "已就位"}),
    ("仅 squash 合并", {"已设置", "已就位"}),
    ("合并后删除 head 分支", {"已设置", "已就位"}),
    ("auto-merge 关闭", {"已设置", "已就位"}),
    ("Actions 不能创建或批准 PR", {"已设置", "已就位"}),
)
# By visibility: secret protection and the event policy. A public repository's policy may
# be reported missing when GitHub's API can't create it (CRIT-9), and habit sets it once.
BY_VISIBILITY = {
    "public": (
        ("secret scanning", {"已设置", "已就位"}),
        ("push protection", {"已设置", "已就位"}),
        ("pull_request_target 事件策略", {"已设置", "已就位", "缺失"}),
    ),
    "private": (
        ("secret scanning", {"已跳过"}),
        ("push protection", {"已跳过"}),
        ("pull_request_target 事件策略", {"已跳过"}),
    ),
}
CREDENTIAL = re.compile(r"\b(?:gh[opsur]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")
_LINE = re.compile(r"^\[([^\]]+)\] (.+?)：(.*)$")
RULES_IN_EFFECT = ("deletion", "non_fast_forward", "pull_request", "required_status_checks", "update")


def report_items(text):
    """{subject: (status, detail)} from an owner-script report, and its last line."""
    items = {}
    for line in text.splitlines():
        match = _LINE.match(line)
        if match:
            items.setdefault(match.group(2), (match.group(1), match.group(3)))
    lines = [line for line in text.splitlines() if line.strip()]
    return items, (lines[-1] if lines else "")


def _expected(context):
    return FIRST_RUN + (("%s 的经典分支保护" % context.default_branch, {"已就位", "已移除"}),) + BY_VISIBILITY[context.visibility]


def _report_results(context, text, label, allowed_for):
    items, last = report_items(text)
    results = [Result("the %s prints no credential" % label, not CREDENTIAL.search(text), "checked for gh token shapes")]
    failed = [subject for subject, (status, _) in items.items() if status == "未通过"]
    results.append(Result("the %s has no failed item" % label, not failed, ", ".join(failed) or "none failed"))
    for subject, allowed in _expected(context):
        status, detail = items.get(subject, (None, "not reported"))
        allowed = allowed_for(subject, allowed)
        results.append(Result("the %s reports %s as %s" % (label, subject, " or ".join(sorted(allowed))), status in allowed,
                              "%s：%s" % (status, detail) if status else detail))
    return results, items, last


def _owner_command(context):
    from govlib import owner

    return owner.command(context.repository)


def owner_report_commands(context):
    return [("owner_report", "the owner-script command, first run", _owner_command(context))]


def owner_report(context):
    results, items, last = _report_results(context, context.input("owner_report"), "first run's report", lambda s, a: a)
    if context.visibility == "private":
        detail = items.get("secret scanning", ("", ""))[1]
        results.append(Result("the private skip says why", "私有仓库" in detail, detail or "no reason given"))
    results.append(Result("the first run's report ends with its write count", last.startswith("写入 "), last))
    return results


def owner_rerun_commands(context):
    return [("owner_rerun", "the owner-script command again, after the first probe run", _owner_command(context))]


def owner_rerun(context):
    def in_place(subject, allowed):
        return {"通过"} if allowed == {"通过"} else (allowed & {"已就位", "已跳过", "缺失"})

    results, items, last = _report_results(context, context.input("owner_rerun"), "rerun's report", in_place)
    wrote = [subject for subject, (status, _) in items.items() if status in ("已设置", "已移除")]
    results.append(Result("the rerun's report sets and removes nothing", not wrote, ", ".join(wrote) or "nothing written"))
    results.append(Result("the rerun's report counts no write", last.startswith("写入 0 项"), last))
    before = context.recall("rulesets_after_first_run")
    if before is None:
        raise ProbeError("no ruleset snapshot from the first run: run `live.py probe` with owner-state between habit's two runs")
    now = dict((str(ruleset["id"]), ruleset.get("updated_at")) for ruleset in _rulesets(context))
    results.append(Result("the rerun left every ruleset's updated_at unchanged", now == before,
                          "before %s, after %s" % (json.dumps(before, sort_keys=True), json.dumps(now, sort_keys=True))))
    return results


def _rulesets(context):
    listed = context.api("repos/%s/rulesets?includes_parents=false&per_page=100" % context.repository) or []
    return [context.api("repos/%s/rulesets/%s" % (context.repository, item["id"])) for item in listed]


def _applies_to_default_branch(ruleset, branch):
    if ruleset.get("target") != "branch":
        return False
    include = ((ruleset.get("conditions") or {}).get("ref_name") or {}).get("include") or []
    return any(p in ("~ALL", "~DEFAULT_BRANCH", "refs/heads/" + branch, branch, "refs/heads/*", "refs/heads/**") for p in include)


def owner_state(context):
    rulesets = _rulesets(context)
    if context.recall("rulesets_after_first_run") is None:
        context.remember("rulesets_after_first_run", dict((str(r["id"]), r.get("updated_at")) for r in rulesets))
    by_name = dict((ruleset.get("name"), ruleset) for ruleset in rulesets)
    results = []
    for name in target_state.RULESET_NAMES:
        body = target_state.target_ruleset(name, context.confirmed["required_checks"])
        actual = by_name.get(name)
        if actual is None:
            results.append(Result("the %s ruleset exists" % name, False, "no ruleset named %s" % name))
            continue
        differences = target_state.ruleset_differences(actual, body)
        shown = "bypass_actors compared" if "bypass_actors" in actual else "bypass_actors hidden from the agent; the owner report compares them"
        results.append(Result("the %s ruleset matches the target" % name, not differences, "; ".join(differences) or shown))
    others = [r for r in rulesets if r.get("name") not in target_state.RULESET_NAMES and _applies_to_default_branch(r, context.default_branch)]
    results.append(Result("no other ruleset applies to %s" % context.default_branch, not others,
                          ", ".join("%s (id %s)" % (r.get("name"), r.get("id")) for r in others) or "none"))
    rules = context.api("repos/%s/rules/branches/%s" % (context.repository, context.default_branch)) or []
    types = sorted(set(rule.get("type") for rule in rules))
    missing = [kind for kind in RULES_IN_EFFECT if kind not in types]
    results.append(Result("Gate's and Merge's rules are in effect on %s" % context.default_branch, not missing,
                          "in effect: %s" % ", ".join(types) + ("; missing: %s" % ", ".join(missing) if missing else "")))
    repo = context.api("repos/%s" % context.repository)
    visible = dict((key, repo[key]) for key in target_state.TARGET_SETTINGS if key in repo)
    if visible:
        wrong = dict((key, value) for key, value in visible.items() if value != target_state.TARGET_SETTINGS[key])
        results.append(Result("the merge settings the agent can read match the target", not wrong,
                              json.dumps(wrong or visible, sort_keys=True)))
    return results


SECRET_COMMAND = (
    "/bin/bash -c 'export GH_CONFIG_DIR=\"$HOME/.config/gh-maintainer\"; "
    "unset GH_TOKEN GITHUB_TOKEN GH_ENTERPRISE_TOKEN GITHUB_ENTERPRISE_TOKEN; r=%s; "
    "echo \"== PATCH repos/$r security_and_analysis\"; "
    "printf %%s \"{\\\"security_and_analysis\\\":{\\\"secret_scanning\\\":{\\\"status\\\":\\\"enabled\\\"},"
    "\\\"secret_scanning_push_protection\\\":{\\\"status\\\":\\\"enabled\\\"}}}\" "
    "| gh api --method PATCH \"repos/$r\" --input - --jq \"{visibility, security_and_analysis}\"; echo \"exit=$?\"; "
    "echo \"== GET repos/$r\"; gh api \"repos/$r\" --jq \"{visibility, security_and_analysis}\"'"
)


def secret_commands(context):
    return [("secret_response", "GitHub's response to enabling secret protection on the private sandbox, as its owner",
             SECRET_COMMAND % context.repository)]


def secret_response(context):
    text = context.input("secret_response")
    sections = re.split(r"(?m)^== (PATCH|GET) .*$", text)
    parts = dict(zip(sections[1::2], sections[2::2]))
    try:
        state = json.loads(parts.get("GET", "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ProbeError("the GET section of secret_response holds no JSON: %r" % parts.get("GET", "")[:200])
    analysis = state.get("security_and_analysis") or {}
    enabled = [key for key in ("secret_scanning", "secret_scanning_push_protection")
               if (analysis.get(key) or {}).get("status") == "enabled"]
    patch = " ".join(parts.get("PATCH", "").split())[:400]
    return [
        Result("the private sandbox is private", state.get("visibility") == "private", "visibility: %s" % state.get("visibility")),
        Result("GitHub's response to the secret-protection settings, recorded", bool(patch), patch or "no PATCH response"),
        Result("secret scanning and push protection stay off on the private sandbox", not enabled,
               "enabled: %s" % ", ".join(enabled) if enabled else "security_and_analysis: %s" % json.dumps(analysis, sort_keys=True)),
        Result("GitHub's response prints no credential", not CREDENTIAL.search(text), "checked for gh token shapes"),
    ]


def no_commands(context):
    return []


PROBES = (
    Probe("owner-report", ("public", "private"), ("owner_report",), owner_report_commands, owner_report),
    Probe("owner-state", ("public", "private"), (), no_commands, owner_state),
    Probe("owner-rerun", ("public", "private"), ("owner_rerun",), owner_rerun_commands, owner_rerun),
    Probe("owner-private-secret", ("private",), ("secret_response",), secret_commands, secret_response),
)
