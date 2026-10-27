"""The machine check (#44 §9, #26): read-only, one Chinese line per item.

Codex items need the CLI bundled in the ChatGPT app; when it is absent they are skipped,
and the skip is reported. `codex debug prompt-input` prints no warning when the skill list
overflows its budget: Codex shortens descriptions and drops entries silently. So the budget
item compares the listed entries, by name, with the skills Codex would list from the home's
skill roots: a missing one is omitted, and a description cut short is shortened.
"""

import json
import os
import re
import shutil
import tempfile

from machinelib import AGENT, CODEX_APP, GENERATOR, home as homes, rules, skills, state as states

CODEX_ITEMS = ("Codex rules", "Codex skill list")
ITEMS = CODEX_ITEMS + (
    "Codex user-only key",
    "名称冲突",
    "deny entries",
    "links",
    "managed skills",
    "identity",
)

_ENTRY = re.compile(r"^- ([^:\s][^:]*):(.*)\(file: ([^)]*)\)\s*$")


def codex_path(codex):
    """The Codex CLI to use, or None when it is absent."""
    path = codex or CODEX_APP
    return path if os.path.isfile(path) and os.access(path, os.X_OK) else None


def listed_skills(prompt_input):
    """{name: description} from `codex debug prompt-input`'s skills section; None when it has none."""
    data = json.loads(prompt_input)
    texts = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and "<skills_instructions>" in node:
            texts.append(node)

    walk(data)
    if not texts:
        return None
    found = {}
    for text in texts:
        section = text.split("### Available skills", 1)[-1].split("</skills_instructions>", 1)[0]
        for line in section.split("\n"):
            match = _ENTRY.match(line)
            if match:
                found.setdefault(match.group(1).strip(), []).append(match.group(2).strip())
    return found


def _normal(text):
    return " ".join(text.split())


def codex_skills(home):
    """The skills Codex would list for the model, from ~/.agents/skills and ~/.codex/skills."""
    found = []
    for root in (home.skills, os.path.join(home.codex, "skills")):
        found.extend(skill for skill in skills.skills_in(root) if skill.listed_by_codex)
    return found


def budget_problems(home, codex):
    work = tempfile.mkdtemp(prefix="machine-check-")
    try:
        code, out, err = home.run([codex, "debug", "prompt-input", "x"], cwd=work)
    finally:
        shutil.rmtree(work, True)
    if code != 0:
        return ["`codex debug prompt-input` 失败：%s" % (err or out).strip()]
    try:
        listed = listed_skills(out)
    except ValueError:
        return ["`codex debug prompt-input` 的输出不是 JSON"]
    if listed is None:
        return ["`codex debug prompt-input` 的输出里没有 skill 列表"]
    omitted, shortened = [], []
    for skill in codex_skills(home):
        if skill.name not in listed:
            omitted.append(skill.name)
            continue
        full = _normal(skill.meta.get("description", ""))
        shown = _normal(listed[skill.name][0])
        if full and shown != full and (not shown or full.startswith(shown)):
            shortened.append(skill.name)
    problems = []
    if omitted:
        problems.append("超出预算，被省略：%s" % "、".join(sorted(set(omitted))))
    if shortened:
        problems.append("超出预算，描述被截短：%s" % "、".join(sorted(set(shortened))))
    return problems


def _key_problems(home):
    problems = []
    codex_root = os.path.join(home.codex, "skills")
    for root in (home.skills, codex_root):
        for skill in skills.skills_in(root):
            if skill.user_invoked and skill.policy != skills.FALSE:
                where = "%s 里的 " % home.show(codex_root) if root == codex_root else ""
                problems.append("%s%s 缺少 Codex user-only key%s"
                                % (where, skill.dir_name, "（链接的 personal skill）" if skill.linked else ""))
    return problems


def _collision_problems(home, machine_names):
    problems = []
    for skill in skills.skills_in(home.skills):
        if skill.dir_name not in machine_names and skill.name in machine_names:
            problems.append("personal skill %s 与 machine skill %s 同名" % (home.show(skill.path), skill.name))
    for root in home.personal_roots():
        for skill in skills.skills_in(root):
            if skill.name in machine_names or skill.dir_name in machine_names:
                problems.append("personal skill %s 与 machine skill %s 同名" % (home.show(skill.path), skill.name))
    codex_root = os.path.join(home.codex, "skills")
    for skill in skills.skills_in(codex_root):
        if skill.name in machine_names or skill.dir_name in machine_names:
            problems.append("%s 里有 machine skill 的名称 %s，Codex 会列出两次" % (home.show(codex_root), skill.name))
    return problems


def _deny_problems(home):
    problems = []
    for harness, path in (("Claude Code", home.claude_settings), ("OpenCode", home.opencode_settings)):
        try:
            data = rules.read_json(path)
        except rules.SettingsError as error:
            problems.append("%s 的 %s %s" % (harness, home.show(path), error))
            continue
        if data is None:
            problems.append("%s 的 %s 不存在" % (harness, home.show(path)))
            continue
        try:
            missing, conflicting = rules.missing_entries(harness, data)
        except rules.SettingsError as error:
            problems.append("%s 的 %s：%s" % (harness, home.show(path), error))
            continue
        if missing:
            problems.append("%s 缺少 deny entries：%s" % (harness, "、".join(missing)))
        if conflicting:
            problems.append("%s 的这些条目不是 deny：%s" % (harness, "、".join(conflicting)))
        overridden = rules.deny_overridden(harness, data)
        if overridden:
            problems.append("%s 里后面的条目覆盖了 deny：%s" % (harness, "、".join(overridden)))
        denied = rules.listing_denied(harness, data)
        if denied:
            problems.append("%s 也拒绝了 `gh secret list`：%s" % (harness, "、".join(denied)))
    return problems


def link_problem(home, path, target):
    """Why a link isn't in place, or None."""
    if not os.path.lexists(path):
        return "%s 不存在，应链接到 %s" % (home.show(path), home.show(target))
    if not os.path.islink(path):
        return "%s 是真实文件或目录，应链接到 %s" % (home.show(path), home.show(target))
    if os.path.realpath(path) != os.path.realpath(target):
        return "%s 指向 %s，应指向 %s" % (home.show(path), os.readlink(path), home.show(target))
    if not os.path.exists(target):
        return "%s 指向的 %s 不存在" % (home.show(path), home.show(target))
    return None


def _link_problems(home):
    problems = []
    if not os.path.isfile(home.agents_md) or os.path.islink(home.agents_md):
        problems.append("%s 应是真实文件" % home.show(home.agents_md))
    for path, target in home.links():
        problem = link_problem(home, path, target)
        if problem:
            problems.append(problem)
    if os.path.lexists(home.dsh_agents_md):
        problems.append("%s 存在，dsh 会把全局指令加载两次" % home.show(home.dsh_agents_md))
    return problems


def _managed_problems(home):
    try:
        installed = states.load(home)
    except states.StateError as error:
        return [str(error)]
    if installed is None:
        return ["没有 installed state，本机还没有 install"]
    problems = []
    for name, expected in sorted(installed["skills"].items()):
        actual = skills.disk_hash(os.path.join(home.skills, name))
        if actual is None:
            problems.append("%s 不在了" % name)
        elif actual != expected:
            problems.append("%s 与上次 install 写入的内容不同" % name)
    return problems


def _identity_problems(home):
    problems = []
    code, out, err = home.run(["gh", "api", "user"])
    login = user_id = None
    if code == 0:
        try:
            user = json.loads(out)
            login, user_id = user.get("login"), user.get("id")
        except ValueError:
            pass
    if login != AGENT:
        problems.append("gh 应以 agent account %s 操作，实际：%s" % (AGENT, login or (err or out).strip() or "未知"))
    code, out, _ = home.run(["git", "config", "--global", "--get", "user.email"])
    email = out.strip() if code == 0 else ""
    expected = "%s+%s@users.noreply.github.com" % (user_id, AGENT) if user_id else None
    if not expected or email != expected:
        problems.append("git 的全局 commit 身份应是 %s，实际：%s" % (expected or "agent account 的 noreply 地址", email or "未设置"))
    shell = home.env.get("SHELL") or "/bin/zsh"
    # An interactive login shell reads the ghm definition, an alias or a function (#19); the
    # shell names its kind without calling it. No history file and no macOS Terminal session
    # file, so the check writes nothing.
    probe = "whence -w ghm" if os.path.basename(shell) == "zsh" else "type -t ghm"
    code, out, _ = home.run(
        [shell, "-l", "-i", "-c", "unset HISTFILE; " + probe], timeout=30, extra_env={"SHELL_SESSIONS_DISABLE": "1"}
    )
    kind = out.strip().split()[-1] if code == 0 and out.strip() else ""
    if kind not in ("alias", "function"):
        problems.append("交互式登录 shell（%s）里没有把 ghm 定义为 alias 或 function" % shell)
    return problems


def run(home, codex=None, machine_names=None):
    """The check's report. machine_names defaults to the managed skills in the installed state."""
    report = homes.Report("machine check")
    if machine_names is None:
        try:
            installed = states.load(home)
        except states.StateError:
            installed = None
        machine_names = set(installed["skills"]) if installed else set()
    machine_names = set(machine_names) | {GENERATOR}
    found = codex_path(codex)

    def add(item, problems, passed):
        if problems:
            for problem in problems:
                report.add(homes.FAIL, item, problem)
        else:
            report.add(homes.PASS, item, passed)

    if found is None:
        for item in CODEX_ITEMS:
            report.add(homes.SKIP, item, "没有找到 ChatGPT app 自带的 Codex CLI（%s）" % (codex or CODEX_APP))
    else:
        rule_problems = []
        if not os.path.isfile(home.codex_rules):
            rule_problems.append("%s 不存在" % home.show(home.codex_rules))
        else:
            with open(home.codex_rules, encoding="utf-8") as handle:
                if handle.read() != rules.CODEX_RULES:
                    rule_problems.append("%s 与 install 写入的内容不同" % home.show(home.codex_rules))
            rule_problems.extend(rules.check_codex_rules(home, found))
        add("Codex rules", rule_problems, "`codex execpolicy check` 禁止 ghm 和 Actions secret 写入，允许 `gh secret list`")
        add("Codex skill list", budget_problems(home, found), "`codex debug prompt-input` 列出了全部 skill，没有省略或截短")
    add("Codex user-only key", _key_problems(home), "每个 user-invoked skill 都有 Codex user-only key")
    add("名称冲突", _collision_problems(home, machine_names), "没有 personal skill 与 machine skill 同名，~/.codex/skills/ 里也没有")
    add("deny entries", _deny_problems(home), "Claude Code 和 OpenCode 都拒绝 ghm 和 Actions secret 写入，允许 `gh secret list`")
    add("links", _link_problems(home), "四个链接就位，~/.dsh/AGENTS.md 不存在")
    add("managed skills", _managed_problems(home), "managed skills 与 installed state 一致")
    add("identity", _identity_problems(home), "gh 和 git 都是 agent account %s，ghm 已定义" % AGENT)
    return report
