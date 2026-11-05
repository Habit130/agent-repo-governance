# agent-repo-governance

借鉴 Anthropic 的代码审查实践与 mattpocock/skills，构建兼容 OpenCode、Claude Code 和 deepseekharness 的个性化仓库治理体系。

## 运行

Suites、检查和 CI 的命令见 `docs/agents/build.md`；generator 等程序仍在逐个 delivery 开发中。

### 新机器

新机器第一次 install 之前，按顺序做一次：

1. 装好 Command Line Tools（`xcode-select --install`），它带来 `git` 和 `/usr/bin/python3`；再用 Homebrew 装 `gh`。Account wizard 不安装任何东西，只检查它们在不在。
2. 安装各 harness 并手动登录。
3. 在 habit 自己的终端（Terminal 等）里运行下面这条 account wizard 命令，不要在 Claude Code 里用 `!` 前缀运行，因为两次登录要在终端里回答 gh：

   ```text
   /bin/bash -c 'set -eu; d="$(mktemp -d)"; trap "rm -rf \"\$d\"" EXIT; git clone --quiet --depth 1 https://github.com/Habit130/agent-repo-governance.git "$d/src"; /usr/bin/python3 "$d/src/machine/scripts/machine.py" wizard'
   ```

   它把 agent account Habit098 设为 gh 的默认登录（scopes `repo`、`read:org`、`gist`、`workflow`），让 git 的 GitHub credential 经过 gh，把 git 的全局 commit 身份设为 Habit098 的 noreply 地址；再在 `~/.config/gh-maintainer` 里登录 maintainer account Habit130，并在 `~/.zshrc` 里定义 `ghm`。两次登录都会打开浏览器：第一次在浏览器里以 Habit098 登录，第二次以 Habit130 登录；浏览器已登录别的账户时，先在无痕窗口打开 gh 给的网址。Token 只存在 keychain 里，wizard 从不读取或显示它。某一步做不完时，wizard 停在那一步并用中文说明怎么处理；处理后重跑，已完成的步骤会跳过。Wizard 不会登出任何账户。
4. Wizard 最后一行给出下一步：运行下面的 install ready command。
5. Codex harness 询问时，信任 governed repositories。

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
