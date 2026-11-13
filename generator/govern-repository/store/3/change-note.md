urgency: when convenient
must-act: yes

版本 3 改变 review bot 的要求方式，换掉 Bugbot，改由 Codex review bot 和 Copilot code
review 承担，并补齐几处流程规则。发布本版本不等于任何仓库已完成升级；仓库采用它时，
habit 要做下面「habit 要做的事」里的几步，所以 must-act 为 yes。版本 1 和 2 保持不变。

仓库采用版本 3 后得到：

- Review 要求按位置而不按厂商：low 不要 review bot，medium 要一个，high 要两个，
  且来自不同提供方。支持的 bot 是 Codex review bot 和 Copilot code review。Bugbot
  不再使用，Upgrade 会删除它的生成规则文件。
- 启用哪些 review bot、按什么顺序，是 habit 在 Initialize 或 Upgrade 时确认的值。
  PR 按合并前默认分支上的这份清单评判，PR 自己改清单不会降低自己的要求；默认分支上
  还没有 record 时（Initialize），以 PR 加入的清单为准。medium 时第一个 bot 不可用，
  由清单里的下一个接替。
- habit 可以对某个 head 豁免某项 review：habit 本人在 PR 上按固定格式写一条评论，
  只对那个 head 有效。
- Merge watch：默认分支上被取消或超时的运行也算失败，会开 miss record；Merge summary
  的 `Required reviews:` 行缺少应有的项时，记为 `merge-summary` 缺失。
- 只在重跑后才通过的 required check，在它的原因有 issue 之前不算修复。
- habit 批准、但不改仓库任何文件的 ticket，可以凭结果评论关闭。
- Reviewer 的启动指令自带它要写的内容，habit 不必再手动补充；Builder 在合并后报告前
  重新读取已合并的 head。
- 更轻的 handoff：只有 Planner 写派发计划，一次 delivery 可以交付整个 spec。

habit 要做的事：

- Initialize 或 Upgrade 时确认 review bot 清单及顺序。
- 需要 Copilot 的每个 head，由 habit 在浏览器里把 Copilot 加为 reviewer，强度选 Lite；
  agent account 发出的请求会被静默丢弃。
- 仓库设置里「Copilot reviews count toward required approvals」保持关闭。
- 准备好后，断开 Cursor GitHub App。
- Upgrade 合并后，照常运行 owner script。

与版本 2 相比，预期结果有这些变化：

- Merge watch 的 missing-review 记录用 bot-1、bot-2 这两个位置名，不再写 bugbot、codex；
  reduced 和 substituted 两种状态不再被读取。
- 默认分支上 cancelled、timed_out、startup_failure 的运行会开 red-default-branch
  记录，版本 2 只对 failure 开。
- 合并到 record 低于版本 3 的 base 上（如 Upgrade 本身的 PR）时，不评判 review bot，
  运行日志里写一行 NOTE。
- 合并到没有 record 的 base 上（如 Initialize 本身的 PR）时，按合并加入的 record 里
  的清单评判，同样写一行 NOTE；以前这种合并总会留下一条错误的 missing-review 记录。
- 生成时必须给出 review bot 清单，没有就拒绝；preconditions 的 checklist 列出
  Codex review bot 和 Copilot code review，不再列 Bugbot。
- 版本 3 发布后，store 的普通选择、安装的版本都变为 3。原来用版本 3 当草稿的
  render 和 install 测试，改为在临时 store 里另造一个版本 4 草稿；scenario 的
  repair-files 在真实 store 下读作 Upgrade（scenario 不运行）。
- 已有 fixture 没有删除、改名或改判。

尚未验证的部分：model scenario 因额度成本没有运行，最终 head 的模型行为未经验证；
Repair 和 OpenCode 发布前没有行为检查。Initialize 的行为检查是本次发布 PR 在公开
sandbox 上的端到端运行；Upgrade 的行为检查是本仓库随后升级到版本 3。Copilot 的
review 字段是观察所得，不是文档承诺，字段变化只会造成错误的 miss record，不会挡住
合并。
