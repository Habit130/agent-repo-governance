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

The record's confirmed values are not drift. Nothing here writes.
"""

from govlib import GovernError, checkout, compare, github, harness, render, store as stores, target

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
    """The GitHub state's departures from #41 §7, as the agent account reads it."""
    found = {"rulesets": [], "other_rulesets": [], "branch_protection": None, "settings": [], "unreadable": [],
             "owner_script_checks": list(BLIND_SPOT)}
    rulesets, message = github.rulesets(gh, repository)
    if rulesets is None:
        found["unreadable"].append("rulesets: %s" % message)
        rulesets = []
    rules = gh.get(github.branch_rules_path(repository, branch))
    applying = set(rule.get("ruleset_id") for rule in rules.data or []) if rules.ok else set()
    if not rules.ok:
        found["unreadable"].append("the rules on %s: %s" % (branch, rules.message))
    chosen = set()
    for name in target.RULESET_NAMES:
        candidates = [r for r in rulesets if r.get("name") == name and r.get("target") == "branch"]
        if not candidates:
            found["rulesets"].append({"name": name, "state": "missing", "differences": []})
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
    return found


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
    gh = github.GitHub(env)
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
    elif mode == "Initialize" and found["present"]:
        drift["reason"] = "the record doesn't parse, so its version is unknown and nothing is compared"
        drift["in_files"] = True
        drift["in_github"] = False
    else:
        drift["reason"] = "no record, so nothing to compare" if mode == "Initialize" else "the record is newer than the machine"
    facts["drift"] = drift
    facts["outcome"] = outcome(mode, found, drift)
    return facts, 1 if mode == "stop" else 0


def outcome(mode, found, drift):
    """What #25 does next, by mode and drift."""
    if mode == "stop":
        return "stop"
    if mode == "Initialize":
        return "rebuild as at Initialize" if found["present"] else "Initialize"
    if mode == "Upgrade":
        return "Upgrade, handling any drift with the version change"
    if drift["in_files"] and drift["in_github"]:
        return (
            "Repair through the Upgrade flow, restoring the drift in files, "
            "then a ready owner-script command for the drift in GitHub state"
        )
    if drift["in_files"]:
        return "Repair through the Upgrade flow, restoring the drift in files"
    if drift["in_github"]:
        return "a ready owner-script command, then re-verification"
    return "no drift: one Chinese message, nothing written"
