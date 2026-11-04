"""Whether a private repository's rules are in effect (#44 §6.1, §6.7; #53), from #17's reads.

#17's revision found the reads, as the agent account, that changed with the agent's own push,
force-push and merge attempts between GitHub Free and Pro (and in its lapse simulation):

- at Initialize, where no rules exist yet, `GET repos/{r}/rulesets` answers 200 when rulesets
  are available to the repository, and 403 with `PRO_REFUSAL` when they aren't;
- at Upgrade and Repair, and after habit's owner-script run, `GET repos/{r}/rules/branches/{b}`
  answers 200 listing the default branch's active rules, and 403 with `PRO_REFUSAL` when they
  aren't in effect.

`check` takes one of the two reads, through `github.Retried`, and gives one case:

- `available` (Initialize) or `in effect` (otherwise): the read passes. The rules read passes
  only when it lists every rule type of #41 §7's Gate and Merge rulesets (`target.py`);
- `lapsed`: a 403 with `PRO_REFUSAL`. The plan has lapsed: renew the student verification, or
  make the repository public (#41 §6);
- `ruleset missing`: the rules read answers but a Gate or Merge rule type is missing. A ruleset
  is disabled or gone: habit reruns the owner script, which re-enables it;
- `undecided`: anything else after the one retry, a read that stays failed, a 403 without that
  message (rate limits answer 403 too) or an answer that isn't a list of rules. It fails closed
  and never counts as a pass.

Each case carries `issue_line`, the English line the issue records, and `habit_lines`, the
Chinese lines habit hears verbatim, with governance terms and product names in English. Nothing
here writes.
"""

from govlib import MAINTAINER, github, owner, target

PRO_REFUSAL = "Upgrade to GitHub Pro or make this repository public to enable this feature."
GUARDED = ("Gate", "Merge")

LAPSED_ZH = (
    "GitHub 拒绝了这个 private 仓库的 rulesets 读取：%s 的 GitHub Pro 不在生效状态，所以这里的 rulesets 不能用，规则没有生效。" % MAINTAINER,
    "解决办法二选一：续期 GitHub Education 学生认证，或者把这个仓库改为 public。",
)
MISSING_ZH = (
    "这个 private 仓库的默认分支上缺少 %s ruleset 的规则：这个 ruleset 被停用或删除了，规则没有完全生效。",
    "解决办法：habit 运行下面的 owner script 命令，把 ruleset 恢复启用，然后再运行一次治理。",
)
UNDECIDED_ZH = (
    "这次没能判断这个 private 仓库的规则是否生效：GitHub 的回答在重试一次后仍然没读到或读不懂，所以按未通过处理，运行停止。",
    "解决办法：稍后再运行一次治理；在判断出规则生效之前，运行不会继续。",
)


def required_types():
    """{ruleset name: its rule types} for the rulesets whose rules must be in effect."""
    return dict((name, sorted(rule["type"] for rule in target.ruleset(name)["rules"])) for name in GUARDED)


def _refused(response):
    return response.status == 403 and (response.message or "").strip() == PRO_REFUSAL


def _undecided(fact, why):
    fact.update(case="undecided", passed=False, habit_lines=list(UNDECIDED_ZH),
                issue_line="Rules in effect can't be decided on %s: %s; the run fails closed. Remedy: run again later."
                % (fact["repository"], why))
    return fact


def check(gh, repository, branch, initialize):
    """The facts of one read: `read`, `path`, `case`, `passed`, `missing`, the lines and any command."""
    read = "rulesets" if initialize else "rules"
    path = github.rulesets_list_path(repository) if initialize else github.branch_rules_path(repository, branch)
    fact = {"repository": repository, "read": read, "path": path, "missing": [], "owner_command": False}
    response = gh.get(path)
    what = "rulesets read" if initialize else "rules read"
    if _refused(response):
        fact.update(case="lapsed", passed=False, habit_lines=list(LAPSED_ZH),
                    issue_line="Rules not in effect on %s: GitHub refused the agent account's %s with 403 (\"%s\"), so the "
                    "plan has lapsed. Remedy: renew the student verification, or make the repository public."
                    % (repository, what, PRO_REFUSAL))
        return fact
    if not response.ok:
        return _undecided(fact, "the %s stays unread after one retry (%s%s)" % (
            what, "HTTP %s: " % response.status if response.status else "", response.message or "no answer"))
    data = response.data
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        return _undecided(fact, "the %s answered something that isn't a list" % what)
    if initialize:
        fact.update(case="available", passed=True, habit_lines=[],
                    issue_line="Rulesets are available on %s: the rulesets read answers 200." % repository)
        return fact
    if not all(isinstance(item.get("type"), str) for item in data):
        return _undecided(fact, "the rules read lists a rule without a type")
    present = set(item["type"] for item in data)
    wanted = required_types()
    missing = [name for name in GUARDED if not set(wanted[name]) <= present]
    if not missing:
        fact.update(case="in effect", passed=True, habit_lines=[],
                    issue_line="Rules in effect on %s: the rules on %s list every Gate and Merge rule type." % (repository, branch))
        return fact
    names = " and ".join(missing)
    types = sorted(set(t for name in missing for t in wanted[name]) - present)
    fact.update(case="ruleset missing", passed=False, missing=missing, owner_command=True,
                command=owner.command(repository),
                habit_lines=[MISSING_ZH[0] % names, MISSING_ZH[1]],
                issue_line="Rules not in effect on %s: the rules on %s lack the %s ruleset%s rule types (%s), so %s disabled "
                "or gone. Remedy: habit reruns the owner script, which re-enables %s."
                % (repository, branch, names, "'s" if len(missing) == 1 else "s'", ", ".join(types),
                   "that ruleset is" if len(missing) == 1 else "those rulesets are", "it" if len(missing) == 1 else "them"))
    return fact
