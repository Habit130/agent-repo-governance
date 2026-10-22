# How Codex loads instructions, skills and permissions

Research for [How Codex loads instructions, skills and permissions](https://github.com/Habit130/agent-repo-governance/issues/23),
child of [Map: governance model and generator v1](https://github.com/Habit130/agent-repo-governance/issues/4).

- Date: 2026-10-22
- Harness: ChatGPT desktop app (`com.openai.codex`) `26.1016.61520`, and the Codex CLI
  `0.163.0-alpha.11.1` bundled inside it
- Machine: habit's Mac, macOS 27.2.0, `HOME=/Users/habit`, `CODEX_HOME` unset (so `~/.codex`)
- Method: read the ticket and map; read OpenAI's Codex documentation at
  `learn.chatgpt.com/docs` (the `developers.openai.com/codex` URLs redirect there); inspected the
  installed app bundle, CLI help, `~/.codex/config.toml` and the app's own
  skill-creator/installer references; ran `codex doctor`, `codex debug prompt-input`,
  `codex execpolicy check`, `codex sandbox` and two one-shot `codex exec` sessions in scratch
  directories. No credential file was read; `gh auth status` printed the account only, not a token.
  No install, upgrade or configuration edit was performed.

The installed CLI is not on `PATH`; every command below uses the absolute path:

```
/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex
```

The public docs describe current Codex generally; the installed build is an alpha. Where the two
disagree, this note says so and reports the installed behavior. All documentation URLs were read on
2026-10-22.

---

## 1. Installation and shared configuration

### 1.1 Installed app and CLI

```
$ /usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' /Applications/ChatGPT.app/Contents/Info.plist
com.openai.codex
$ /usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' /Applications/ChatGPT.app/Contents/Info.plist
ChatGPT
$ /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' /Applications/ChatGPT.app/Contents/Info.plist
26.1016.61520
$ /Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex --version
codex-cli 0.163.0-alpha.11.1
$ command -v codex
(no output)
```

There is no `/Applications/Codex.app`; the Codex desktop experience is the ChatGPT app with bundle id
`com.openai.codex`, and `codex app` launches it. The app bundles the CLI under
`Contents/Resources/codex-cli/`. `codex doctor` reports the same executable and desktop app version:

```
"current executable": "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
"desktop app": {"version": "26.1016.61520"}
```

Because Codex is installed, the ticket's "stop and ask habit" condition was not reached. No install
or upgrade was performed.

### 1.2 The app and CLI share `CODEX_HOME`

Both use the same Codex home, `~/.codex` by default (or `$CODEX_HOME` when set), and the same
`config.toml`. `codex doctor` reports `config.toml: /Users/habit/.codex/config.toml`, and that file
contains both CLI-facing keys (`model`, `model_reasoning_effort`, `[features]`, `[projects.*]`) and
app-facing keys (`[desktop]`, `notify`, plugin marketing state). The app's window/UI state lives in
`~/.codex/.codex-global-state.json`; that is state, not the policy configuration.

So: **one configuration file, two surfaces**. App and CLI versions are separate numbers because the
app ships a build of the CLI and either can be updated on its own.

Sources: local inspection above; [Advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced)
("Codex stores its local state under `CODEX_HOME` (defaults to `~/.codex`)"); `codex app --help`.

---

## 2. Instructions: `AGENTS.md`

### 2.1 Discovery order

The official rule is explicit ([Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)):

1. **Global scope**: read `$CODEX_HOME/AGENTS.override.md` if it exists, otherwise
   `$CODEX_HOME/AGENTS.md`; use the first non-empty file at that level.
2. **Project scope**: start at the project root (by default the directory containing `.git`), walk
   down to the current working directory, and in each directory check `AGENTS.override.md`, then
   `AGENTS.md`, then any names in `project_doc_fallback_filenames`. Include **at most one file per
   directory**.
3. **Merge**: concatenate files from the root down to the working directory, separated by blank
   lines. Closer files appear later, so their guidance wins on conflict. It is append-with-last-wins,
   not replacement.

If no project root is found, only the current directory is checked. `project_root_markers`
(e.g. `[".git", ".hg"]`) changes what counts as a root; `project_root_markers = []` stops parent
search and treats the working directory as the root.

The installed build inserted the global file and the project file into one user message under
`# AGENTS.md instructions for <cwd>`, with the separator `--- project-doc ---` between them. A real
`codex exec` session in the same scratch repository answered `CANARY-ROOT-AGENTS`, so the project
file is not just visible to `debug prompt-input`.

### 2.2 Size, truncation, fallbacks and imports

- `project_doc_max_bytes` defaults to **32 KiB**. Codex skips empty files and stops adding files when
  the combined instruction size reaches the limit; the final file is truncated mid-file and no
  truncation marker is inserted into the prompt. The docs recommend raising the limit or splitting
  guidance across nested directories.
- `project_doc_fallback_filenames` accepts additional filenames such as `["TEAM_GUIDE.md",
  "CLAUDE.md"]`. It is a user-level configuration knob, not a repository declaration.
- **`CLAUDE.md` is not an instruction file by default.** It is not in the default discovery list and
  was not loaded in the live test. It can be made a fallback by listing it in
  `project_doc_fallback_filenames`; then it behaves like `AGENTS.md` for that directory. This repo's
  root `CLAUDE.md` is therefore ignored by Codex unless that config is set, while `AGENTS.md` loads
  normally.
- **Imports do not resolve.** An `AGENTS.md` containing `@imported.md` was injected with the literal
  `@imported.md` line; the target file's canary did not appear. No import syntax is documented for
  Codex's instruction loader. `@` in a Codex prompt is a file mention, not an `AGENTS.md` import.
- **`AGENTS.override.md` replaces, not supplements, the regular file in that directory.** In the live
  nested test, `sub/AGENTS.override.md` was loaded while `sub/AGENTS.md` was absent from the prompt;
  the root `AGENTS.md` still loaded because it was in a different directory.
- **Global override**: `~/.codex/AGENTS.override.md`, when present and non-empty, shadows
  `~/.codex/AGENTS.md` (documented, not separately live-tested).
- **Code review rules**: a `## Code Review Rules` section in the nearest `AGENTS.md` steers Codex
  GitHub code review; this is the same file, not a separate rules file ([GitHub review docs](https://learn.chatgpt.com/docs/third-party/github)).

### 2.3 Live instruction tests

| Fixture | Result |
|---|---|
| Root `AGENTS.md` with `CANARY-ROOT-AGENTS` | loaded (prompt input and real `exec`) |
| `sub/AGENTS.md` + `sub/AGENTS.override.md` + root `AGENTS.md` | root and sub override loaded; `sub/AGENTS.md` skipped |
| `sub/CLAUDE.md` | not loaded by default |
| `@imported.md` line in `AGENTS.md` | line kept literal; `imported.md` not loaded |
| 40 KB `AGENTS.md` with an end canary | end canary missing; project portion truncated at the 32 KiB budget |
| no Git repository, `AGENTS.md` in cwd | cwd file loaded |
| `-c project_doc_fallback_filenames=["CLAUDE.md"]` with only `CLAUDE.md` | loaded as the project doc |
| explicit `[projects."<path>"] trust_level="untrusted"` | project `AGENTS.md` skipped |
| unlisted path (no `[projects]` entry) | project `AGENTS.md` loaded; `.codex/config.toml` ignored |

The last two rows matter: **"untrusted" is not the same as "unlisted"**. An explicitly untrusted
project suppresses project instructions; a project Codex has not been told about still gets its
`AGENTS.md` but not its `.codex/` layer. The docs describe the untrusted case as stricter approvals
and no project `.codex/` config; the live build additionally skipped project `AGENTS.md`.

Repository-committable: `AGENTS.md`, `AGENTS.override.md` (and any fallback filename, only useful if
the user adds it to config). Nothing here grants trust or permissions.

---

## 3. Skills

### 3.1 Discovery roots

The documented local roots ([Build skills](https://learn.chatgpt.com/docs/build-skills)) are:

| Scope | Location |
|---|---|
| `REPO` | `$CWD/.agents/skills`, each parent up to `$REPO_ROOT/.agents/skills` (Codex scans `.agents/skills` in every directory from cwd up to the repository root) |
| `USER` | `$HOME/.agents/skills` |
| `ADMIN` | `/etc/codex/skills` |
| `SYSTEM` | bundled with Codex |

The installed build additionally discovered, and listed in its model-visible skill-root table:

- `<repo>/.codex/skills` at every directory from cwd up to the repository root (not in the public
  roots table above; observed in the prompt input).
- `$CODEX_HOME/skills` (the user skill location used by the installer and skill-creator;
  `~/.codex/skills` on this machine).
- `$CODEX_HOME/skills/.system` (the system/bundled cache).
- Plugin caches under `~/.codex/plugins/cache/...`, including bundled and marketplace plugins.

`.claude/skills` was **not** discovered. This is a clean difference from Claude Code: Codex reads
the shared `.agents` tree, not Claude's directory.

Skill folders may be symlinks; Codex follows the target when scanning (docs). The initial skill list
shows each skill's file path as a short root-relative path, and the prompt includes a root table
(`r0`, `r1`, ...) that expands those paths.

The machine set in `~/.agents/skills` is read directly; it does not need a symlink into `~/.codex`.
This matches the repository's "one machine copy" direction, for Codex at least.

### 3.2 Format, frontmatter and invocation

A skill is a directory with a required `SKILL.md` and optional `scripts/`, `references/`,
`assets/`, and `agents/openai.yaml`. The docs require `name` and `description`; the shipped
skill-creator validator accepts:

```
name, description, license, allowed-tools, metadata
```

`name` must be hyphen-case (lowercase letters, digits, hyphens), cannot start/end with a hyphen or
contain `--`, and is capped at 64 characters. `description` must be a non-empty string. The shipped
validator rejects unknown frontmatter keys; the docs and validator are the authoring contract.

Invocation:

- CLI or IDE extension: `/skills` to pick, or type `$` to mention a skill; explicit form is
  `$skill-name`.
- ChatGPT app: `@` selects a skill.
- Implicit invocation: Codex may choose a skill when the task matches its `description`.

Initial skill list budget: at most **2% of the model context window**, or **8,000 characters** when
the context window is unknown; `skills.max_context_tokens` can raise it, capped at 10,000 tokens.
When the list overflows, Codex shortens descriptions first and may omit skills with a warning. When
a skill is selected, its full `SKILL.md` is read.

### 3.3 Explicit-only skills and name collisions

`agents/openai.yaml` can carry UI metadata, dependencies and invocation policy:

```yaml
policy:
  allow_implicit_invocation: false
```

The default is `true`. When `false`, the skill is not injected into the model's initial skill list
and cannot be chosen implicitly; it remains available through explicit `$skill-name` invocation.
Live test: a skill with this policy was absent from the prompt list (`EXPLICIT-CANARY: 0`), while a
normal sibling was listed. A skill with no `description` was also omitted.

Name collisions: "If two skills share the same `name`, Codex doesn't merge them; both can appear in
skill selectors" (docs). Live test with `collide` in both `.codex/skills` and `.agents/skills`
produced two list entries with the same name and different descriptions, one per root. No
shadowing, override or dedupe by name was observed; no precedence is documented.

`[[skills.config]]` in `~/.codex/config.toml` disables a skill without deleting it:

```toml
[[skills.config]]
path = "/Users/habit/.codex/skills/hatch-pet/SKILL.md"
enabled = false
```

That entry is present on this machine, and `hatch-pet` was absent from the prompt list while other
skills from the same root loaded.

### 3.4 Live skill tests

| Fixture | Result |
|---|---|
| root `AGENTS.md`; `.agents/skills/repo-shared`, `.codex/skills/repo-codex`, `.claude/skills/repo-claude` | first two listed; `.claude` absent |
| root and `sub/` each with `.agents/skills` and `.codex/skills` | all four listed; every directory from cwd to root scanned |
| `CODEX_HOME=/tmp/...` with `skills/home-skill/SKILL.md` | `$CODEX_HOME/skills` listed as a root and skill present |
| skill with `allow_implicit_invocation: false` | omitted from initial list |
| skill with no `description` | omitted |
| same `name` in two roots | both listed, no merge |
| `hatch-pet` disabled via `[[skills.config]]` | omitted |

Repository skill roots load even when the project has no explicit trust entry (observed in the same
scratch repos that had no `[projects]` entry). That is a real distinction from `.codex/config.toml`,
`.codex/rules` and `.codex/hooks.json`, which are trust-gated. The docs' trust statement names
"project-scoped `.codex/` layers, including project-local config, hooks, and rules"; it does not list
skills. I did not repeat the skill test with an explicit `trust_level="untrusted"` entry.

### 3.5 What a repository can commit

- `.agents/skills/<name>/SKILL.md` — native, documented, and loaded without explicit trust.
- `.codex/skills/<name>/SKILL.md` — observed in this build; not in the public roots table; loaded
  without explicit trust.
- Skills are also distributed through plugins; that is a separate packaging and installation path,
  not a repository commit.
- A repository cannot commit the `[[skills.config]]` disable list or the machine's user skill set;
  those live in `~/.codex/config.toml` and `~/.agents/skills` / `~/.codex/skills`.
- Cloud tasks see skills stored in the repository; personal skills from the local computer are not
  synced to cloud tasks ([Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)).

---

## 4. Permissions

### 4.1 Sandbox modes

| Mode | Filesystem | Network | Notes |
|---|---|---|---|
| `read-only` | read; writes denied | restricted | live: write to the workspace failed with `Operation not permitted` |
| `workspace-write` | read access; write inside workspace plus `$TMPDIR` and `/tmp`, unless excluded | off by default; enable with `sandbox_workspace_write.network_access = true` | live: workspace and `/tmp` writable; outside workspace denied; `.git`, `.agents`, `.codex`, `.aws` protected read-only |
| `danger-full-access` | unrestricted | unrestricted | removes the sandbox; use only in a controlled environment |

On macOS the sandbox is Seatbelt (`sandbox-exec`); on Linux/WSL2 it is `bwrap` + seccomp; on
Windows MXC or the legacy Windows sandbox. In `workspace-write`, these paths under a writable root
are recursively read-only: `.git` (and the resolved gitdir for a `.git` pointer file), `.agents`,
`.codex`, `.aws`. Extra writable roots come from `sandbox_workspace_write.writable_roots`;
`exclude_tmpdir_env_var` and `exclude_slash_tmp` remove the temp directories from the writable set.

Live checks in a scratch repository:

```
read-only:        echo > ./sandbox-write.txt        -> Operation not permitted
workspace-write:  echo > ./ww.txt                   -> written
workspace-write:  echo > /tmp/.../tmp-probe         -> written
workspace-write:  echo > $HOME/Library/Caches/...   -> Operation not permitted
workspace-write:  echo > .git/... .agents/... .codex/... .aws/... -> Operation not permitted
workspace-write:  curl --noproxy '*' https://example.com -> DNS failure (network off)
workspace-write + network_access=true:               -> request left the sandbox (HTTP 200, then timeout)
```

### 4.2 Approval policy

Current policies are `on-request`, `never`, or a granular table:

```toml
approval_policy = "on-request"
# or
approval_policy = { granular = {
  sandbox_approval = true,
  rules = true,
  mcp_elicitations = true,
  request_permissions = false,
  skill_approval = false,
} }
```

`approval_policy = "untrusted"` is **retired** and can prevent the client from starting;
`on-failure` is deprecated. `approvals_reviewer = "user"` (default) or `"auto_review"` decides who
reviews eligible approval prompts; automatic review only reviews actions that already need approval
and does not move the sandbox boundary. The default is `on-request`; interactive Codex recommends
the "Auto" preset (workspace-write + on-request) for a version-controlled folder, and may start
read-only until the folder is trusted. Non-interactive `codex exec` defaults to a read-only sandbox
and has no approval prompt; pass `--sandbox workspace-write` explicitly for edits.

Sources: [Sandbox](https://learn.chatgpt.com/docs/sandboxing),
[Agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security),
[Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[Permissions](https://learn.chatgpt.com/docs/permissions).

### 4.3 Command rules (execpolicy)

Rules are Starlark `.rules` files under a `rules/` folder next to an active config layer. The usual
locations are `~/.codex/rules/` and `<repo>/.codex/rules/`; project rules load only when the project
`.codex/` layer is trusted. Admins can enforce rules through `requirements.toml`. A rule looks like:

```python
prefix_rule(
    pattern = ["gh", "secret"],
    decision = "forbidden",
    justification = "Actions secrets must not be written by agents.",
    match = ["gh secret set FOO"],
    not_match = ["gh pr view"],
)
```

Fields: `pattern` (non-empty list of literals or literal unions), `decision` (`allow` / `prompt` /
`forbidden`, default `allow`), `justification`, `match` and `not_match` (inline examples validated at
load). The most restrictive matching decision wins: `forbidden` > `prompt` > `allow`.

Codex treats `bash -lc` / `bash -c` / `zsh -lc` / `sh -c` specially: a simple linear chain of plain
words joined by `&&`, `||`, `;` or `|` is parsed and split into separate commands before rules are
applied. A script using redirection, substitutions, environment assignments, wildcards or control
flow is not split; the whole `["bash","-lc","<script>"]` is evaluated as one command, so an inner
`gh secret` prefix is not seen. This is the documented model; advanced shell is intentionally
evaluated as one command.

The official test command is `codex execpolicy check --rules <file> -- <command...>`. Live results
with a file containing `forbidden` rules for `["ghm"]`, `["gh","secret"]` and `["gh","api"]`:

```
ghm status                                      -> forbidden
gh secret set FOO                               -> forbidden
gh api --method PUT repos/o/r/actions/secrets/FOO -> forbidden
curl -X PUT https://api.github.com/...          -> no match
bash -lc 'gh secret set FOO'                    -> no match (check tool did not split)
```

The last line is a caveat: the rules page says the runtime splits simple shell chains, but the
installed `execpolicy check` did not match the inner command when presented as one argv. I did not
run a model session that attempted the wrapped form, so treat wrapped invocations as a gap to
verify on the installed build.

### 4.4 Hooks

Codex supports lifecycle hooks ([Hooks](https://learn.chatgpt.com/docs/hooks)). Sources are
`hooks.json` or inline `[hooks]` tables next to active config layers:

- `~/.codex/hooks.json` and `~/.codex/config.toml`
- `<repo>/.codex/hooks.json` and `<repo>/.codex/config.toml` (only when the project `.codex/` layer
  is trusted)
- enabled plugins' bundled `hooks/hooks.json`
- managed hooks in `requirements.toml` / MDM / cloud policy

Events: `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `PreToolUse`,
`PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `Stop`,
`Interrupt`. Matching hooks from all layers run; layers do not replace each other. Non-managed hooks
must be reviewed and trusted by exact definition hash (`/hooks`); `--dangerously-bypass-hook-trust`
skips that for one invocation. `PreToolUse` can deny with
`{"permissionDecision":"deny","permissionDecisionReason":"..."}`, legacy `{"decision":"block"}` or
exit code 2 plus stderr; it can also rewrite input. `PermissionRequest` can allow or deny an approval
request. Command hooks default to 600 s; `SessionEnd` and `Interrupt` default to 1 s (max 3 s).
`async: true` hooks run in the background and cannot block or approve. Managed hooks can be forced
with `[features].hooks = true` and `allow_managed_hooks_only = true`.

Hooks are a guardrail, not a complete enforcement boundary: the docs state that a `PreToolUse`
callback error, timeout or malformed response can fail the hook without blocking the tool, and some
specialized tool paths can opt out. Do not treat a hook as a hard security boundary by itself.

### 4.5 Machine-level policy and managed configuration

On this machine there is no system policy: `/etc/codex` does not exist, so
`/etc/codex/requirements.toml`, `/etc/codex/managed_config.toml` and `/etc/codex/skills` are absent.
`codex doctor` reports "managed filesystem source: none". `defaults read com.openai.codex` shows app
preferences only, not requirements keys.

The machine-level controls a Mac could carry, from the docs:

- `~/.codex/config.toml` — user defaults (sandbox, approval, rules location, hooks, skills, model,
  trust list).
- `/etc/codex/requirements.toml` — enforced requirements (Unix, including macOS).
- `/etc/codex/managed_config.toml` — legacy managed defaults (macOS/Linux).
- macOS MDM preference domain `com.openai.codex` with `requirements_toml_base64` and
  `config_toml_base64`.
- Cloud-managed Agent Security requirements when signed in to a supported ChatGPT workspace.
- `/etc/codex/skills` for admin-provided skills.

Requirements can enforce approval/sandbox allowlists, permission profiles, `[rules]` prefix rules,
`[features]` pins, `allow_managed_hooks_only`, MCP/plugin allowlists and more. Precedence for local
execution (low to high) is: system `/etc/codex/requirements.toml`, cloud Agent Security requirements,
legacy managed defaults, macOS MDM. Managed defaults override user `config.toml` and CLI `--config`
for a run; requirements constrain what the user can select.

### 4.6 Project trust, and what a repository can commit

Trust is recorded in the user-level `~/.codex/config.toml`:

```toml
[projects."/path/to/project"]
trust_level = "trusted"   # or "untrusted"
```

- **Unlisted path**: project `AGENTS.md` loads; project `.codex/config.toml`, rules and hooks do not.
  Live: a new scratch repo had `sandbox_mode = "danger-full-access"` in `.codex/config.toml`, and the
  prompt still said `read-only`.
- **`trusted`**: project `.codex/config.toml` loads. Live: with a scratch `CODEX_HOME` whose config
  trusted the repo path, the same file changed the prompt's sandbox mode to `danger-full-access`.
- **`untrusted`**: project `.codex/` layers are skipped, project `AGENTS.md` was also skipped in the
  installed build, and Codex derives the stricter approval behavior described in the docs.
- Trust is **per exact path**, not inherited by prefix. A live probe created a child of
  `/Users/habit/Projects` (which is trusted in this machine's config) and it still resolved as
  read-only. This repository's exact path is not in the trust list.
- A committed project config cannot grant itself trust; only the user-level config (or the app's
  trust prompt, which writes it) can.
- Project `.codex/config.toml` may not override provider/auth/telemetry/notification/profile keys:
  `openai_base_url`, `chatgpt_base_url`, `apps_mcp_product_sku`, `model_provider`,
  `model_providers`, `notify`, `profile`, `profiles`, `experimental_realtime_ws_base_url`, `otel`.
  Codex ignores those in project config and warns.

Repository-committable and trust-gated summary:

| Artifact | Can be committed | Loads without explicit trust? |
|---|---|---|
| `AGENTS.md`, `AGENTS.override.md` | yes | yes (unless the project is explicitly `untrusted`) |
| `.agents/skills/` | yes | yes (observed) |
| `.codex/skills/` | yes | yes (observed; not in the public roots table) |
| `.codex/config.toml` | yes | no; trusted only |
| `.codex/rules/` | yes | no; trusted only |
| `.codex/hooks.json` / inline `[hooks]` | yes | no; trusted only; hooks also need review/trust |
| `[projects."<path>"] trust_level` | no (user-level) | n/a |
| `requirements.toml` enforcement | no (system/MDM/cloud) | n/a |
| `.worktreeinclude` | yes | n/a; app worktree copy behavior |

Sources: [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[Advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced),
[Managed configuration](https://learn.chatgpt.com/docs/enterprise/managed-configuration),
live tests.

### 4.7 Can a machine-level setting block `ghm` and Actions secrets?

The honest answer is **partially, and only at the boundaries Codex evaluates**:

- **`ghm`**: `ghm` is an interactive zsh function, not an executable. Live checks: `zsh -lc 'whence -w
  ghm'` → `ghm: none`; `zsh -ic 'whence -w ghm'` → `ghm: function`; `command -v ghm` → nothing.
  Codex's shell tool ran `/bin/zsh -lc`, so `ghm` is not normally available in a Codex shell at all.
  A `prefix_rule(pattern=["ghm"], decision="forbidden")` does match a literal `ghm` invocation
  (`codex execpolicy check` returned `forbidden`), and a `PreToolUse` hook can deny it. But a command
  that explicitly starts an interactive shell (`zsh -ic 'ghm ...'`) moves the function call inside a
  script string; whether the runtime splits that form needs verification, and the check tool did not
  split a `bash -lc` wrapper in the test below.
- **Actions secrets through `gh`**: `prefix_rule(["gh","secret"])` blocks `gh secret set/delete/list`
  directly, and `prefix_rule(["gh","api"])` blocks all `gh api` calls, including the REST writes to
  `/repos/.../actions/secrets/...`. Both returned `forbidden` in `execpolicy check`.
- **Actions secrets through REST**: a `curl`/`python`/other HTTP client is not matched by a `gh`
  prefix rule; live `curl -X PUT https://api.github.com/...` produced no match. A `PreToolUse` hook
  can inspect the full command string and deny known patterns, but hooks are documented as fail-open
  on callback error, and a script can obfuscate the URL. The strongest machine control is network:
  in the default `read-only` or `workspace-write` sandbox, command network access is off, so `gh`
  and REST cannot reach GitHub at all. Once `network_access = true` or
  `danger-full-access` is chosen, only rules/hooks remain, and neither is a complete boundary.
- **Managed policy**: `requirements.toml` can install `[rules]` prefix rules and pin sandbox/approval
  choices; this is stronger than a user rule because the user cannot override it. It is still
  prefix-based for the command forms above, so the REST/wrapper caveats remain.

This is a "reduce and catch mistakes" control, not an "agent cannot ever write a secret" guarantee.
The same conclusion the map reached for Claude Code/OpenCode denies applies with extra nuance here:
the machine can block the obvious direct commands, not every path to the API.

---

## 5. Sessions

### 5.1 CLI

`codex exec` is the non-interactive entry point (docs: [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)):

```bash
codex exec "summarize the repository structure"
codex exec --sandbox workspace-write "make the test pass"
codex exec --json "..." | jq
codex exec --ephemeral "..."           # do not persist rollout files
codex exec -o last.txt "..."           # write the final message
codex exec --output-schema schema.json "..."
codex exec --skip-git-repo-check "..." # outside a Git repository
codex exec resume --last "continue"
```

- The prompt is the first argument; if omitted (or `-`), it is read from stdin. Piped stdin is
  appended as a `<stdin>` block when a prompt is also given.
- Default sandbox is `read-only`. `--sandbox workspace-write` or `danger-full-access` changes it.
  `--full-auto` was removed; use `--sandbox workspace-write` or `--approve-for-me`.
- `--json` emits JSONL events (`thread.started`, `turn.started`, `item.*`, `turn.completed`); the
  final agent message is on stdout normally.
- `--ignore-user-config` skips `$CODEX_HOME/config.toml`; `--ignore-rules` skips user and project
  `.rules`; `--ephemeral` skips session rollout persistence.
- Live one-shot: `codex exec --ephemeral -s workspace-write --json "Run 'sleep 3; echo DONE'..."` ran
  `/bin/zsh -lc 'sleep 3; echo DONE'`, captured `DONE`, and finished with exit 0.

### 5.2 Desktop app

- New chat, type the first message in the composer, and send. The app is launched with
  `codex app [PATH]`; the installed app is `/Applications/ChatGPT.app`.
- The composer has a **Worktree** selector (see 5.5) and a model picker. The app writes
  app-specific settings into `[desktop]` in the shared `~/.codex/config.toml`.
- In the app, skills are selected with `@`; in the CLI/IDE, `/skills` or `$`.

### 5.3 Model selection

- `~/.codex/config.toml` on this machine sets `model = "gpt-6.1-sol"`, `service_tier = "default"`,
  `model_reasoning_effort = "medium"`, `personality = "pragmatic"`.
- CLI: `-m/--model` overrides for a run; `--profile <name>` layers
  `$CODEX_HOME/<name>.config.toml`.
- App: model picker in the composer; it uses the same config default unless changed.
- The model catalog is server-driven; `codex doctor` reported `model: gpt-6.1-sol`, and the live
  session accepted it.

### 5.4 Background commands and waiting

Yes, through **unified exec**, which is enabled in this build (`codex features list` includes
`unified_exec`, `unified_exec_tty`, `write_stdin_approval`; `codex doctor` lists them as enabled):

- A command can return a resumable session; `write_stdin` polls it.
- Empty `write_stdin` polls are capped by `background_terminal_max_timeout`, default **300000 ms
  (5 minutes)**.
- Managed requirements can disable resumable processes and `write_stdin`, leaving one-shot
  `exec_command` available.
- This is resumable process polling inside the session, not a separate detached job scheduler. A
  short command (3 s) completed synchronously in the live test; a longer one can be polled, up to
  the timeout.

Sources: [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
(`features.unified_exec`, `background_terminal_max_timeout`), [Hooks](https://learn.chatgpt.com/docs/hooks)
("Unified exec (`exec_command`) ... a later `write_stdin` poll").

### 5.5 App worktrees

The desktop app creates a Git worktree per chat by default ([Worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)):

- Location: `$CODEX_HOME/worktrees`, configurable in Settings > Worktrees.
- Starting point: `HEAD` of the selected branch; uncommitted changes are applied to the worktree;
  the worktree is in **detached HEAD**, so it does not pollute branches.
- Retention: most recent **15** Codex-managed worktrees by default; managed worktrees are disposable
  and tied to a chat. Permanent worktrees are separate and can host multiple chats.
- Handoff moves a chat between Local and Worktree, with Codex handling the Git operations.
- `.worktreeinclude` at the repo root lists ignored files (e.g. `.env`) to copy into a managed
  worktree; Codex also copies an ignored `AGENTS.override.md`.
- Git still forbids the same branch checked out in two worktrees at once.
- CLI `codex exec --worktree` also exists for a managed CLI worktree.

This is separate from the manual `git worktree` the research session itself used.

---

## 6. Identity

### 6.1 Local sessions

Codex runs shell commands inside the user's session, under the sandbox. It does not swap
credentials. On this machine, a full-access `codex sandbox` probe reported:

```
gh: /opt/homebrew/bin/gh
github.com
  ✓ Logged in to github.com account Habit098 (keyring)
git user.name = Habit098
```

So local Codex sessions act as **Habit098**, the agent account, through the machine's `gh` and
`git`. The live `codex exec` shell used `/bin/zsh -lc`, so it inherits the login environment (with
the `ghm` caveat above). No credential file was read; `gh auth status` printed the account and token
prefix, not the token.

### 6.2 Cloud features

Cloud tasks are started by signing in with the ChatGPT account, choosing GitHub repositories and
connecting GitHub if prompted ([Codex Cloud](https://learn.chatgpt.com/docs/cloud),
[Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)). The docs say
repository access and personal connections "depend on the account running the task", and cloud
tasks can commit or open a pull request when they have permission. The docs do not name a separate
bot identity.

The ticket records that Codex is connected through habit's ChatGPT account, linked to **Habit130**.
So the working model is:

- **Local Codex: Habit098**, the machine's `gh`/`git` identity.
- **Cloud Codex: habit's ChatGPT-linked GitHub connection (Habit130)**, not Habit098.

I did not read `~/.codex/auth.json` or the cloud connection state, so the exact GitHub author on a
cloud commit/PR is not directly observed here. The docs are silent on a distinct cloud bot identity;
verify the author on a test cloud PR before relying on it. Do not conflate the two identities when
reasoning about approvals: local GitHub actions are Habit098; cloud actions are under the ChatGPT
account's GitHub connection.

---

## 7. What this means for the governance model

These are consequences of the facts above, not new recommendations:

- `AGENTS.md` is the one instruction file Codex reads natively. The repo's existing pattern
  (`AGENTS.md` as canonical, `CLAUDE.md` importing it for Claude Code) works for Codex because Codex
  reads `AGENTS.md` directly; Codex does **not** expand `@AGENTS.md` and does not read `CLAUDE.md` by
  default. If a repo wanted `CLAUDE.md` to be the Codex source, it would need
  `project_doc_fallback_filenames`, a user-level setting.
- The machine skill set `~/.agents/skills` is a native Codex root, as is the repo's
  `.agents/skills`; `.claude/skills` is not. Codex is therefore a first-class consumer of the
  "one machine copy" direction, while Claude Code still needs its own path or a symlink.
- Codex has the richest permission surface of the four harnesses: sandbox modes, approvals, prefix
  rules, lifecycle hooks, managed requirements and MDM. But the parts a repository can commit are
  trust-gated: `.codex/config.toml`, `.codex/rules` and `.codex/hooks.json` do not load until habit
  trusts that exact project path. `AGENTS.md` and `.agents/skills` (and the observed
  `.codex/skills`) do load without explicit trust, so repo content can still steer behavior before
  trust is granted.
- A committed project config cannot grant itself trust, and a repository cannot commit a machine
  `requirements.toml`. Machine policy belongs in `~/.codex/config.toml`, `/etc/codex/*` or MDM; a
  governed repository should not assume a committed permission file is effective.
- Direct `ghm`, `gh secret` and `gh api` calls can be forbidden by machine rules; `curl`/REST and
  interactive-shell wrappers are not covered by those prefixes. Network-off in the default sandbox
  is the stronger control. Hooks can deny more, but the docs call them a guardrail, not a complete
  boundary.
- `codex exec` is a usable non-interactive session for automation; it defaults to read-only and
  needs explicit `--sandbox workspace-write` to edit. Background work is resumable
  (`unified_exec`/`write_stdin`), not a detached daemon. App chats use `$CODEX_HOME/worktrees`.
- App and CLI share configuration but not version numbers; an update to either can change behavior.
  Record the installed pair, not just "Codex", when verifying governance.

---

## Appendix: fixtures and commands

All scratch fixtures were under `/tmp/codex-research/` and removed or left as one-shot test dirs;
no user-level config was edited. The two `codex exec` sessions were `--ephemeral`.

Key commands:

```bash
CODEX=/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex
"$CODEX" doctor --json
"$CODEX" debug prompt-input "x"            # model-visible prompt, no model call
"$CODEX" sandbox -c 'sandbox_mode="workspace-write"' -- /bin/sh -c '...'
"$CODEX" execpolicy check --rules /tmp/.../default.rules --pretty -- gh secret set FOO
"$CODEX" exec --ephemeral -s workspace-write --json "..."
```

Fixtures:

| Directory | Purpose |
|---|---|
| `scratch1` | root `AGENTS.md` canary; real `exec` canary check |
| `scratch2` | nested `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`, `@imported.md` |
| `scratch3` | `.agents/skills`, `.codex/skills`, `.claude/skills` |
| `scratch4` | 40 KB `AGENTS.md` truncation |
| `scratch5` | no Git repository |
| `scratch6` | same skill name in two roots |
| `scratch9` | explicit-only skill and missing description |
| `scratch10` | `CLAUDE.md` fallback via `-c` |
| `scratch11` | project `.codex/config.toml` trusted vs untrusted |
| `scratch12` | sandbox write/network/protected-path checks |
| `scratch13` | `$CODEX_HOME/skills` root |
| `scratch16` | root and nested `.agents`/`.codex` skill roots |
| `scratch17` | explicit `trust_level="untrusted"` and project instructions |
| `home11`, `home17` | scratch `CODEX_HOME` trust stores |
| `rules14` | `prefix_rule` fixtures for `ghm`/`gh secret`/`gh api` |

## Open or uncertain

- **Project `AGENTS.md` and trust**: unlisted and `trusted` projects load it; an explicit
  `trust_level="untrusted"` entry skipped it in the installed build. A parallel source-level read of
  current `main` reported the same untrusted-project behavior; the public docs describe trust mainly
  as gating `.codex/` layers. Re-check after the next app update, because this is exactly the
  boundary a governance model would rely on.
- **`.codex/skills`**: observed as a repository skill root in the installed alpha, but absent from
  the public "where Codex loads local skills" table. Treat it as build behavior, not a stable
  contract, until documented.
- **Rules vs shell wrappers**: `execpolicy check` did not match `["gh","secret"]` inside
  `bash -lc 'gh secret set FOO'`, while the rules page says the runtime splits simple chains. I did
  not run a model session that attempted the wrapped form. Verify on the installed build before
  claiming a rule blocks wrapped commands.
- **Skill name collision resolution**: both entries appear; no precedence or merge is documented. I
  did not invoke `$collide` to see which body loads (or whether both are offered).
- **Cloud GitHub author**: not observed. The ticket records the ChatGPT account is linked to
  Habit130; the docs do not name a separate identity. Verify on a cloud PR.
- **Skill frontmatter strictness**: the docs require `name` and `description`; the shipped validator
  also rejects unknown keys. A source-level reading of current `main` reports that the parser can
  fall back to the directory name when `name` is absent, but the authoring contract and the shipped
  validator require it. Use the validator before relying on that tolerance.
- **`~/.codex/skills`**: read by the installed build, and the bundled skill-creator tells authors to
  create skills there; the public "where Codex loads local skills" table lists `.agents/skills`, the
  admin location and the system location but not this path. Treat it as a user root that is not in
  the documented discovery table.
