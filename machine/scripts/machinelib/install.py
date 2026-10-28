"""The install (#44 §8, #26): one internal entry that takes a source tree and a home directory.

The ready command fetches the latest commit of `origin`'s default branch afresh and passes
that tree and habit's home; suites pass a test-built tree and a throwaway home. The install
moves forward only: before writing anything it refuses a source commit that the installed
state's commit isn't an ancestor of. Then it runs §8's steps in order:

1. machine skills: take over same-name skills (silently when identical, listed when not),
   remove their entries from the `skills` CLI's lock file, restore and list any managed
   skill changed since the last write, and remove skills dropped from the set. It writes no
   Codex user-only key: machine skills carry theirs in the source tree, and a personal skill
   is never written, nor anything through a link inside one; the machine check only reports
   a personal skill missing the key (#44 §8, changed by #70);
2. machine rules (`rules.py`);
3. links, created where absent, a real file or a foreign link reported and never overwritten;
4. the installed state, and a copy of `machine/` at `~/.agents/governance/machine`, from
   which habit runs the machine check and the list on their own;
5. the machine check; 6. the governed-repository list; 7. whether the copies' upstream has
   newer commits, as a read-only report.
"""

import json
import os
import shutil

from machinelib import MachineError, check, governed, home as homes, rules, skills, state as states

PROVENANCE = "skill-copies/provenance.json"


def _remove(path):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def _replace_dir(home, target, files):
    """Write files as a new directory at target, through a staging directory outside every skill root."""
    staging = os.path.join(home.staging, os.path.basename(target))
    if os.path.lexists(staging):
        _remove(staging)
    if not os.path.isdir(home.staging):
        os.makedirs(home.staging)
    skills.write_dir(staging, files)
    if os.path.lexists(target):
        old = staging + ".old"
        if os.path.lexists(old):
            _remove(old)
        os.rename(target, old)
        _remove(old)
    parent = os.path.dirname(target)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    os.rename(staging, target)


def _refuse_older(home, source, commit):
    try:
        installed = states.load(home)
    except states.StateError as error:
        raise MachineError("%s；install 未写入任何内容" % error)
    if installed and installed["commit"] != commit and not skills.is_ancestor(source, installed["commit"], commit):
        raise MachineError(
            "本机已安装 %s，而源码树的 %s 不比它新（install 只向前移动）；install 未写入任何内容"
            % (installed["commit"], commit)
        )
    return installed


def _machine_skills(home, report, skill_set, installed):
    managed = dict(installed["skills"]) if installed else {}
    written = {}
    for name in sorted(skill_set):
        files = skill_set[name]
        target = os.path.join(home.skills, name)
        new_hash = skills.content_hash(files)
        linked = os.path.islink(target)
        current = None if linked else skills.disk_hash(target)
        if name in managed:
            if current != managed[name]:
                report.add(homes.NOTE, "machine skills", "%s 在上次 install 后被改动或删除，已恢复" % name)
        elif os.path.lexists(target):
            if linked or current != new_hash:
                report.add(homes.NOTE, "machine skills", "接管同名 skill %s：内容不同，已替换" % name)
        if linked or current != new_hash:
            _replace_dir(home, target, files)
        written[name] = new_hash
    for name in sorted(set(managed) - set(skill_set)):
        target = os.path.join(home.skills, name)
        edited = os.path.lexists(target) and skills.disk_hash(target) != managed[name]
        if os.path.lexists(target):
            _remove(target)
        report.add(homes.NOTE, "machine skills", "%s 已不在 machine skill set 里，已移除%s"
                   % (name, "（它在上次 install 后有本地改动）" if edited else ""))
    report.add(homes.PASS, "machine skills", "%d 个 machine skills 就位：%s" % (len(written), "、".join(sorted(written))))
    return written


def _lock_file(home, report, names):
    path = home.lock
    if not os.path.lexists(path):
        return
    try:
        with open(path, "rb") as handle:
            lock = json.loads(handle.read().decode("utf-8"))
        entries = lock["skills"]
        if not isinstance(entries, dict):
            raise ValueError("skills is not an object")
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.add(homes.NOTE, "lock file", "%s 无法解析，未修改：%s" % (home.show(path), error))
        return
    taken = sorted(name for name in entries if name in names)
    if not taken:
        return
    backup = rules.backup_path(path)
    shutil.copy2(path, backup)
    for name in taken:
        del entries[name]
    with open(path, "rb") as handle:
        ending = "\n" if handle.read().endswith(b"\n") else ""
    rules.write_text(path, json.dumps(lock, indent=2, ensure_ascii=False) + ending)
    report.add(homes.NOTE, "lock file", "已从 %s 移除被接管的条目：%s（备份 %s）"
               % (home.show(path), "、".join(taken), home.show(backup)))


def _machine_rules(home, report, codex):
    for harness, path in (("Claude Code", home.claude_settings), ("OpenCode", home.opencode_settings)):
        subject = "%s settings" % harness
        try:
            added, backup, conflicting = rules.apply_deny(harness, path)
        except rules.SettingsError as error:
            report.add(homes.NOTE, subject, "%s %s；未写入" % (home.show(path), error))
            continue
        if added:
            report.add(homes.NOTE, subject, "已向 %s 添加 deny entries：%s%s"
                       % (home.show(path), "、".join(added), "（备份 %s）" % home.show(backup) if backup else "（新建）"))
        if conflicting:
            report.add(homes.NOTE, subject, "这些已有条目不是 deny，未改动：%s" % "、".join(conflicting))
    current = None
    if os.path.isfile(home.codex_rules):
        with open(home.codex_rules, encoding="utf-8") as handle:
            current = handle.read()
    if current != rules.CODEX_RULES:
        parent = os.path.dirname(home.codex_rules)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        rules.write_text(home.codex_rules, rules.CODEX_RULES)
        report.add(homes.NOTE, "Codex rules", "已写入 %s" % home.show(home.codex_rules))
    found = check.codex_path(codex)
    if found is None:
        report.add(homes.SKIP, "Codex rules", "没有找到 Codex CLI，未用 `codex execpolicy check` 验证")
        return
    problems = rules.check_codex_rules(home, found)
    for problem in problems:
        report.add(homes.FAIL, "Codex rules", problem)
    if not problems:
        report.add(homes.PASS, "Codex rules", "`codex execpolicy check` 验证通过")


def _links(home, report):
    for path, target in home.links():
        if not os.path.lexists(path):
            if not os.path.exists(target):
                report.add(homes.NOTE, "links", "%s 不存在，未创建 %s" % (home.show(target), home.show(path)))
                continue
            parent = os.path.dirname(path)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            os.symlink(target, path)
            report.add(homes.NOTE, "links", "已创建 %s -> %s" % (home.show(path), home.show(target)))
            continue
        problem = check.link_problem(home, path, target)
        if problem:
            report.add(homes.NOTE, "links", "%s；未覆盖" % problem)
    if os.path.lexists(home.dsh_agents_md):
        report.add(homes.NOTE, "links", "%s 存在，未删除；dsh 会把全局指令加载两次" % home.show(home.dsh_agents_md))


def _upstream(home, report, source):
    try:
        with open(os.path.join(source, *PROVENANCE.split("/"))) as handle:
            provenance = json.load(handle)
        entry = provenance["license"]
        repository, commit = entry["repository"], entry["commit"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.add(homes.FAIL, "upstream", "无法读取 %s：%s" % (PROVENANCE, error))
        return
    code, out, err = home.run(
        ["gh", "api", "repos/%s/compare/%s...HEAD" % (repository, commit), "--jq", "{ahead_by, status}"]
    )
    try:
        facts = json.loads(out) if code == 0 else None
        ahead = facts["ahead_by"]
    except (ValueError, KeyError, TypeError):
        report.add(homes.NOTE, "upstream", "无法比较 %s 与 %s 的最新 commit：%s" % (repository, commit[:12], (err or out).strip()))
        return
    if ahead:
        report.add(homes.NOTE, "upstream", "%s 比 skill copies 记录的 %s 新 %d 个 commit；是否更新由 habit 决定"
                   % (repository, commit[:12], ahead))
    else:
        report.add(homes.NOTE, "upstream", "%s 没有比 %s 更新的 commit" % (repository, commit[:12]))


def run(source, home, codex=None):
    """Install from source into home; return the reports, install first. Raises MachineError on a refusal."""
    source = os.path.realpath(source)
    commit = skills.source_commit(source)
    installed = _refuse_older(home, source, commit)
    skill_set = skills.machine_skill_set(source)
    tools = skills.tracked(source, skills.MACHINE_SOURCE)

    report = homes.Report("install %s" % commit)
    written = _machine_skills(home, report, skill_set, installed)
    _lock_file(home, report, set(skill_set))
    _machine_rules(home, report, codex)
    _links(home, report)
    _replace_dir(home, home.tools, tools)
    states.save(home, commit, written)
    if os.path.isdir(home.staging) and not os.listdir(home.staging):
        os.rmdir(home.staging)
    report.add(homes.PASS, "installed state", "已记录 commit %s 和 %d 个 managed skills；machine check 和 list 可从 %s 单独运行"
               % (commit, len(written), home.show(home.tools)))
    reports = [report, check.run(home, codex, set(skill_set)), governed.run(home)]
    upstream = homes.Report("upstream")
    _upstream(home, upstream, source)
    return reports + [upstream]
