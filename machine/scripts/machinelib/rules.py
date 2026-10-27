"""The machine rules (#44 §8 step 2, #15, #24): deny entries against `ghm` and Actions-secret writes.

- **Claude Code**, `~/.claude/settings.json`: `permissions.deny` holds `Bash(<command> *)`
  entries. A trailing ` *` also matches the bare command, and deny wins over every allow
  (Claude Code's permissions documentation).
- **OpenCode**, `opencode.json`: `permission.bash` maps patterns to `deny`, where `*` matches
  any text and the last matching pattern wins, so missing entries go after habit's own. The
  bare `ghm` gets its own entry, since a bare command matching `ghm *` isn't documented.
- **Codex**: `governance.rules` holds partial prefix rules, owned whole by the install and
  checked with `codex execpolicy check --rules <file> <command...>`. That command takes the
  command's words with no `--`, exits 0 whatever the decision, and prints JSON whose
  `decision` is `forbidden` for a match and absent when nothing matches.

Listing secret names, `gh secret list`, stays allowed everywhere. A secret write through
`gh api` stays an instruction: denying it would deny every `gh api` call.
"""

import fnmatch
import json
import os
import shutil
import time

FORBIDDEN_COMMANDS = ("ghm", "gh secret set", "gh secret delete", "gh secret remove")
LISTING = "gh secret list"

CLAUDE_DENY = ["Bash(%s *)" % command for command in FORBIDDEN_COMMANDS]
OPENCODE_DENY = ["ghm", "ghm *", "gh secret set *", "gh secret delete *", "gh secret remove *"]

CODEX_RULES = """\
# Owned whole by the agent-repo-governance install, which rewrites this file at every run.
# Partial rules (#24): they match a command's leading words only.
prefix_rule(
    pattern = ["ghm"],
    decision = "forbidden",
    justification = "ghm is habit's maintainer account alias; agents never call it.",
    match = [["ghm", "pr", "merge", "1"]],
)
prefix_rule(
    pattern = ["gh", "secret", ["set", "delete", "remove"]],
    decision = "forbidden",
    justification = "Agents never create, overwrite or delete Actions secrets; listing names stays allowed.",
    match = [["gh", "secret", "set", "TOKEN"], ["gh", "secret", "delete", "TOKEN"], ["gh", "secret", "remove", "TOKEN"]],
    not_match = [["gh", "secret", "list"]],
)
"""

# The commands `codex execpolicy check` must forbid, and the one it must leave alone.
CODEX_PROBES = (
    (["ghm", "pr", "merge", "1"], True),
    (["gh", "secret", "set", "TOKEN"], True),
    (["gh", "secret", "delete", "TOKEN"], True),
    (["gh", "secret", "remove", "TOKEN"], True),
    (["gh", "secret", "list"], False),
)


class SettingsError(Exception):
    pass


def read_json(path):
    """A settings file's parsed object, None when the file is absent, or SettingsError."""
    if not os.path.lexists(path):
        return None
    try:
        with open(path, "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        raise SettingsError("无法解析：%s" % error)
    if not isinstance(data, dict):
        raise SettingsError("顶层不是 JSON 对象")
    return data


def _claude_missing(data):
    permissions = data.get("permissions", {})
    if not isinstance(permissions, dict):
        raise SettingsError("permissions 不是对象")
    deny = permissions.get("deny", [])
    if not isinstance(deny, list):
        raise SettingsError("permissions.deny 不是列表")
    return [entry for entry in CLAUDE_DENY if entry not in deny], []


def _claude_add(data, missing):
    data.setdefault("permissions", {}).setdefault("deny", []).extend(missing)


def _opencode_missing(data):
    permission = data.get("permission", {})
    if not isinstance(permission, dict):
        raise SettingsError("permission 不是对象，无法逐条添加")
    bash = permission.get("bash", {})
    if not isinstance(bash, dict):
        raise SettingsError("permission.bash 不是对象，无法逐条添加")
    missing = [pattern for pattern in OPENCODE_DENY if pattern not in bash]
    conflicting = ["%s = %s" % (pattern, bash[pattern]) for pattern in OPENCODE_DENY
                   if pattern in bash and bash[pattern] != "deny"]
    return missing, conflicting


def _opencode_add(data, missing):
    bash = data.setdefault("permission", {}).setdefault("bash", {})
    for pattern in missing:
        bash[pattern] = "deny"


HARNESSES = {
    "Claude Code": (_claude_missing, _claude_add),
    "OpenCode": (_opencode_missing, _opencode_add),
}


def missing_entries(harness, data):
    """(missing deny entries, existing entries for them that aren't deny) for a parsed settings object."""
    return HARNESSES[harness][0](data if data is not None else {})


def listing_denied(harness, data):
    """The entries that would also deny `gh secret list`, which must stay allowed."""
    if data is None:
        return []
    if harness == "Claude Code":
        deny = (data.get("permissions") or {}).get("deny") or []
        found = []
        for entry in deny:
            if not isinstance(entry, str):
                continue
            if entry == "Bash":
                found.append(entry)
            elif entry.startswith("Bash(") and entry.endswith(")"):
                pattern = entry[5:-1]
                if pattern.endswith(":*"):
                    pattern = pattern[:-2] + " *"
                if fnmatch.fnmatchcase(LISTING, pattern) or (pattern.endswith(" *") and LISTING == pattern[:-2]):
                    found.append(entry)
        return found
    bash = (data.get("permission") or {}).get("bash")
    if isinstance(bash, str):
        return ["permission.bash = %s" % bash] if bash == "deny" else []
    if not isinstance(bash, dict):
        return []
    last = None
    for pattern, action in bash.items():
        if fnmatch.fnmatchcase(LISTING, pattern):
            last = (pattern, action)
    return ["%s = deny" % last[0]] if last and last[1] == "deny" else []


def backup_path(path):
    """A dated backup beside the file that never replaces an earlier one."""
    stamp = time.strftime("%Y%m%d")
    candidate = "%s.governance-backup-%s" % (path, stamp)
    serial = 1
    while os.path.lexists(candidate):
        serial += 1
        candidate = "%s.governance-backup-%s-%d" % (path, stamp, serial)
    return candidate


def apply_deny(harness, path):
    """Add the missing deny entries to one settings file; return (added, backup, conflicting).

    Other entries are never changed. The file is backed up before a write, and a file that
    doesn't parse raises SettingsError, unwritten.
    """
    data = read_json(path)
    missing, conflicting = missing_entries(harness, data)
    if not missing:
        return [], None, conflicting
    backup = None
    if data is None:
        data = {}
    else:
        backup = backup_path(path)
        shutil.copy2(path, backup)
    HARNESSES[harness][1](data, missing)
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w") as handle:
        handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return missing, backup, conflicting


def codex_decision(output):
    """The decision `codex execpolicy check` printed, or None when no rule matched."""
    data = json.loads(output)
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    return data.get("decision")


def check_codex_rules(home, codex):
    """Problems `codex execpolicy check` finds with the installed rules, in Chinese; empty when they hold."""
    problems = []
    for command, forbidden in CODEX_PROBES:
        code, out, err = home.run([codex, "execpolicy", "check", "--rules", home.codex_rules] + command)
        shown = " ".join(command)
        if code != 0:
            problems.append("`%s` 检查失败：%s" % (shown, (err or out).strip()))
            continue
        try:
            decision = codex_decision(out)
        except ValueError:
            problems.append("`%s` 的输出不是预期的 JSON：%s" % (shown, out.strip()))
            continue
        if forbidden and decision != "forbidden":
            problems.append("`%s` 未被禁止（decision：%s）" % (shown, decision))
        if not forbidden and decision == "forbidden":
            problems.append("`%s` 被禁止了，但列出名称应保持允许" % shown)
    return problems
