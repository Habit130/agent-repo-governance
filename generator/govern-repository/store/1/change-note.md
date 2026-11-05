urgency: when convenient
must-act: yes

Governance model version 1 是第一个版本。现在还没有 governed repository，所以没有哪个 repository 需要 Upgrade。一个 repository 第一次 Initialize 时，version 1 才落到它里面。

第一次 Initialize 落地这些东西：

- AGENTS.md 里的固定规则：怎么开始一个 session，流程概览，硬性限制，怎么和 habit 及其他 agent 说话，governance 文件和 credential 的规则，以及 Code Review Rules。AGENTS.md 后面的 "This repository" 一节归这个 repository 自己，写着从它原有规则里保留下来的部分。
- 三个角色 Planner、Builder、Reviewer 各自的流程，以及 review、issue、label 的用法、PR 模板和 Bugbot 的规则文件。
- 这个 repository 自己的命令、CI 和 Actions secrets 说明，由 generator 检查过后写下。
- Governance record：sensitive paths 和 required checks，都由 habit 在确认时定下。
- Governance gate：每个 PR 都要通过的 required check。它检查 PR 的作者、Risk 行，以及改到 sensitive path 时 tier 够不够。
- Merge watch：每次 merge 之后检查该做的 review 是否都做了，漏了就开一个 miss issue。它不拦任何 merge。
- Owner script：habit 运行它，把 GitHub 设成目标状态：Gate、Merge、History 三个 ruleset，只允许 squash merge，以及 Actions、secret scanning 和 push protection 的设置。从这时起，只有 habit 能 merge。
- Labels：triage 的状态和分类 label、wayfinder label 和 miss label。

habit 要做的：

1. 这个版本 merge 之后，运行一次 install，让本机拿到 version 1。
2. 每个 repository 的第一次 Initialize：
   - 在这个 repository 的目录里启动 generator。
   - 按 generator 给的 checklist 邀请 agent account 成为 collaborator（checklist 附有现成命令，agent 随后自己接受邀请），并把 Bugbot 和 Codex review bot 连接到这个 repository。
   - 回答 generator 的那一次确认。
   - 之后按 Builder 的指引走完 high 的 review，然后 merge。
   - Initialize 的 PR merge 之后，运行 generator 交给 habit 的 owner script 命令。
3. Private repository 只有 ruleset 能生效时才能 Initialize。确认时，habit 要表示知道两件事：GitHub 在 private repository 里不检测、也不阻止 credential；Actions 的分钟数有限。
