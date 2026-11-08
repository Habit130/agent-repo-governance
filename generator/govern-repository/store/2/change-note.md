urgency: when convenient
must-act: yes

版本 2 保留默认工作流权限，并修正产品 smoke、标签说明和仓库规则的沿用方式。
habit 可按需安排升级；采用本版本时，仍需完成通常的安装、生成、评审、合并及
owner 操作。发布本版本不等于任何仓库已完成升级。版本 1 保持不变。

owner script 关闭 Actions 创建或批准 PR 的能力时，先读取当前状态，再同时提交
原有 default_workflow_permissions 与关闭审批的值；保留 read 或 write 默认权限，
已经关闭时不写入，状态无效或无法读取时不猜测。写入后再次读取，只有确认默认权限
未变且审批关闭才报告成功；读回失败或不一致时计入已接受的写入并报告未通过，不自动
重写或猜测成功。此项是兼容性修复，不声称复现过
可选字段 API 的故障。升级合并后 habit 重跑新版 owner script，并核对结果；
回退升级后也需要重跑对应版本的 owner script。

合并后 smoke 要验证实际合并提交的产品构建或测试。同一工作流在默认分支 push
上运行的产品测试也符合条件，应检查该提交的实际结果。没有默认分支产品验证时，
high-risk ticket 预先确定可执行的本地 smoke；失败或无法运行意味着交付未完成。
治理审计、合并前 PR CI 或可能发布产物的 Release dispatch 都不是替代证据。

标签描述是创建默认值及用途说明，保留同名同用途的已有描述，用途冲突交给 habit。
仓库特有规则按需引用权威 runbook，保留强制禁止规则、命令清单和验证证据。Upgrade
保留仓库自有内容与未被 habit 修改的 confirmed 值，不自动清理下游文档。

新增版本的测试预期包括两字段权限更新、写入后的权限核验、产品 smoke、标签用途及权威规则引用；
历史 fixture 保持不变。实际 v2 的 Initialize、Upgrade、Repair 和精确比较继续使用
原有 record 格式，不需要额外身份确认或签发配置。

governance-gate 继续使用 GitHub Actions 共用 App 15368，算法与信任边界保持不变。
本版本不修复共用签发身份或同 SHA 旧成功结果的局限，不引入独立 App、签名密钥、
受保护签名环境或新依赖。公开和私有 sandbox 仍验证 owner 权限保留、恢复及无写入
重跑；离线测试不能代替这些 live 结果。
