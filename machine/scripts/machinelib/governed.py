"""The governed-repository list (#44 §9, #26, #36, #40): read-only, as the agent account, in Chinese.

It lists every repository of the maintainer account that the agent account can see, reads
the record on each default branch, and skips both sandbox repositories by name. It never
calls `ghm`. The installed template store supplies the released versions, urgency and action notes.
"""

import json
import os
from urllib.parse import quote

from machinelib import AGENT, GENERATOR, MAINTAINER, RECORD_PATH, SANDBOXES, home as homes, state as states

URGENCY_ORDER = ("when convenient", "urgent")


def installed_store(home):
    from govlib import store

    return store.Store(os.path.join(home.skills, GENERATOR, "store"))


def _record(home, repository, branch):
    """Return (record bytes or None, read failed). A missing record is expected."""
    path = "repos/%s/contents/%s?ref=%s" % (repository, RECORD_PATH, quote(branch, safe=""))
    code, out, err = home.run(["gh", "api", path, "-H", "Accept: application/vnd.github.raw"], binary=True)
    if code == 0:
        return out, False
    return None, "HTTP 404" not in err


def _misses(home, repository):
    code, out, err = home.run(
        ["gh", "issue", "list", "--repo", repository, "--label", "miss", "--state", "open", "--json", "number", "--limit", "1000"]
    )
    if code != 0:
        return None
    try:
        return len(json.loads(out))
    except ValueError:
        return None


def run(home):
    from govlib import record, secrets, store as stores

    report = homes.Report("governed-repository list")
    code, out, _ = home.run(["gh", "api", "user"])
    login = None
    if code == 0:
        try:
            identity = json.loads(out)
        except ValueError:
            identity = None
        if isinstance(identity, dict):
            login = identity.get("login")
    if login != AGENT:
        if isinstance(login, str) and login:
            # An unterminated key in the login must not consume the list outcome that follows it.
            detail = "gh 应以 agent account %s 运行，实际：%s" % (AGENT, secrets.redact(homes.shown_identifier(login)))
        else:
            detail = "无法确认 gh 是否以 agent account %s 运行" % AGENT
        report.add(homes.FAIL, "account", detail + "；列表未生成")
        return report

    try:
        installed = states.load(home)
    except states.StateError as error:
        installed = None
        report.add(homes.FAIL, "installed state", str(error))
    commit = installed["commit"] if installed else None
    source = installed_store(home)
    try:
        released = source.released()
        installed_version = released[-1] if released else None
        notes = {version: source.change_note(version) for version in released}
    except stores.StoreError as error:
        released, installed_version, notes = [], None, {}
        report.add(homes.FAIL, "installed store", str(error))
    report.add(
        homes.NOTE,
        "header",
        "installed commit %s；installed version %s"
        % (commit or "无（尚未 install）", installed_version if installed_version is not None else "无（store 里没有已发布版本）"),
    )

    code, out, _ = home.run(
        ["gh", "repo", "list", MAINTAINER, "--limit", "1000", "--json", "nameWithOwner,isPrivate,defaultBranchRef"]
    )
    try:
        repositories = json.loads(out) if code == 0 else None
    except ValueError:
        repositories = None
    if not isinstance(repositories, list):
        report.add(homes.FAIL, "repositories", "无法列出 %s 的仓库" % MAINTAINER)
        return report

    governed = 0
    for entry in sorted(repositories, key=lambda item: item.get("nameWithOwner", "")):
        name = entry.get("nameWithOwner")
        if name in SANDBOXES:
            continue
        branch = (entry.get("defaultBranchRef") or {}).get("name")
        if not name or not branch:
            continue
        data, failed = _record(home, name, branch)
        if failed:
            report.add(homes.FAIL, homes.shown_identifier(name), "读取 record 失败")
            continue
        if data is None:
            continue
        governed += 1
        misses = _misses(home, name)
        parts = []
        try:
            version = record.parse(data)["version"]
        except record.RecordError:
            version = None
            parts.append("record 无法解析，运行 generator 修复")
        if version is not None:
            parts.append("版本 %d" % version)
            if installed_version is None or version > installed_version:
                parts.append("record 比本机新，先更新本机")
            else:
                missing = [v for v in released if v > version]
                if missing:
                    urgency = max((notes[v]["urgency"] for v in missing), key=URGENCY_ORDER.index)
                    parts.append("缺少版本 %s，最高紧急度 %s" % ("、".join(str(v) for v in missing), urgency))
                    action_notes = [
                        "版本 %d（%s）" % (v, os.path.join(source.version_dir(v), stores.CHANGE_NOTE))
                        for v in missing if notes[v]["must_act"] == "yes"
                    ]
                    parts.append("版本说明要求 habit 操作：" + ("、".join(action_notes) or "无"))
                else:
                    parts.append("已是最新版本")
        parts.append("未关闭 miss record %s 条" % ("?" if misses is None else misses))
        if entry.get("isPrivate"):
            parts.append("私有")
        report.add(homes.NOTE, homes.shown_identifier(name), "；".join(parts))
    if not governed:
        report.add(homes.NOTE, "repositories", "没有找到 governed repository")
    return report
