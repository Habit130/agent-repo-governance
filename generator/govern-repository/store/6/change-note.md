urgency: urgent
must-act: yes

版本 6 修复了两处可能报错结论的审计：保护审计在某个已确认的 required check 从 Gate 消失后
仍可能通过；Merge watch 可能按合并后才改过的 PR 描述判断。版本 6 还把 Antigravity app
加为第五个 harness，并为它的指令和配置文件设了 sensitive-path floor。建议各仓库在下一次
delivery 前 Upgrade。发布以本说明合入默认分支为准，版本 7 同时成为下一版草稿。

**habit 需要做的事**

1. 发布合并且 squash commit 的 Linux 和 macOS CI 通过后，按 README 运行 install，
   确认 installed version 为 6。下面几项随 install 生效，与仓库采用哪个版本无关：
   - Generator 引用仓库文件里的文字前先核对已提交的内容，与已提交 blob 不一致的文件只
     报告位置，不引用其文字。Record 无法核对时，依赖它的命令停止；写入遇到核对失败的
     路径，须 habit 对该改动明确批准才继续。若误判拒绝了某个文件，Initialize、Upgrade
     或 Repair 会停下等 habit 决定（#340：#346）；
   - Generator 检查 `GEMINI.md`、Antigravity 的 `.agents/`、旧的 `.agent/`、`_agents/`、
     `_agent/` 和根目录的 `.gemini/config.json`：Initialize 时整理其中的规则，逐项提出
     移除，经 habit 确认后移除；Repair 只列出。Workspace skill 列出；`_agents/skills/`
     里的 skill 移到 `.agents/skills/`，其余保留。个人文件夹内的文件和未通过核对的文件
     保留（#325：#336；#341：#347）；
   - Generator 在任何带 Antigravity 环境变量的 shell 中拒绝运行，继承了 Claude Code 或
     OpenCode 标记的也一样（#324：#336）；
   - Machine install 把 Antigravity app 的全局指令文件链接到唯一的全局文件；machine
     check 新增 Antigravity app 一项，发现该 app 其他的全局指令文件时判为失败（#323：#336）。
2. 为各仓库分别发起 Upgrade。下文「仓库采用 v6 后」的内容只在 Upgrade 合并后生效。
   本工具仓库在本次发布时仍采用 v5，另由 #350 升级。v5 到 v6 的 Upgrade PR 按 v5
   审查。新仓库直接 Initialize 到 v6。
3. Owner script 和它的目标状态与 v5 相同。Upgrade 时，只有 required checks 改变、
   GitHub 状态偏离目标或某项读取失败，generator 才会交出 owner-script 命令；交出时按
   Builder 的交接运行。新仓库在 Initialize 合并、product smoke 通过后运行 owner script。

**仓库采用 v6 后**

- Merge summary 撰写者的保护审计读取默认分支 record 里已确认的 required checks，逐个
  报告 Gate 缺少的 check，并让 habit 重跑 owner script。重跑会替换手动添加的 product
  check 发布者绑定。每个条件只在一处陈述，其他地方指向那里。在两个已登记的 sandbox 中，
  merge 交接只报告 miss record 的数量，不再默认附 `retro` 启动请求。Class retro 并入
  governance model：Planner 的派发计划安排 class retro，每次 retro 有固定的参照点和
  记录基线的 issue；审计类 ticket 要写明其目标状态的来源。（#309：#312、#313、
  #316–#319，以及 #295、#301、#306；均由 #332 交付）
- Merge watch 对每项合并时事实都按合并当时的取值判断，包括 PR 描述里的 Risk 和
  Reverts 声明。合并后改过的内容不改变结论；无法确定合并时取值时报告 `INCOMPLETE`，
  同时照常记录已独立证实的 miss。（#315、#308：#333）
- Antigravity app 成为第五个 harness，可运行 Planner、Builder 和 Reviewer session；
  generator 不在其中运行，Antigravity CLI 不受支持。Antigravity app 的角色 session
  需要已采用 v6 的仓库，并要求 machine check 的 Antigravity app 项通过、仓库里没有
  该 app 自己的指令或配置文件。它不支持 whole-spec delivery、teamwork、swarm 和
  remote agents；等待 PR 未经验证，session 说明在等什么后停止；它的各项限制只靠指令
  约束。Session mark 可以把 harness 注入的 model 通知作为来源。Upgrade 到 v6 时，
  generator 把上面列出的 Antigravity 文件作为冲突提出，经 habit 确认后移除。（#322：
  #323–#327，由 #336 交付；#341：#347）
- Record 新增五个默认 sensitive-path pattern，floor 均为 medium：`**/GEMINI.md`、
  `.agent/**`、`_agents/**`、`_agent/**`、`.gemini/config.json`。在已 Upgrade 的
  仓库里，改动这些路径的 PR 至少为 medium。（#336、#347）
- 合并交接新增复核：PR 在 Upgrade 或 gate 所读策略改变期间一直打开，或无法确定是否
  属于这种情况时，Merge summary 撰写者在默认分支的新 clone 里用当前 gate 判断该 PR，
  把回执写进 Merge summary，交出 pinned merge 命令前再确认一次。Initialize 不做这项
  复核；Upgrade PR 本身按其 base 已采用的策略判断。（#334：#343）
- GitHub 派发和终端交接给 habit 同一个可移植的启动块；需要手动调用 skill 时，habit
  键入所选 harness 的前缀后整块粘贴一次。High 的 Reviewer 交接列出所有推送过 commit
  的 Builder 的 session mark 所排除的 model vendor，包括接手之前的。（#335：#344）
- 每个 head 只做一次完整 Verification：Builder 工作中跑相关测试，推送前在已提交的
  head 上跑完整 Verification。Reviewer 可以引用 pinned head 上已通过的 required CI，
  代替它覆盖的本地命令，并在 Merge summary 或 high-risk report 中写明所引用的 run 和
  覆盖的命令。v6 的 Initialize 在 build 文档骨架里询问每个 required check 运行哪些
  命令。（#338：#345）

**v6 不包含的**

Gate 的代码与 v5 相同：默认分支的 gate 或 record 改变后，gate 不会自己重新判断仍打开
且 head 未变的 PR。Upgrade 到 v6 的仓库，对 Upgrade 期间一直打开的每个 PR，仍须在合并
前取得按当前默认分支策略做出的新 gate 结论；v6 的 Merge summary 撰写者通过上面的合并
交接复核取得它。#296 第 3 项规定的 Upgrade 前过渡复核继续有效。#314、#307 和 #229 的
第 03 行不在 v6 中。

**离线预期和验证范围**

普通 store 选择、render、compare 和隔离安装选中 v6。显式选择已发布的旧版仍然有效；
v7 仅在单次显式允许草稿时可用于 render 或 compare。Release check 对照最终 v6 检查
v7 的所有路径、内容和 Git mode，仅允许 manifest 版本号递增及省略根发布说明。

既有 fixture 路径均保留，本次发布没有改动任何 fixture。各 PR 说明的预期变化：

- Harness 探测 fixture 新增 Antigravity CLI 和 app 两项，原有各项的名称和判定不变；
  对应测试还比较每项判定出的 harness。（#336）
- #336 新增 Antigravity 的 harness 用例和文件用例（相对 v5 均为新增）。其中两个文件
  用例随后改为预期下划线目录的规则和 skill 路径、它们的内容一致性结果，以及单独的
  个人配置文件。（#347）
- Antigravity skill 文字的预期改为要求通用读取和只报位置的结果；各行为 fixture 的
  判定不变；新增 miss #342 的回归 fixture。（#346）
- Merge watch 的既有预期全部保留，新增 fixture 覆盖 #304。（#333）
- 渲染策略的断言改为预期每个 head 一次完整 Verification 的规则。（#345）
- 新增 fixture，未改既有预期：生效 branch rule 和已绑定的 product check（#332），合并
  交接复核（#343）。
- 本次发布：五个把 v5 当作最高已发布版本的测试改为 v6 和草稿 v7。Release runner 的
  v6 离线预期新增两条：Initialize 的 Reviewer 不在 Antigravity app 中启动，Initialize
  不做合并交接复核。v5 及更早版本的预期不变。另有 Antigravity 的 README 断言改为
  已发布措辞。

Model scenarios 因额度成本未运行，最终 head 的模型行为未经验证。公开 sandbox 的
真实 Initialize 检查本次发布，本仓库随后单独 Upgrade 检查采用流程。Repair 和
OpenCode 在发布前没有行为检查。（#138、#139）
