# agent-repo-governance

借鉴 Anthropic 的代码审查实践与 mattpocock/skills，构建兼容 OpenCode、Claude Code 和 deepseekharness 的个性化仓库治理体系。

## 运行

Suites、检查和 CI 的命令见 `docs/agents/build.md`；generator 等程序仍在逐个 delivery 开发中。

### Install

本仓库改动 machine skill set 的 PR merge 后，habit 在 Claude Code 里用 `!` 前缀运行这条 ready command。它每次都相同：重新 clone `origin` 默认分支的最新 commit 到临时目录，从那里 install 到本机，不用本地 checkout。

```text
/bin/bash -c 'set -eu; d="$(mktemp -d)"; trap "rm -rf \"\$d\"" EXIT; git clone --quiet --filter=blob:none https://github.com/Habit130/agent-repo-governance.git "$d/src"; /usr/bin/python3 "$d/src/machine/scripts/machine.py" install --source "$d/src" --home "$HOME"'
```

Install 之后，machine check 和 governed-repository list 可单独运行。两者都不改动 skills、规则、链接或 installed state；只有它们调用的 Codex 和交互式登录 shell 可能按各自习惯写自己的文件：

```text
/usr/bin/python3 ~/.agents/governance/machine/scripts/machine.py check
/usr/bin/python3 ~/.agents/governance/machine/scripts/machine.py list
```

Install 只写 machine skills，从不写 personal skill，也不经 personal skill 里的链接写入。Machine check 里，machine skill 缺少 Codex user-only key、在 Codex skill list 里被省略或描述被截短时算失败；personal skill 出现同样的问题只报告（`说明`），不算失败。

GitHub:https://github.com/habit130/agent-repo-governance

## 本次初始化范围

建立本仓库自身的治理契约；治理工具实现、skills 安装及其他仓库的修改属于后续独立交付。

## Agent instructions

Agents and contributors start from `AGENTS.md`; verified commands are in `docs/agents/build.md`.
