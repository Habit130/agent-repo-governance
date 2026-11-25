urgency: urgent
must-act: yes

版本 5 修复了两条会让审查失效的路径。旧 gate 重跑时可能采用已被修改的 PR 正文，旧
Merge watch 也可能把合并后补上的证据算进合并时的审查。建议受影响的仓库在下一次
delivery 前 Upgrade。发布以本说明合入默认分支为准，版本 6 同时成为下一版草稿。

**habit 需要做的事**

1. 发布合并且 squash commit 的 Linux 和 macOS CI 通过后，按 README 运行 install，
   确认 installed version 为 5。Install 更新本机 generator 和 machine skills，包括
   Codex Desktop Local 的 `wait-on-pr`。已有仓库继续执行各自 record 对应的规则。
2. 为各仓库分别发起 Upgrade。本工具仓库在本次发布时仍采用 v4，另由 #277 升级。
   v4 到 v5 的 Upgrade PR 按 v4 审查，Merge summary 标题用七位 head。采用 v5 后的
   PR 用完整的 40 位 head。新仓库直接 Initialize 到 v5。
3. Upgrade 合并后按 Builder 的交接运行新版 owner script。检查已写入的项目及默认
   分支上实际生效的保护。GitHub 已接受写入但读回未确认时，报告会计入该次写入并
   指出待核查项目。新仓库在 Initialize 合并、product smoke 通过后运行 owner script。

**仓库采用 v5 后**

- Gate 在每次运行时从 GitHub 读取当前 PR 的 head、正文和作者。Risk 理由须含有
  非空白字符。Pure revert 走 low 需要核对被撤销的 commit、其父提交的治理 record、
  重新计算的树，以及合入默认分支的 PR 与 squash commit。来源无法确认时，按常规
  sensitive-path floor 判断。Upgrade 前启动的旧 gate run 仍使用旧代码。（#209、#242、#283）
- Merge watch 按 squash commit 的父提交读取当时的治理版本、agent account 和 bot
  顺序。审计支持的历史版本以该脚本渲染时的版本为上限。v5 遇到 v6 record 会报告
  审计未完成，v6 草稿则按继承的 v5 规则审计自身。Initialize 没有原 record 时读取
  本次引入的 record。它按合并时间核对
  review、状态、summary 和豁免，区分同一 head 上证据的作者、provider 及完成时间。
  Copilot 须有该 head 的已提交 review，以及源自其 Actions workflow 的成功 check。
  v5 的 medium PR 若涉及固定内容或指令文件且只有 Copilot 完成 bot review，还须有
  Reviewer。High 的 summary 第三行声明是否适用 security review；认证、隐私或凭据
  处理按实际改动判断。合并前仍由 session 核对所需审查和豁免。（#244、#255、#274、#293）
- Merge watch 检查默认分支 push 的整个提交区间。遇到部分证据不可读，会先记录已经
  证实的 miss，再报告未完成的审计。重复事件按同一 miss 的真实记录去重。合并前还会
  检查默认分支实际生效的 Gate、Merge、各自的规则及 gate check 来源。（#266、#268）
- High 的每个 finding 都需要 Builder 在 GitHub 答复，包括 Nit。Reviewer 在答案齐全后
  才交付 high-risk report 和 pinned merge 命令。原 Builder 等待时会检查仍打开的 PR
  是否有待答复的 finding；合并后核对仓库、PR、合并者、目标分支、审查过的 head 和
  squash commit，再验证该提交的 product smoke。等待中的 Builder 无需 habit 另行通知。
  等待不受支持、中断或 GitHub 证据不足时，habit 可在原 Builder 对话说“继续”。
  后续每项不可逆操作仍由 habit 单独批准。（#273、#284、#289）
- Codex Desktop Local 的 Builder 和 Reviewer 等待 PR 时优先使用已安装的
  `wait-on-pr`。缺少该 skill 时可按 harness 时限轮询，或说明等待事项并停止。
  Planner 排程时检查验收测试用到的接口，先安排改变接口的 ticket 合并，再从更新后的
  默认分支启动依赖该接口的验收。（#265、#278、#290）
- 首次 Initialize 的 evidence 说明 gate 从下一张 PR 起生效。其回退说明记录既有的
  GitHub 设置和恢复步骤。Medium 有 Reviewer 参与时由 Reviewer 写 Merge summary；
  high 的 Reviewer 获有效豁免时由 Builder 给出报告和合并交接。（#209、#293）

**离线预期和验证范围**

普通 store 选择、render、compare 和隔离安装选中 v5。显式选择已发布的旧版仍然有效；
v6 仅在单次显式允许草稿时可用于 render 或 compare。Release check 对照最终 v5
检查 v6 的所有路径、字节和 Git mode，仅允许 manifest 版本号递增及省略根发布说明。
发布已存在的草稿却缺少下一版草稿时，release fixture 预期失败。（#221）

既有 fixture 路径均保留。共用 parser fixture 从 v5 起把只有 ASCII 或 Unicode
空白的 Risk 理由判为格式错误，v1–v4 仍按原预期判断。有实际文字的理由继续有效。
Gate、Merge watch 和 owner script 的新用例覆盖上述来源、历史证据与已接受写入。
Release runner 的 v5 离线预期按原 Builder 的等待状态交接；v3、v4 仍在原 Builder
终端回复 merged。（#225、#242、#268、#288）

Model scenarios 因额度成本未运行，最终 head 的模型行为未经验证。公开 sandbox 的
真实 Initialize 检查本次发布，本仓库随后单独 Upgrade 检查采用流程。Repair 和
OpenCode 在发布前没有行为检查。（#138、#139）
