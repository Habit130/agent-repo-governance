#!/usr/bin/env python3
"""List what changed per skill copy between the recorded commit and a newer upstream commit, in plain Chinese.

The output is ready for an update PR's Merge summary: per copied skill, its new place, its
description, whether habit alone starts it, and each file added, removed or changed with its
line counts and up to ten of its changed lines quoted; then the unchanged skills and the license. It reads files only; no model judges
them. Exit 0 with the list, 2 on a refusal.

    python3 skill-copies/scripts/changes.py --to <newer sha>
"""

import argparse
import difflib
import os
import sys

sys.dont_write_bytecode = True

import copylib  # noqa: E402


def description(skill_md):
    for line in copylib.front_matter(skill_md):
        if line.startswith("description:"):
            return line[len("description:"):].strip()
    return None


# Changed lines quoted per file, so the Merge summary can say what changed, not only how much.
QUOTED = 10


def changed_lines(old, new):
    """(lines added, lines removed) between two files' texts."""
    added, removed = [], []
    old_lines = old.decode("utf-8", "replace").splitlines()
    new_lines = new.decode("utf-8", "replace").splitlines()
    for line in difflib.unified_diff(old_lines, new_lines, lineterm="", n=0):
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    return added, removed


def quoted(label, lines):
    lines = [line for line in lines if line.strip()]
    shown = ["    %s：%s" % (label, line) for line in lines[:QUOTED]]
    if len(lines) > QUOTED:
        shown.append("    另有 %d 行%s，未列出" % (len(lines) - QUOTED, label))
    return shown


def lines_of(data):
    return len(data.decode("utf-8", "replace").splitlines())


def skill_changes(upstream, older, newer, entry):
    """The Chinese lines for one copy; empty when nothing changed, None when it's gone."""
    path = upstream.locate(newer, entry["name"])
    if path is None:
        return None
    old = upstream.tree_files(older, entry["path"])
    new = upstream.tree_files(newer, path)
    lines = []
    if path != entry["path"]:
        lines.append("位置从 %s 移到 %s" % (entry["path"], path))
    old_md, new_md = old.get("SKILL.md", ("", b""))[1], new.get("SKILL.md", ("", b""))[1]
    if description(old_md) != description(new_md):
        if description(new_md) is None:
            lines.append("去掉了用途说明（description）")
        else:
            lines.append("用途说明（description）改为：“%s”" % description(new_md))
    was, now = copylib.user_invoked(old_md), copylib.user_invoked(new_md)
    if now and not was:
        codex = new.get(copylib.CODEX_FILE)
        note = "已带 Codex 的 user-only key" if codex and copylib.has_codex_key(codex[1]) else "复制时要补上 Codex 的 user-only key"
        lines.append("改为只由 habit 调用，模型不再自行调用；%s" % note)
    elif was and not now:
        lines.append("不再只由 habit 调用：模型也能自行调用（去掉了 disable-model-invocation）")
    for rel in sorted(set(old) | set(new)):
        if rel not in old:
            lines.append("新增文件 %s（%d 行）" % (rel, lines_of(new[rel][1])))
        elif rel not in new:
            lines.append("删除文件 %s" % rel)
        else:
            if old[rel][1] != new[rel][1]:
                added, removed = changed_lines(old[rel][1], new[rel][1])
                lines.append("%s 有改动：增加 %d 行，删除 %d 行" % (rel, len(added), len(removed)))
                lines.extend(quoted("删除", removed) + quoted("增加", added))
            if old[rel][0] != new[rel][0]:
                lines.append("%s 的可执行权限变了（%s 改为 %s）" % (rel, old[rel][0], new[rel][0]))
    return lines


def report(upstream, provenance, older, newer):
    out, unchanged, changed = [], [], 0
    for entry in provenance["copies"]:
        lines = skill_changes(upstream, older, newer, entry)
        if lines is None:
            changed += 1
            out.append("- %s：在新提交中找不到，上游可能删除或改名了它，需要 habit 决定是否放弃这个 skill。" % entry["name"])
        elif lines:
            changed += 1
            out.append("- %s：" % entry["name"])
            out.extend(line if line.startswith("    ") else "  - %s" % line for line in lines)
        else:
            unchanged.append(entry["name"])
    license_entry = provenance["license"]
    old_license = upstream.file(older, license_entry["path"])
    new_license = upstream.entries(newer, license_entry["path"]).get("")
    if new_license is None:
        license_line = "许可证 LICENSE：在新提交中找不到，需要 habit 决定怎么处理。"
    elif upstream.blob(new_license[1]) != old_license[1]:
        license_line = "许可证 LICENSE：有改动，复制时一并更新，并确认许可条件。"
    else:
        license_line = "许可证 LICENSE：无变化。"
    head = "%s 从 %s 到 %s：%d 个 skill 中 %d 个有变化。" % (
        license_entry["repository"], older[:12], newer[:12], len(provenance["copies"]), changed
    )
    lines = [head] + out
    lines.append("无变化：%s。" % ("、".join(unchanged) if unchanged else "无"))
    lines.append(license_line)
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--to", required=True, help="the newer upstream commit, as a full SHA")
    parser.add_argument("--from", dest="older", help="an older commit in the recorded commit's place (default: recorded)")
    copylib.add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        provenance = copylib.load_provenance(os.path.realpath(args.copies))
        sources = [provenance["license"]] + provenance["copies"]
        repositories = sorted(set(entry["repository"] for entry in sources))
        recorded = sorted(set(entry["commit"] for entry in sources))
        if len(repositories) != 1 or len(recorded) != 1:
            raise copylib.CopyError("the copies must come from one upstream repository and commit")
        older = args.older or recorded[0]
        for commit in (older, args.to):
            if not copylib.is_sha(commit):
                raise copylib.CopyError("%r isn't a full lowercase SHA" % commit)
        with copylib.Upstream(copylib.source_of(repositories[0], args.upstream), [older, args.to]) as upstream:
            if older == args.to or not upstream.is_ancestor(older, args.to):
                raise copylib.CopyError("%s isn't newer than %s" % (args.to[:12], older[:12]))
            lines = report(upstream, provenance, older, args.to)
    except (copylib.CopyError, OSError) as error:
        print("REFUSED changes: %s" % error)
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
