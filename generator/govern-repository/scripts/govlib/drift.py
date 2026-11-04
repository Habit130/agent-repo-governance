"""The mode and the drift report (#44 §6.2, ADR 0019), before any write.

The mode: no record is Initialize; an older record is Upgrade; the same version is Repair; a
newer record stops. A record that doesn't parse is rebuilt as at Initialize, its confirmed
values proposed again.

Drift is checked against the record's version and its confirmed values, never against the
installed version:

- files: exact comparison, content and mode, of every fixed file and fixed part, and the
  record up to `confirmed:` (`compare.py`), with the default branch as GitHub names it, so a
  renamed default branch shows as drift;
- markers: in each fixed part's file, the markers missing, duplicated or out of order, and
  whether the generator's text between them is intact: the version's text between its
  markers, found unchanged as one run of lines in the file. Intact markers are restored;
  otherwise the file's governance part is rebuilt as at Initialize;
- GitHub state: the rulesets and readable settings, read as the agent account and compared
  with #41 §7 plus the record's confirmed checks (`target.py`). The Actions setting, secret
  scanning, push protection and the Actions event policy are the owner script's to check.
  Every read gets one retry. One that stays failed goes under `unreadable` and never reads as
  something the run knows: an unread rulesets list isn't three missing rulesets, and an unread
  rules list leaves "applies to the default branch" unknown. `unplaced` names an inactive
  ruleset the agent read but can't place on the default branch, which no retry or owner-script
  run would settle. Either keeps the outcome from reading as no drift.

The record's confirmed values are not drift. Nothing here writes.
"""

from govlib import GovernError, checkout, compare, github, harness, render, store as stores, target

OWNER_SCRIPT = ".github/governance/owner.sh"
AT_TARGET_LINE = "这条命令在 GitHub 已是目标状态时不写入任何内容，否则把 GitHub 恢复到目标状态。"
LIST_UNREAD_LINE = "规则集列表没有读到，所以脚本可能删除作用于默认分支、但本次运行没有事先列出的规则集；它的报告会写明删除了哪些。"
BLIND_SPOT = (
    "the Actions setting that lets Actions create or approve pull requests",
    "secret scanning",
    "push protection",
    "the Actions event policy",
)


def decide(found, installed, released):
    """(mode, reason, change notes' versions) from the record's facts and the installed version."""
    if not found["present"]:
        return "Initialize", "the repository has no record", []
    if not found["parses"]:
        return "Initialize", "the record doesn't parse, so it is rebuilt as at Initialize", []
    version = found["version"]
    if version > installed:
        return "stop", "the record is at version %d, newer than the installed version %d; run the install" % (version, installed), []
    if version < installed:
        return "Upgrade", "the record is at version %d, older than the installed version %d" % (version, installed), [
            v for v in released if v > version
        ]
    return "Repair", "the record is at the installed version %d" % installed, []


def _block_lines(text, where):
    start, end = render.find_block(text, where)
    lines = text[start:end].splitlines(True)
    return lines[1:-1]


def markers(text, template_text, where):
    """A fixed part's marker problems and whether the generator's text between them is intact."""
    begins, ends = [], []
    for number, line in enumerate((text or "").splitlines(), 1):
        if render.BEGIN.match(line):
            begins.append(number)
        elif line == render.END:
            ends.append(number)
    problems = []
    if not begins or not ends:
        problems.append("missing")
    if len(begins) > 1 or len(ends) > 1:
        problems.append("duplicated")
    if begins and ends and len(begins) == len(ends) and any(b > e for b, e in zip(begins, ends)):
        problems.append("out of order")
    inner = "".join(_block_lines(template_text, where))
    intact = text is not None and bool(inner) and inner in text
    return {"begin_lines": begins, "end_lines": ends, "problems": problems, "generator_text_intact": intact}


def github_drift(gh, repository, data, branch, checks):
    """The GitHub state's departures from #41 §7, as the agent account reads it through `gh`."""
    found = {"rulesets": [], "other_rulesets": [], "branch_protection": None, "settings": [], "unreadable": [],
             "rulesets_unread": False, "owner_script_checks": list(BLIND_SPOT)}
    rulesets, message = github.rulesets(gh, repository)
    if rulesets is None:
        found["unreadable"].append("rulesets: %s" % message)
        found["rulesets_unread"] = True
        rulesets = []
    rules = gh.get(github.branch_rules_path(repository, branch))
    applying = set(rule.get("ruleset_id") for rule in rules.data or []) if rules.ok else None
    if not rules.ok:
        found["unreadable"].append("the rules on %s: %s" % (branch, rules.message))
    chosen = set()
    for name in target.RULESET_NAMES:
        candidates = [r for r in rulesets if r.get("name") == name and r.get("target") == "branch"]
        if not candidates:
            state = "unread" if found["rulesets_unread"] else "missing"
            found["rulesets"].append({"name": name, "state": state, "differences": []})
            continue
        ruleset = candidates[0]
        chosen.add(ruleset.get("id"))
        if "unreadable" in ruleset:
            found["rulesets"].append({"name": name, "id": ruleset.get("id"), "state": "unreadable", "differences": []})
            found["unreadable"].append("ruleset %s: %s" % (name, ruleset["unreadable"]))
            continue
        differences = target.ruleset_differences(ruleset, name, checks)
        found["rulesets"].append(
            {"name": name, "id": ruleset.get("id"), "state": "differs" if differences else "in place", "differences": differences}
        )
    for ruleset in rulesets:
        if ruleset.get("id") in chosen:
            continue
        if "unreadable" in ruleset:
            found["unreadable"].append("ruleset %s: %s" % (ruleset.get("name"), ruleset["unreadable"]))
        found["other_rulesets"].append(
            {
                "name": ruleset.get("name"),
                "id": ruleset.get("id"),
                "target": ruleset.get("target"),
                "enforcement": ruleset.get("enforcement"),
                "applies_to_default_branch": github.ruleset_applies(ruleset, branch, applying),
            }
        )
    response = gh.get(github.branch_path(repository, branch))
    if response.ok:
        enabled = bool(((response.data or {}).get("protection") or {}).get("enabled"))
        found["branch_protection"] = {"classic_protection": enabled}
    else:
        found["unreadable"].append("the default branch %s: %s" % (branch, response.message))
    differing, unreadable = target.settings_differences(data)
    if unreadable:
        again = gh.get("repos/%s" % repository)
        if again.ok:
            differing, unreadable = target.settings_differences(again.data or {})
    found["settings"] = differing
    found["unreadable"].extend("setting %s" % key for key in unreadable)
    found["drift"] = bool(
        any(r["state"] in ("missing", "differs") for r in found["rulesets"])
        or any(r["applies_to_default_branch"] for r in found["other_rulesets"])
        or (found["branch_protection"] or {}).get("classic_protection")
        or differing
    )
    found["uncertain"] = [r["name"] for r in found["rulesets"] if r["state"] == "unreadable"] + [
        r["name"] for r in found["other_rulesets"] if r["applies_to_default_branch"] is None
    ]
    unread_details = set(r.get("id") for r in rulesets if "unreadable" in r)
    found["unplaced"] = [
        r["name"] for r in found["other_rulesets"]
        if r["applies_to_default_branch"] is None and r["enforcement"] != "active" and r["id"] not in unread_details
    ]
    return found


def owner_script_changed(source, older, newer):
    """Whether the owner script, which holds the target state, differs between two versions."""
    texts = []
    for version in (older, newer):
        if not any(e["path"] == OWNER_SCRIPT for e in source.manifest(version)["templates"]):
            return True
        texts.append(render.template_source(source, version, OWNER_SCRIPT))
    return texts[0] != texts[1]


def handover(mode, owner_changed, required_checks_changed, in_github, unreadable, rulesets_unread):
    """Whether habit gets the ready owner-script command, and the lines that say what it does.

    Always at Initialize. At Upgrade and Repair, when the owner script, the target state or the
    required checks changed, GitHub state drifted, or a read stayed failed.
    An inactive ruleset the agent can't place never gets it.
    """
    command = mode == "Initialize" or any((owner_changed, required_checks_changed, in_github, unreadable))
    lines = [AT_TARGET_LINE] if command else []
    if command and rulesets_unread:
        lines.append(LIST_UNREAD_LINE)
    return {"owner_command": command, "lines": lines}


def file_drift(source, root, repository, branch, version):
    """Exact comparison and the markers, at the record's version."""
    compared = compare.compare(source, root, repository, branch, version=version)
    manifest = source.manifest(version)
    values = render.check_values(version, repository, branch)
    marker_report = []
    for entry in manifest["templates"]:
        if entry["class"] != "fixed part":
            continue
        data = checkout.read(root, entry["path"])
        try:
            text = data.decode("utf-8") if data is not None else None
        except UnicodeDecodeError:
            text = None
        where = "version %d's template for %s" % (version, entry["path"])
        report = markers(text, render.template_text(source, version, entry, values), where)
        report["path"] = entry["path"]
        if data is None:
            report["problems"] = ["file missing"]
        if report["problems"]:
            report["repair"] = "restore the markers" if report["generator_text_intact"] else "rebuild as at Initialize"
            marker_report.append(report)
    damaged = set(report["path"] for report in marker_report)
    files = [d for d in compared["differences"] if not (d["kind"] == "markers" and d["path"] in damaged)]
    return {"differences": files, "markers": marker_report, "checked": compared["checked"]}


def run(worktree, store_root, env=None):
    """The mode and drift facts; exit code 0, or 1 when the mode is stop."""
    judged = harness.require(env)
    root = checkout.toplevel(worktree)
    if root is None:
        raise GovernError("%s isn't inside a git checkout" % worktree)
    repository = checkout.repository(root)
    gh = github.Retried(env)
    data = gh.require("repos/%s" % repository, "the repository")
    branch = data.get("default_branch")
    source = stores.Store(store_root)
    released = source.released()
    if not released:
        raise GovernError("the installed template store has no released version, so the run stops")
    installed = released[-1]
    found = checkout.read_record(root)
    mode, reason, notes = decide(found, installed, released)

    facts = {
        "harness": judged,
        "repository": repository,
        "default_branch": {"github": branch, "checkout": checkout.local_default_branch(root)},
        "installed_version": installed,
        "record": found,
        "mode": mode,
        "reason": reason,
        "change_notes": [dict(source.change_note(v), version=v) for v in notes],
        "skipped_versions": notes[:-1],
    }
    drift = {"checked": False, "record_parses": bool(found.get("parses")) if found["present"] else None}
    if mode in ("Upgrade", "Repair"):
        version = found["version"]
        drift.update(file_drift(source, root, repository, branch, version))
        drift["version"] = version
        drift["github"] = github_drift(gh, repository, data, branch, found["confirmed"]["required_checks"])
        drift["checked"] = True
        drift["in_files"] = bool(drift["differences"] or drift["markers"])
        drift["in_github"] = drift["github"]["drift"]
        drift["owner_script_changed"] = mode == "Upgrade" and owner_script_changed(source, version, installed)
    elif mode == "Initialize" and found["present"]:
        drift["reason"] = "the record doesn't parse, so its version is unknown and nothing is compared"
        drift["in_files"] = True
        drift["in_github"] = False
    else:
        drift["reason"] = "no record, so nothing to compare" if mode == "Initialize" else "the record is newer than the machine"
    facts["drift"] = drift
    drift["handover"] = handover_from(facts, False)
    facts["outcome"] = outcome(mode, found, drift)
    return facts, 1 if mode == "stop" else 0


def outcome(mode, found, drift):
    """What #25 does next, by mode and drift."""
    if mode == "stop":
        return "stop"
    if mode == "Initialize":
        return "rebuild as at Initialize" if found["present"] else "Initialize"
    github_facts = drift.get("github") or {}
    unread = github_facts.get("unreadable")
    if mode == "Upgrade":
        changing = "Upgrade, handling any drift with the version change"
        return changing + "; the unread items named beside a ready owner-script command, then one more read" if unread else changing
    if drift["in_files"] and drift["in_github"]:
        chosen = (
            "Repair through the Upgrade flow, restoring the drift in files, "
            "then a ready owner-script command for the drift in GitHub state"
        )
    elif drift["in_files"]:
        chosen = "Repair through the Upgrade flow, restoring the drift in files"
    elif drift["in_github"]:
        chosen = "a ready owner-script command, then re-verification"
    elif unread:
        return "not proven: the unread items named beside a ready owner-script command, then one more read"
    elif github_facts.get("unplaced"):
        return "not proven: the inactive rulesets named, with no command, nothing written"
    else:
        return "no drift: one Chinese message, nothing written"
    return chosen + "; the unread items named beside it, then one more read" if unread else chosen


def handover_from(facts, required_checks_changed):
    """The handover rule on a `mode` report, with what only the answered run knows."""
    drift = facts.get("drift") or {}
    github_facts = drift.get("github") or {}
    return handover(facts.get("mode"), drift.get("owner_script_changed"), required_checks_changed, drift.get("in_github"),
                    github_facts.get("unreadable"), github_facts.get("rulesets_unread"))
