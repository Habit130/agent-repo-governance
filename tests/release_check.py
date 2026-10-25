"""The release check (#44 §11): compare a PR's base and head trees and print one line per rule.

It is keyed on the change note. A version whose note is on the base is released and frozen;
version directories are consecutive integers from 1; only version 1, while it is the only
version, may lack its note; every note's fields parse; and no fixture is removed or renamed.
Two INFO lines list the fixtures added and changed, which a PR's body or change note
mentions.
"""

import subprocess

from govlib import store

STORE = "generator/govern-repository/store"
FIXTURES = "tests/fixtures"


def tree(repo, rev, prefix):
    """{path below prefix: (mode, blob)} for every file under prefix at rev."""
    out = subprocess.run(
        ["git", "-C", repo, "ls-tree", "-r", "-z", "--full-tree", rev, "--", prefix],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.decode("utf-8")
    files = {}
    for record in out.split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        mode, _, blob = meta.split(" ")
        if path.startswith(prefix + "/"):
            files[path[len(prefix) + 1:]] = (mode, blob)
    return files


def blob(repo, sha):
    return subprocess.run(["git", "-C", repo, "cat-file", "blob", sha], stdout=subprocess.PIPE, check=True).stdout


def versions(files):
    """({version: {path within the version: (mode, blob)}}, [entries that aren't version directories])."""
    found, strays = {}, set()
    for path, entry in files.items():
        top, _, rest = path.partition("/")
        number = store.version_name(top)
        if number is None or not rest:
            strays.add(top)
            continue
        found.setdefault(number, {})[rest] = entry
    return found, sorted(strays)


def rule_frozen(base, head):
    released = sorted(v for v, files in base.items() if store.CHANGE_NOTE in files)
    if not released:
        return True, "no version is released on the base"
    problems = []
    for version in released:
        if version not in head:
            problems.append("version %d is released, and the head removes its directory" % version)
            continue
        before, after = base[version], head[version]
        changed = sorted(p for p in before if p in after and before[p] != after[p])
        removed = sorted(p for p in before if p not in after)
        added = sorted(p for p in after if p not in before)
        for label, paths in (("changes", changed), ("removes", removed), ("adds", added)):
            if paths:
                problems.append("version %d is released, and the head %s %s" % (version, label, ", ".join(paths)))
    if problems:
        return False, "; ".join(problems)
    return True, "released versions %s are byte-identical at the head" % ", ".join(str(v) for v in released)


def rule_consecutive(head, strays):
    numbers = sorted(head)
    problems = []
    if strays:
        problems.append("the store holds %s, which are not version directories" % ", ".join(strays))
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append("the head's versions are %s, not consecutive from 1" % ", ".join(str(v) for v in numbers))
    if problems:
        return False, "; ".join(problems)
    if not numbers:
        return True, "the head has no version directory"
    return True, "the head's versions are %s, consecutive from 1" % ", ".join(str(v) for v in numbers)


def rule_notes(head):
    missing = sorted(v for v, files in head.items() if store.CHANGE_NOTE not in files)
    if missing == [1] and sorted(head) == [1]:
        return True, "only version 1 exists, and it may change until its note is added"
    if missing:
        return False, "version %s has no change note; a version's templates, manifest and note arrive in one PR" % (
            ", ".join(str(v) for v in missing)
        )
    return True, "every version at the head has its change note"


def rule_note_fields(repo, head):
    problems, checked = [], 0
    for version in sorted(head):
        entry = head[version].get(store.CHANGE_NOTE)
        if entry is None:
            continue
        checked += 1
        try:
            store.parse_change_note(blob(repo, entry[1]))
        except store.ChangeNoteError as error:
            problems.append("version %d's change note: %s" % (version, error))
    if problems:
        return False, "; ".join(problems)
    return True, "%d change notes have valid urgency and must-act fields" % checked


def rule_fixtures(base, head):
    gone = sorted(p for p in base if p not in head)
    if gone:
        return False, "the head removes or renames fixtures %s; fixtures are never removed" % ", ".join(
            FIXTURES + "/" + p for p in gone
        )
    return True, "every fixture on the base is still at the head (%d files)" % len(base)


def check(repo, base_rev, head_rev):
    """Return (passed, lines)."""
    base_versions, _ = versions(tree(repo, base_rev, STORE))
    head_versions, strays = versions(tree(repo, head_rev, STORE))
    base_fixtures = tree(repo, base_rev, FIXTURES)
    head_fixtures = tree(repo, head_rev, FIXTURES)
    results = [
        ("frozen", rule_frozen(base_versions, head_versions)),
        ("consecutive", rule_consecutive(head_versions, strays)),
        ("notes", rule_notes(head_versions)),
        ("note-fields", rule_note_fields(repo, head_versions)),
        ("fixtures", rule_fixtures(base_fixtures, head_fixtures)),
    ]
    lines = ["%s %s: %s" % ("PASS" if ok else "FAIL", rule, detail) for rule, (ok, detail) in results]
    added = sorted(FIXTURES + "/" + p for p in head_fixtures if p not in base_fixtures)
    changed = sorted(
        FIXTURES + "/" + p for p in head_fixtures if p in base_fixtures and head_fixtures[p] != base_fixtures[p]
    )
    lines.append("INFO new fixtures: %s" % (", ".join(added) or "none"))
    lines.append("INFO changed fixtures: %s" % (", ".join(changed) or "none"))
    return all(ok for _, (ok, _) in results), lines
