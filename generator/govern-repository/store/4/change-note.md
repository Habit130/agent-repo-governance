urgency: urgent
must-act: yes

版本 4 修复了一个可能让变更跳过敏感路径最低审查等级的 gate 判断。受影响的仓库按
#25 在下一次 delivery 前 Upgrade。合并本说明即发布版本 4，版本 5 同时作为下一版草稿
建立。版本 5 的内容与版本 4 相同，差别只有 manifest 的版本号和草稿没有发布说明。

仓库采用版本 4 后有这些变化。

- Gate 只把治理生效后合并的提交判为 pure revert，依据是该提交的父提交已有治理
  record。公开仓库缺少适用的 Actions event policy 时，owner script 会说明
  2026 年 12 月 2 日起 `pull_request_target` 会被拦截，gate 因此无法报告
  required check。（#173）
- Builder 和 Reviewer 记录 harness、model、vendor 与信息来源。High 的 Reviewer
  核对自己的 vendor 与每个推送过提交的 Builder session 的 vendor 都不同。需要
  habit 亲自调用的 skill，交接会明确给出调用步骤。向已有 PR 推送后，Builder 等当前
  head 正在运行的 gate workflow 结束，再集中更新 PR 正文，交接前确认这次编辑触发的
  gate 结果。（#174、#176、#179）
- 每个等级都有 self-verification。Medium 和 high 各有一个 review bot 位置，按
  habit 确认的顺序请求，当前 bot 不可用才换下一个。Medium 的 bot 都不可用或清单为空
  时，可以由同 vendor 的 Reviewer session 补位。固定内容或指令文件仅获一项 bot 审核，
  且适用 Review bots 的额外审查规则时，仍需不可豁免的 Reviewer session。两种 medium
  情形均允许同 vendor，角色说明和最低审查表已统一。High 的 Reviewer 必须来自不同
  vendor，bot 用尽时由 habit 决定等候或豁免该位置。Builder 在 low 或 medium 要驳回 bot
  的 Important finding，先升到 high。（#194、#197）
- 豁免由 habit 用 owner 账号在该 PR 评论，首行按 `review.md` 中的 Waivers 格式写明
  豁免项、完整 head SHA 和理由。换 head 要重新批准。涉及认证、隐私或凭据的 high 变更
  仍需 Reviewer 的 security review，habit
  可额外请求 Codex security review。#192 首个 head 在观察窗口内没有自动完成的 bot
  review，发布流程继续沿用 habit 手动请求。（#192、#194）
- Merge watch 从 medium 起按一个 bot 位置核对 v4 的合并。Initialize 前没有 record 时，
  读取合并加入的 record。合并到 v4 以前的 record 上时，记录过渡说明，检查该 head 的
  Merge summary，从 medium 起还检查 Reviewer 状态。v3 base 上仍识别 habit 为该
  head 写的 Reviewer 豁免。合并前仍按 base 版本验证 bot。（#194）
  已声明的 Reviewer 豁免需要独立核对 owner 评论中的豁免项和完整 head SHA。
  即使 Reviewer 状态成功，缺少有效授权时也会留下 missing-review 记录。（#197）
  只有成功读取并解析 bot 清单后，Merge watch 才认可 medium Reviewer 补位。
  清单缺失或读取、解析失败时，按缺少 bot-1 处理。有效的 owner 逐提交豁免可覆盖该位置。（#197）
- 仓库采用 v4 后，exact comparison 无差异且 record 的 confirmed 值与默认分支
  一致的 pure Upgrade 走 medium，仍受敏感路径 floor 约束。Initialize 以及改变
  confirmed 值、required checks 或 owner script 目标状态的 Upgrade 走 high。
  Session 在读角色指令前刷新默认分支，只有干净且检出在默认分支时才快进。Builder
  难度单独记录，habit 据此选 model 和 effort，review 强度仍由风险等级决定。同一轮
  草稿变更默认按整份 spec 交付。（#194、#195）

本工具仓库另外拆分了构建文档和按版本组织的 policy-text suite，记录上述治理决策，
并用同一个 PR 切发布和下一版草稿。Release check 验证草稿副本的路径、Git mode 和
应当相同的所有字节。（#192、#193、#195、#196）

Install 带来 generator、已发布的 v4、未发布的 v5 文件，以及 #166 刷新的托管 skill
副本。普通选择取 v4。habit 在发布合并后运行 install，各治理仓库再分别 Upgrade。
Upgrade 沿用已有的 bot 清单和顺序。首次 Initialize 或原 record 缺少 bot 清单的
Upgrade，由 habit 确认清单和顺序。按需提出 bot 请求并为 high 启动合格的 Reviewer。
Upgrade 合并后按交接运行新版 owner script。此次 owner script 模板有变更，因此
must-act 为 yes。

预期结果随发布调整。Store、render、compare 和隔离安装默认取 v4，仍可显式选择旧版；
v5 的 render 和 compare 需要单次显式 opt-in，拒绝时目标保持原样。Machine list 的
最新发布版本变为 v4。Live runner 的 v4 Initialize 指引改为一个 bot 位置和不同 vendor
的 Reviewer，离线保留 v3 的两个 bot 位置。新增的 fixture 分别覆盖缺少授权的 Reviewer
豁免及无法解析的 bot 清单。空清单 fixture 的输入改用 generator 实际渲染的格式，原有
fixture 的路径和预期结果均保留。渲染断言现在核对 medium Reviewer 的两种情形。

Model scenarios 因额度成本未运行，最终 head 的模型行为未经验证。公开 sandbox 的
端到端 Initialize 是本次发布的 Initialize 行为检查，本仓库随后单独 Upgrade 是
Upgrade 的行为检查。Repair 和 OpenCode 发布前没有行为检查。（#138、#139）
