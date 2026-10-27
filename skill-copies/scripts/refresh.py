#!/usr/bin/env python3
"""Refresh every skill copy, upstream's LICENSE and provenance.json from one upstream commit.

The copies are the relied-on skills of the template store's highest version, `govern-repository`
aside, each found at `skills/<group>/<name>/` at the commit. Everything is read and checked
before anything is written, so a refusal writes nothing. Exit 0 when written, 2 on a refusal.

    python3 skill-copies/scripts/refresh.py --commit <sha>
"""

import argparse
import json
import os
import shutil
import sys

sys.dont_write_bytecode = True

import copylib  # noqa: E402
from copylib import storedform  # noqa: E402


def plan(upstream, commit, names):
    copies = []
    for name in names:
        path = upstream.locate(commit, name)
        if path is None:
            raise copylib.CopyError("relied-on skill %s isn't at skills/<group>/%s at %s" % (name, name, commit[:12]))
        files, added = copylib.expected_copy(upstream, commit, path)
        copies.append((name, path, files, added))
    return copies, upstream.file(commit, copylib.LICENSE)


def write(root, commit, copies, license_file):
    skills = os.path.join(root, copylib.SKILLS)
    if os.path.islink(skills) or (os.path.lexists(skills) and not os.path.isdir(skills)):
        raise copylib.CopyError("%s is not a directory" % skills)
    for name in (copylib.LICENSE, copylib.PROVENANCE):
        storedform.check_target(root, name)
    if os.path.isdir(skills):
        shutil.rmtree(skills)
    entries = []
    for name, path, files, added in copies:
        for rel, (mode, data) in sorted(files.items()):
            storedform.write_file(root, "%s/%s/%s" % (copylib.SKILLS, name, storedform.encode(rel)), data, mode)
        entries.append(
            {"name": name, "repository": copylib.REPOSITORY, "path": path, "commit": commit, "codex_key_added": added}
        )
    license_mode, license_data = license_file
    storedform.write_file(root, copylib.LICENSE, license_data, license_mode)
    provenance = {
        "license": {"repository": copylib.REPOSITORY, "path": copylib.LICENSE, "commit": commit},
        "copies": entries,
    }
    data = (json.dumps(provenance, indent=2) + "\n").encode("utf-8")
    storedform.write_file(root, copylib.PROVENANCE, data, "100644")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", required=True, help="the upstream commit, as a full SHA")
    parser.add_argument("--store", default=copylib.STORE, help="the template store whose relied-on list names the copies")
    copylib.add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        if not copylib.is_sha(args.commit):
            raise copylib.CopyError("--commit %r isn't a full lowercase SHA" % args.commit)
        names = copylib.relied_on(args.store)
        with copylib.Upstream(copylib.source_of(copylib.REPOSITORY, args.upstream), [args.commit]) as upstream:
            copies, license_file = plan(upstream, args.commit, names)
        write(os.path.realpath(args.copies), args.commit, copies, license_file)
    except (copylib.CopyError, storedform.StoredFormError, OSError) as error:
        print("REFUSED refresh: %s" % error)
        return 2
    for name, path, files, added in copies:
        print("copied %s: %d files from %s%s" % (name, len(files), path, ", Codex key added" if added else ""))
    print("copied %s at %s" % (copylib.LICENSE, args.commit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
