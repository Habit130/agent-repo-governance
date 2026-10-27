#!/usr/bin/env python3
"""Verify every skill copy and upstream's LICENSE against upstream at their recorded commits.

It fetches each recorded commit read-only and confirms every copy is byte-identical with its
upstream directory, file set and modes included, apart from a Codex user-only key added to a
user-invoked skill that lacks it. It prints one PASS or FAIL line per copy and for the license,
one line per added key, then a summary. Exit 0 when all pass, 1 on a difference, 2 on a refusal.
CI has no network, so Execution runs it and Acceptance reruns it (#44 §10).

    python3 skill-copies/scripts/verify.py
"""

import argparse
import os
import sys

sys.dont_write_bytecode = True

import copylib  # noqa: E402


def check_copy(upstream, root, entry):
    """(problems, whether the copy should carry an added Codex key) for one provenance entry."""
    commit, path = entry["commit"], entry["path"]
    try:
        expected, added = copylib.expected_copy(upstream, commit, path)
    except copylib.CopyError as error:
        return [str(error)], False
    problems = []
    if added != entry["codex_key_added"]:
        problems.append(
            "provenance records codex_key_added %s, but upstream %s"
            % (str(entry["codex_key_added"]).lower(), "lacks the Codex key" if added else "needs no added Codex key")
        )
    copy_dir = os.path.join(root, copylib.SKILLS, entry["name"])
    if not os.path.isdir(copy_dir):
        return problems + ["no copy at %s/%s" % (copylib.SKILLS, entry["name"])], added
    try:
        problems += copylib.differences(expected, copylib.copy_files(copy_dir))
    except copylib.CopyError as error:
        problems.append(str(error))
    return problems, added


def check_license(upstream, root, entry):
    try:
        mode, want = upstream.file(entry["commit"], entry["path"])
    except copylib.CopyError as error:
        return [str(error)]
    path = os.path.join(root, copylib.LICENSE)
    if not os.path.isfile(path) or os.path.islink(path):
        return ["no %s beside the copies" % copylib.LICENSE]
    with open(path, "rb") as handle:
        data = handle.read()
    return copylib.differences({copylib.LICENSE: (mode, want)}, {copylib.LICENSE: (copylib.storedform.mode_of(path), data)})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    copylib.add_arguments(parser)
    args = parser.parse_args(argv)
    root = os.path.realpath(args.copies)
    try:
        provenance = copylib.load_provenance(root)
        sources = [provenance["license"]] + provenance["copies"]
        wanted = {}
        for entry in sources:
            wanted.setdefault(entry["repository"], set()).add(entry["commit"])
        upstreams = {}
        try:
            for repository, commits in sorted(wanted.items()):
                upstreams[repository] = copylib.Upstream(copylib.source_of(repository, args.upstream), commits)
            lines, failed, added_keys = run(upstreams, root, provenance)
        finally:
            for upstream in upstreams.values():
                upstream.close()
    except (copylib.CopyError, OSError) as error:
        print("REFUSED verify: %s" % error)
        return 2
    for line in lines:
        print(line)
    for name in added_keys:
        print("added Codex key: %s" % name)
    if not added_keys:
        print("added Codex key: none")
    if failed:
        print("FAIL verify: %d of the checks above differ from upstream" % failed)
        return 1
    print("PASS verify: %d copies and the license are byte-identical with upstream, Codex keys aside" % len(provenance["copies"]))
    return 0


def run(upstreams, root, provenance):
    lines, failed, added_keys = [], 0, []
    listed = set()
    for entry in provenance["copies"]:
        listed.add(entry["name"])
        problems, added = check_copy(upstreams[entry["repository"]], root, entry)
        where = "%s@%s %s" % (entry["repository"], entry["commit"][:12], entry["path"])
        if problems:
            failed += 1
            lines.append("FAIL copy %s: %s, against %s" % (entry["name"], "; ".join(problems), where))
        else:
            lines.append("PASS copy %s: byte-identical with %s" % (entry["name"], where))
            if added:
                added_keys.append(entry["name"])
    unlisted = [name for name in copylib.copies_on_disk(root) if name not in listed]
    if unlisted:
        failed += 1
        lines.append("FAIL copies: %s on disk without a provenance entry" % ", ".join(unlisted))
    entry = provenance["license"]
    problems = check_license(upstreams[entry["repository"]], root, entry)
    where = "%s@%s %s" % (entry["repository"], entry["commit"][:12], entry["path"])
    if problems:
        failed += 1
        lines.append("FAIL license: %s, against %s" % ("; ".join(problems), where))
    else:
        lines.append("PASS license: %s is byte-identical with %s" % (copylib.LICENSE, where))
    return lines, failed, added_keys


if __name__ == "__main__":
    sys.exit(main())
