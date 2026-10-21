# How deepseekharness loads instructions, skills and permissions

Research for [How deepseekharness loads instructions, skills and permissions](https://github.com/Habit130/agent-repo-governance/issues/10),
child of [Map: governance model and generator v1](https://github.com/Habit130/agent-repo-governance/issues/4).

- Date: 2026-10-21
- Harness: DeepSeek Harness app `com.deepseek.dsh` 0.2.1-rc.2 (nightly channel), CLI `0.2.1-rc.2`
- Profiles examined: `headless` (CLI) and `desktop` (the Electron profile this session runs in)
- Method: read the ticket and comments; ran the CLI by absolute path; dumped the composed config,
  default config and config schema; read the package READMEs and bundle patches shipped inside
  `app.asar`; ran live one-shot sessions in a scratch directory with test instructions and skills;
  ran several `--patch` overlays; read this session's own session log header. No configuration file
  under `$DSH_HOME`, the app bundle or other user config was edited; the harness itself wrote its
  normal session logs.

Every fact below carries the command and output, or the configuration quote, it rests on. Where a
fact holds for only one profile, the profile is named.

---

## 1. Source, installation and launch (checklist items 1 and 2)

### 1.1 Installed app and CLI

```
$ /usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "/Applications/DeepSeek Harness.app/Contents/Info.plist"
com.deepseek.dsh
$ /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "/Applications/DeepSeek Harness.app/Contents/Info.plist"
0.2.1-rc.2
$ "/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh" --version
0.2.1-rc.2
```

The CLI is not on `PATH`; every command in this document uses the absolute path. Ticket comment by
habit on 2026-10-21 records the same install, version and update channel, so **no install is
needed and no install authorisation is exercised here** (checklist item 2 is satisfied by that
comment, not by an action in this session).

### 1.2 What the launcher does

`/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh` is a shell shim that
runs Electron as Node:

```sh
ELECTRON_RUN_AS_NODE=1 exec "$resources/../MacOS/DeepSeek Harness" --expose-internals \
  "$resources/app.asar/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js" "$@"
```

### 1.3 Source of truth

The app ships the harness as a pnpm tree inside `app.asar/dsh/node_modules/@deepseek-ai/`. Each
package carries its own `README.md`, and the README is the package-level reference (config tables,
defaults, model-experience and known limitations). The packages' `repository` field names the
upstream repository, for example
`@deepseek-ai/dsh-web-app/package.json` → `"url": "git+https://github.com/deepseek-ai/deepseek-harness.git"`,
`"directory": "packages/bundle/web-app"`. No public docs site was needed; every claim below is
quoted or observed from the installed 0.2.1-rc.2 artefacts.

### 1.4 How a session is composed

```
$ dsh --help
Usage: dsh [--profile] <name> [options] [app-args...]
       dsh plugin --profile <name> <pnpm-args...>

dsh: boot a DeepSeek Harness profile — an ordered stack of plugin-bundle patch
layers under your own overrides.
...
  --profile <name>               the profile under $DSH_HOME/profiles to boot
  --patch <path>                 extra patch-list overlay applied after the
                                 profile layer (repeatable)
  --dump-config                  print the composed profile tree and exit
  --dump-config-schema           print JSON Schema for profile entries and
                                 patches without mounting
  --dump-default-config          print the profile tree without its user layer
                                 or --patch overlays and exit
```

- `$DSH_HOME` is `/Users/habit/.dsh` here; `$DSH_PROFILE` is `desktop`.
- A profile is `<DSH_HOME>/profiles/<name>/package.json` (`dsh.profile.bundles`), then the bundles'
  patch layers, then `<profile>/cordis.patch.yml`, then any `--patch` overlay.
- `headless` bundles: `@deepseek-ai/dsh-base`, `@deepseek-ai/dsh-headless`
  (`~/.dsh/profiles/headless/package.json`).
- `desktop` bundles: `@deepseek-ai/dsh-base`, `@deepseek-ai/dsh-web-app`
  (`~/.dsh/profiles/desktop/package.json`).

The CLI can boot and dump `headless`, but **not `desktop`**:

```
$ dsh --profile desktop --help
error: profile "desktop" is managed exclusively by the Electron application
[exit=1]
$ dsh --profile desktop --dump-config
error: profile "desktop" is managed exclusively by the Electron application
[exit=1]
$ dsh --profile desktop --dump-default-config
error: profile "desktop" is managed exclusively by the Electron application
[exit=1]
$ dsh --profile desktop --dump-config-schema
error: profile "desktop" is managed exclusively by the Electron application
[exit=1]
```

So desktop facts below come from its profile files, the web-app bundle patches and presets shipped
in `app.asar`, and this session's own session log — not from a CLI dump.

`--dump-config-schema` also requires a profile even though `--help` does not say so:

```
$ dsh --dump-config-schema
error: --profile <name> is required
[exit=1]
$ dsh --profile headless --dump-config-schema | wc -c
  602211
```

For `headless`, `--dump-config` and `--dump-default-config` are byte-identical (12,314 bytes):

```
$ dsh --profile headless --dump-config > headless.txt
$ dsh --profile headless --dump-default-config > headless-default.txt
$ diff headless.txt headless-default.txt && echo identical
identical
```

That matches `~/.dsh/profiles/headless/cordis.patch.yml` being `[]`: the headless profile has no
user layer of its own.

---

## 2. Instructions: `AGENTS.md` and `CLAUDE.md` (checklist item 3a)

### 2.1 Config keys (both profiles)

`headless` composed config:

```yaml
- id: agent-instructions
  name: '@deepseek-ai/dsh-agent-instructions'
  config:
    maxBytes: 65536
```

`--dump-config-schema` for that entry (`$defs/config35`) gives the defaults:

```
projectRootMarkers             => [".git"]
instructionFileCandidates      => ["AGENTS.md", "CLAUDE.md"]
localInstructionFileCandidates => ["AGENTS.local.md", "CLAUDE.local.md"]
maxSourceBytes                 => 1048576
maxBytes                       => required
```

`desktop` gets the same row from the `standard` agent preset, not from the host plane. The
`dsh-web-app` patch disables the base row (`- id: agent-instructions / disabled: true`) and
`presets/standard.patch.yml` inserts it into the preset with the same `maxBytes: 65536`. This
session's log records `"agentPreset":"standard"` in its `session` header.

### 2.2 Where files come from

`@deepseek-ai/dsh-agent-instructions` README, "What the agent gets":

> The first request includes one durable baseline message with the user-global chain —
> `$DSH_HOME/AGENTS.md`, then `<agentsHome>/AGENTS.md` — followed by the project chain: every
> existing candidate file from the project root down to the session working directory, in
> broad-to-specific order. Within one candidate group, files whose content matches after trimming
> render once: a `CLAUDE.md` that duplicates its `AGENTS.md` is not repeated [...]

- User level: `$DSH_HOME/AGENTS.md` (`~/.dsh/AGENTS.md`), then `$DSH_AGENTS_HOME/AGENTS.md`
  (default `~/.agents/AGENTS.md`). On this machine the second file does not exist
  (`ls ~/.agents/AGENTS.md` → `No such file or directory`), so only the first was observed.
- Project level: candidate names `AGENTS.md`, `CLAUDE.md`, plus `AGENTS.local.md` and
  `CLAUDE.local.md` overlays, from the project root (nearest `.git` ancestor) down to the cwd.
- The README's stated limit: "lowercase names, `.claude/rules/`, and `@path` imports are not
  interpreted".

The baseline is a durable user-role message, so it is visible in the session log. This session
(desktop) has exactly three headings:

```
$ zstd -dc ~/.dsh/sessions/--Users-habit-Projects-tools-agent-repo-governance--/session-042bf24b-.../session.v4.jsonl.zstd | ...
Instructions from: ~/.dsh/AGENTS.md
Instructions from: AGENTS.md
Instructions from: CLAUDE.md
```

Ordering is user-global first, then project, broad to specific. The template's stated rule is
"More specific instructions take precedence over broader ones. They do not override system,
developer, or direct user instructions."

### 2.3 Live test: both files (variant A)

Scratch directory `/tmp/dsh-research.UBWuJq/project` (outside the repository) containing
`AGENTS.md` (canary `CANARY-AGENTS-7731`, build command `build-agents`) and `CLAUDE.md`
(canary `CANARY-CLAUDE-4429`, build command `build-claude`). Run:

```
$ cd /tmp/dsh-research.UBWuJq/project
$ dsh --profile headless --patch /tmp/dsh-research.UBWuJq/test.patch.yml --json - < prompt.txt
```

Reply (final event, verbatim except trimming):

```
**1. INSTRUCTIONS**

Canary words in the injected workspace-instruction context:
- `CANARY-AGENTS-7731` — from `AGENTS.md`
- `CANARY-CLAUDE-4429` — from `CLAUDE.md`
- `~/.dsh/AGENTS.md` contains no canary word.

Heading lines, in order:
1. `Instructions from: ~/.dsh/AGENTS.md`
2. `Instructions from: AGENTS.md`
3. `Instructions from: CLAUDE.md`

**2. CONFLICT**

Build command: `build-agents`.

Why: both project files are equally specific, so precedence falls to the global `~/.dsh/AGENTS.md`,
which says the project's own `AGENTS.md` defines project facts (build commands explicitly named
there), and `CLAUDE.md` is a file for a different tool (Claude Code) being injected as context.
[...]
```

**Facts:** both `AGENTS.md` and `CLAUDE.md` load from the same directory; both canaries are
injected. dsh applies no same-directory tie-break: the model received both contradictory answers
and chose `build-agents` by its own reasoning (from the user-global rule that project facts belong
in `AGENTS.md`), not because the harness suppressed or ranked `CLAUDE.md`.

### 2.4 Live test: one file at a time (variants B and C)

Only `AGENTS.md` present (`CLAUDE.md` moved out of the tree), same prompt:

```
**1. INSTRUCTIONS**

- Canary words ...: `CANARY-AGENTS-7731` — from `AGENTS.md` (project root). The global
  `~/.dsh/AGENTS.md` contains no canary word.
- Headings, in order:
  1. `Instructions from: ~/.dsh/AGENTS.md`
  2. `Instructions from: AGENTS.md`

**2. CONFLICT**
... only one injected file states a build command.
Conclusion: **`build-agents`**. ...
```

Only `CLAUDE.md` present:

```
**1. Canaries in injected workspace-instruction context**

- `CANARY-CLAUDE-4429` — from `CLAUDE.md` (only canary present)
...
Heading lines, in order:
1. `Instructions from: ~/.dsh/AGENTS.md`
2. `Instructions from: CLAUDE.md`

**2. Build command**

`build-claude`.
```

So `CLAUDE.md` is a first-class instruction candidate in dsh, not merely a pointer to `AGENTS.md`.
`@path` imports are not interpreted (README, Known Limitations), so a `CLAUDE.md` that begins with
`@AGENTS.md` is injected as its own file and the line is not expanded.

### 2.5 Effect for governance

A repository can steer dsh by committing `AGENTS.md`; a `CLAUDE.md` in the same directory is a
peer instruction file and **adds** text rather than overriding `AGENTS.md`. If a repository wants
one canonical file, committing only `AGENTS.md` is the reliable option (variant B); a duplicate
`CLAUDE.md` with identical content is deduplicated, but a divergent one is injected and competes.

---

## 3. Skills: discovery, frontmatter and invocation (checklist item 3b)

### 3.1 Config keys

`headless` composed config:

```yaml
- id: skill
  name: '@deepseek-ai/dsh-skill'
- id: skill-filesystem
  name: '@deepseek-ai/dsh-skill-filesystem'
- id: tool-skill
  name: '@deepseek-ai/dsh-tool-skill'
```

Schema defaults for `skill-filesystem` (`$defs/config37`):

```
providerName        => "filesystem"
includeDefaultRoots => true
customSkillDirs     => []
watch               => true
bundledSkillDir     => <none>
```

`tool-skill` accepts only `catalogDescriptionMaxLength` (default `500`). The `desktop` preset mounts
`skill-filesystem` and `tool-skill` with defaults (`presets/standard.patch.yml`).

### 3.2 Roots

`@deepseek-ai/dsh-skill-filesystem` README, "Roots and priority":

| Rank | Source | Path |
|---|---|---|
| 100 | `project-dsh` | `<projectRoot>/.dsh/skills` |
| 200 | `project-agents` | `<projectRoot>/.agents/skills` |
| 300 | `custom` | `Config.customSkillDirs` |
| 400 | `user-dsh` | `<dshHome>/skills` |
| 500 | `user-agents` | `<agentsHome>/skills` |

The project root is the nearest ancestor containing `.git`; without one, the current cwd is used.
`.claude/skills/` is **not** in this table and was not discovered in the live test. Only direct
children are scanned: `<name>/SKILL.md` and `<name>.md`.

### 3.3 Format and invocation

README: a skill is a directory bundle `<name>/SKILL.md` or a flat `<name>.md`; frontmatter requires
`name` (kebab-case) and `description`, and accepts `whenToUse`, `metadata`,
`disable-model-invocation` and `user-invocable`. `disable-model-invocation: true` hides the skill
from the model catalog and the `skill` tool; `user-invocable: false` hides it from `/name`.

`@deepseek-ai/dsh-tool-skill`: before the first request the model receives a user-role catalog with
each skill's name and a capped description, and loads a skill with the `skill` tool. A user invokes
`/name` directly. The catalog deliberately hides paths: in the model-visible rendering "paths,
provider ranks, and disabled skills remain hidden". Loading a skill reveals its base directory in
the `<skill_resources>` block.

### 3.4 Live test

Created one skill in each named project location, plus controls: `.dsh/skills/dsh-canary`,
`.agents/skills/agents-canary`, `.agents/skills/flat-canary.md` (flat form), a custom directory
`/tmp/dsh-research.UBWuJq/custom-skills/custom-canary` wired with
`- id: skill-filesystem / config: customSkillDirs: [...]`, and `.claude/skills/claude-canary` as a
negative control.

Same headless run as variant A reported:

```
**3. SKILLS**

Names ending in `-canary`:
- `agents-canary`
- `custom-canary`
- `dsh-canary`
- `flat-canary`

Paths: the catalog exposes **no source path field** for any of them — only prose [...]
Only the `dsh-canary` **load** exposed one:
/private/tmp/dsh-research.UBWuJq/project/.dsh/skills/dsh-canary

**4. INVOKE**

`dsh-canary` body, verbatim:

# dsh-canary

SKILL-BODY-CANARY: BODY-DSH-9182

This skill lives at `.dsh/skills/dsh-canary/SKILL.md`.
```

**Facts:**
- `.dsh/skills`, `.agents/skills` (bundle and flat file), and a `customSkillDirs` root all load.
- `.claude/skills` is not discovered, confirming the roots table.
- The model catalog lists names and descriptions only; a load exposes the source path.
- Invocation works by name through the `skill` tool; the loaded body is returned verbatim.
- Ordering presented by the catalog is alphabetical (`agents-canary, custom-canary, dsh-canary,
  flat-canary`), not rank order.

**Desktop:** this session's log contains the same catalogue mechanism: 29 model-invocable skills
(`banner-design`, `brand`, `code-review`, ... `writing-for-agents`) injected at seq 11.
`~/.agents/skills` holds 46 entries, 45 of them directories with a `SKILL.md`; 23 of those declare
`disable-model-invocation: true` and are absent from the catalogue, leaving 22 matches. The other
7 catalogue entries are the `office*` skills, which the app supplies from outside
`~/.agents/skills` (no project `.dsh/skills` or `.agents/skills` exists in the repository).

---

## 4. Permissions, settings and hooks (checklist item 3c)

### 4.1 There is no user-facing allow/ask/deny rule list

The permission surface is three plugin entries plus presets, from the `headless` composed config
(the same rows exist in `base` and are used by the desktop preset path):

```yaml
- id: sandbox-policy
  name: '@deepseek-ai/dsh-sandbox-policy'
  config:
    mode: !!js process.env.DSH_PERMISSION_MODE ?? 'workspace-write'
    workspaceRoot: !!js process.cwd()
- id: approval
  name: '@deepseek-ai/dsh-user-approval'
  config:
    policy: !!js >-
      (process.env.DSH_PERMISSION_MODE ?? 'workspace-write') ===
      'danger-full-access' ? 'never' : 'ask'
- id: permission
  name: '@deepseek-ai/dsh-permission-presets'
  config:
    presets:
      read-only:
        sandbox: read-only
        approval: ask
      workspace-write:
        sandbox: workspace-write
        approval: ask
      danger-full-access:
        sandbox: danger-full-access
        approval: never
```

`dsh-permission-presets` schema (`$defs/config28`) accepts exactly:
`presets: { <name>: { sandbox, approval, name?, description? } }` and `defaultPreset`.
`dsh-sandbox-policy` accepts `mode` (`read-only | workspace-write | danger-full-access`) and
`workspaceRoot`; `dsh-user-approval` accepts `policy` (`ask | never`). The exhaustive schema has
**no** rule, pattern, path, tool or deny list:

```
$ grep -o -iE '"(rules|deny|hook)[^"]*"' headless-schema.json | sort -u
(no output)
$ grep -o -iE '"[a-zA-Z]*allow[a-zA-Z]*"' headless-schema.json | sort -u
"allowEmptySignature" "allowLoopbackHttp" "allowParallelInProgress" "allowedAgentPresets"
```

Those four `allow*` keys are signature, loopback-HTTP, parallel-todo and agent-preset settings,
not a tool policy.

Programmatic enforcement does exist inside plugins: `dsh-tools` exposes
`ctx.tools.guard(guard)` and a `tools/pre-execute` waterfall that decides allow/deny/ask. That is
Cordis plugin code, not repository or user configuration, so a repository cannot use it.

**Desktop profile:** `~/.dsh/profiles/desktop/cordis.patch.yml` overrides the preset table with
`defaultPreset: danger-full-access`. This session's session log records the applied values:

```
{"type":"permission/preset","data":{"preset":"danger-full-access"}}
{"type":"sandbox/mode","data":{"mode":"danger-full-access"}}
{"type":"approval/policy","data":{"policy":"never"}}
```

which matches the runtime context ("Current DSH file policy: danger-full-access", "Approval
prompts are disabled in this session"). Under `read-only` or `workspace-write` the approval policy
is `ask`; in a `headless` session there is no answerer, so `ask` fails closed (the README: without
a terminal answerer requests resolve `unavailable`).

### 4.2 Live test: a deny rule written "following the schema" has no effect

`deny.patch.yml`:

```yaml
- id: permission
  config:
    rules:
      - action: deny
        tool: write
        path: project/denied.txt
```

`--dump-config` accepts and preserves the key (no boot-time schema rejection):

```yaml
- id: permission
  name: '@deepseek-ai/dsh-permission-presets'
  config:
    rules:
      - action: deny
        tool: write
        path: project/denied.txt
```

But the plugin ignores `rules` (its Config has only `presets` and `defaultPreset`). Live run asking
the model to create `denied.txt`:

```
tool_call  {"file_path": "/private/tmp/.../project/denied.txt", "content": "DENIED-TEST\n"}
tool_result "<content>\nCreated file\n</content>"
$ cat denied.txt
DENIED-TEST
```

**Fact:** the deny rule does not take effect. Unknown config keys are inert, not errors.

### 4.3 Live test: the schema's real deny knob does take effect

`readonly.patch.yml`:

```yaml
- id: sandbox-policy
  config:
    mode: read-only
```

Same write request:

```
tool_result "Error: [sandbox: file access denied under read-only mode]\n[sandbox: escalation
available — retry this exact operation once with sandbox_permissions (the narrowest wider mode
that suffices) + justification; the approval prompt asks the user]"
$ ls denied2.txt
No such file or directory
```

**Fact:** denial is enforced by the sandbox mode, not by a rule list. The model may retry once with
an explicit wider `sandbox_permissions` plus a justification, which routes to the approval policy;
under `never` (danger-full-access) it cannot escalate, and in headless without an answerer an `ask`
policy fails closed.

### 4.4 Settings

There is no repository-level settings file. The `settings` plugin is a form editor over live plugin
configuration:

```yaml
- id: settings
  name: '@deepseek-ai/dsh-settings'
  disabled: !!js '!ctx.get(''profileContext'')'
```

It is disabled in `headless` (no profile context) and present in `desktop`. Its README: "Forms
expose only volatile fields from active, uniquely addressed profile entries... Changes persist
through the active profile's Cordis patch." It also imports a legacy `settings.yaml` from the
harness home once. The durable user settings for a profile are therefore
`$DSH_HOME/profiles/<profile>/cordis.patch.yml` (here `defaultPreset`, UI rows, model route), not a
committed `.dsh/settings.json`.

### 4.5 Hooks

There is no hook surface.

- The config schema has no `hooks` key: `grep -c -i hook headless-schema.json` → `0`.
- None of the 307 installed `@deepseek-ai` packages matches `/hook/i`, so no hook package is shipped.
  The base bundle has no hook entry.
- Inserting a hook plugin into a `--patch` fails to activate:

```
$ dsh --profile headless --patch hook.patch.yml "Reply with exactly: HOOK-PROBE"
dsh: warning: 1 entry did not activate
hook-test (@deepseek-ai/dsh-hooks): failed to import: Error [ERR_MODULE_NOT_FOUND]:
Cannot find package '@deepseek-ai/dsh-hooks' imported from /Users/habit/.dsh/profiles/headless/
```

- A hook-shaped config key on a real plugin is accepted and inert. `hook-inert.patch.yml` added
  `- id: tools / config: hooks: PreToolUse: ... 'echo HOOK-RAN >> hook.log'`; the run created
  `hookprobe.txt`, its final answer said "No hook intercepted, blocked, or modified the write",
  and `hook.log` did not exist.

The only "hooks" in the product are Cordis plugin lifecycle/event APIs (`dsh-agent` README:
"Plugins, UI, hooks, and orchestrators can also observe or intercept agent activity"). They are
programmatic, not a user or repository configuration file.

### 4.6 `--patch` overlay format

A `--patch` file is a top-level YAML array of loader patch entries. Per the schema's
`includePatch` description: "An insert appends entries, optionally inside the group identified by
id. Other patches replace supplied fields; config is replaced wholesale, not deep-merged. A truthy
name asserts the existing plugin name rather than renaming it. Unknown targets and non-insert
patches without a nonempty id are warned and skipped." Overlays apply after the profile layer and
before the app starts; they were used above for credentials (`credentials`, `authorization`,
`deepseek-account` re-enable, documented in the headless README), `customSkillDirs`,
`sandbox-policy.mode`, and the inert deny/hook experiments.

---

## 5. Subagents and non-interactive runs (checklist item 3d)

### 5.1 Subagents exist and work (both profiles)

`headless` composed config:

```yaml
- id: subagent
  name: '@deepseek-ai/dsh-subagent'
- id: subagent-spawn-in-process
  name: '@deepseek-ai/dsh-subagent-spawn-in-process'
  config:
    providerName: spawn
- id: subagent-fork-in-process
  name: '@deepseek-ai/dsh-subagent-fork-in-process'
  config:
    providerName: fork
- id: tool-subagent
  name: '@deepseek-ai/dsh-tool-subagent'
  config:
    provider: spawn
    toolName: subagent
- id: tool-subagent-fork
  name: '@deepseek-ai/dsh-tool-subagent'
  config:
    provider: fork
    toolName: subagent_fork
- id: workflow-ptc
  name: '@deepseek-ai/dsh-workflow-ptc'
  config:
    provider: spawn
- id: tool-workflow
  name: '@deepseek-ai/dsh-tool-workflow'
```

Schema: `subagent.maxDepth` default `1`, `maxActiveSubagents` default `8`; `workflow-ptc` allows
`maxConcurrentAgents` (default `0`), `maxTotalAgents` (default `1000`). The desktop `standard`
preset mounts the same delegation tools with `modelSelectionSettings: true` for `subagent`.

Live test in `headless`: the model called `subagent` with a child prompt, got
`"started subagent 516e1aed-..."`, polled `list_agents` (`[running]`), and the final answer quoted
the child's reply `CHILD-PONG`. Delegation is asynchronous by default (the child runs as a job),
with `subagent_fork` and `workflow` as siblings.

### 5.2 Non-interactive runs exist

`dsh --profile headless "<task>"` is the one-shot mode: it answers one task, prints the final
answer to stdout, writes diagnostics to stderr, and exits; exit code 0 means the task completed,
1 means it aborted or errored. `--json` turns stdout into newline-delimited run events
(`session`, `status`, `text`, `thinking`, `tool_call`, `tool_result`, `final`) and
`--session-id` resumes a persisted session. `--json` was exercised in every live test above (one
task per invocation); `--session-id` was not exercised. There is no interactive follow-up in headless; the web/tui
profiles are the interactive surfaces.

---

## 6. GitHub authentication (checklist item 3e, extended by issue #18)

Run inside this dsh session (desktop profile):

```
$ gh api user --jq .login
Habit098
[exit=0]
$ git config --get-urlmatch credential.helper https://github.com
!/opt/homebrew/bin/gh auth git-credential
[exit=0]
$ gh auth status
github.com
  ✓ Logged in to github.com account Habit098 (keyring)
  - Active account: true
  - Git operations protocol: https
  - Token: <redacted>
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'
```

Repeated inside a one-shot `headless` session (scratch cwd) through the bash tool:

```
tool_call   {"command": "gh api user --jq .login"}
tool_result "Habit098\n"
tool_call   {"command": "git config --get-urlmatch credential.helper https://github.com"}
tool_result "!/opt/homebrew/bin/gh auth git-credential\n"
```

**Facts:**
- The session acts as `Habit098` (the machine's agent account), through `gh`'s keyring credential,
  which is also git's HTTPS helper. This matches issue #18's decision.
- dsh carries no GitHub token of its own. There is no GitHub credential key in the config schema or
  in the composed `headless` config; the only `github*` schema key is
  `githubConnectionTimeoutMs` on the plugin-manager (pnpm registry probe), not auth. The managed
  credential store (`~/.dsh/.credentials.yaml`) holds only `DEEPSEEK_API_KEY` and
  `OPENCODE_GO_API_KEY` references plus DeepSeek account/session records — no GitHub entry.
- `GH_TOKEN`, `GITHUB_TOKEN` and `GH_ENTERPRISE_TOKEN` are unset in this process; the machine's
  `gh` keyring supplies the identity. No token value was read or printed.
- Headless differs in credentials, not auth: its profile disables the managed store
  (`credentials`, `authorization`, `deepseek-account`), so API-key routes use the launch
  environment, `<cwd>/.env`, then `$DSH_HOME/.env` (headless README). The live tests re-enabled
  the store through a `--patch` overlay to use the GUI-saved DeepSeek key; without it the run
  failed with `MISSING_CREDENTIAL: llm-deepseek: no API key for provider route
  "deepseek-official"`. That is model-provider auth, not GitHub auth. The `gh`/`git` identity is
  still inherited from the machine in a headless session because the bash tool runs as the same
  user; the headless probe above shows the same `Habit098` login and helper.

---

## 7. What this means for the governance model

- Repository-scoped dsh configuration is limited to **instruction files** (`AGENTS.md`,
  optional `CLAUDE.md`, local overlays) and **project skill roots** (`.dsh/skills`,
  `.agents/skills`). A repository cannot commit permissions, approval policy, hooks or settings
  that dsh will enforce.
- Permissions and hooks are user/profile policy: `cordis.patch.yml` plus `--patch`. A governed
  repository's safety therefore rests on the harness profile on the machine, and on `AGENTS.md`
  for behavioural rules — not on a checked-in deny list.
- `AGENTS.md` and `CLAUDE.md` both load and can conflict; for dsh, `AGENTS.md` should be the single
  canonical project file. A `CLAUDE.md` that starts with `@AGENTS.md` (as this repository's does) is
  injected as a second, separate instruction file; the import line is not expanded.
- Skills are portable across Claude Code and dsh only where they sit in a root each harness scans
  (`.claude/skills` for Claude Code, `.dsh/skills` or `.agents/skills` for dsh). A dual-harness
  repository needs a copy/duplicate or a shared root, because neither scans the other's directory.
- Non-interactive headless runs and subagents exist, so dsh can serve as a Builder/Execution
  harness; with `DSH_PERMISSION_MODE` unset its headless stance is `workspace-write` + `ask`, and
  `ask` has no answerer there, so approval-requiring calls fail closed.

---

## Appendix: scratch fixtures and commands

All live tests ran from `/tmp/dsh-research.UBWuJq/project` (no `.git`, so the cwd is the project
scope). The headless profile does not use the GUI-saved model credential by design; the documented
overlay restores it (headless README, "Credentials"). Without it:

```
$ dsh --profile headless "Reply with exactly: PING"
dsh: MISSING_CREDENTIAL: llm-deepseek: no API key for provider route "deepseek-official";
store DEEPSEEK_API_KEY through the credentials service (the web Models page writes it), or export
DEEPSEEK_API_KEY in the launching environment
```

`test.patch.yml`:

```yaml
- id: credentials
  disabled: false
- id: authorization
  disabled: false
- id: deepseek-account
  disabled: false
- id: skill-filesystem
  config:
    customSkillDirs:
      - /tmp/dsh-research.UBWuJq/custom-skills
```

Instruction fixtures. `AGENTS.md`:

```markdown
# AGENTS.md (scratch test)

The AGENTS canary word is **CANARY-AGENTS-7731**.

The build command for this project is `build-agents`.

This file is the project's AGENTS.md. It is intentionally different from CLAUDE.md.
```

`CLAUDE.md`:

```markdown
# CLAUDE.md (scratch test)

The CLAUDE canary word is **CANARY-CLAUDE-4429**.

The build command for this project is `build-claude`.

This file is the project's CLAUDE.md. It is intentionally different from AGENTS.md.
```

Skills were placed at `.dsh/skills/dsh-canary/SKILL.md`,
`.agents/skills/agents-canary/SKILL.md`, `.agents/skills/flat-canary.md` (flat form),
`/tmp/dsh-research.UBWuJq/custom-skills/custom-canary/SKILL.md`, and the negative control
`.claude/skills/claude-canary/SKILL.md`. Each had kebab-case `name`, a distinct `description`, and
a body containing its own `SKILL-BODY-CANARY` word.

Prompt (stdin, `-`):

```
CAPABILITY PROBE. Answer from what this session itself supplies. Do not read AGENTS.md, CLAUDE.md
or any SKILL.md from disk to answer questions 1, 2 or 3; question 4 means use your skill mechanism.

1. INSTRUCTIONS: List every canary word that appears in the workspace-instruction context injected
   into this session, and say which instruction file each came from. Also quote the
   "Instructions from:" heading lines in the order they appear.
2. CONFLICT: The injected project instructions disagree about the project's build command. State
   the build command you conclude this project uses, and explain briefly which instruction you
   followed and why.
3. SKILLS: List every skill available to you in this session that has a name ending in "-canary",
   giving its exact name. If your skill catalog or a skill load exposes a source path for it, give
   that path too. If no path is exposed, say so.
4. INVOKE: Load the skill named dsh-canary with your skill tool and quote its body verbatim.
```

The other overlays, exact files:

```yaml
# deny.patch.yml
- id: permission
  config:
    rules:
      - action: deny
        tool: write
        path: project/denied.txt
```

```yaml
# readonly.patch.yml
- id: sandbox-policy
  config:
    mode: read-only
```

```yaml
# hook-inert.patch.yml
- id: tools
  config:
    hooks:
      PreToolUse:
        - matcher: write
          command: 'echo HOOK-RAN >> hook.log'
```

```yaml
# hook.patch.yml
- insert:
    - id: hook-test
      name: '@deepseek-ai/dsh-hooks'
      config:
        PreToolUse:
          - matcher: write
            command: 'echo HOOK-RAN >> hook.log'
```

The desktop evidence came from:

```
$ zstd -dc ~/.dsh/sessions/--Users-habit-Projects-tools-agent-repo-governance--/session-042bf24b-.../session.v4.jsonl.zstd
{"type":"session",...,"cwd":"/Users/habit/Projects/tools/agent-repo-governance","agentPreset":"standard"}
{"type":"permission/preset",...,"data":{"preset":"danger-full-access"}}
{"type":"sandbox/mode",...,"data":{"mode":"danger-full-access"}}
{"type":"approval/policy",...,"data":{"policy":"never"}}
```

---

## Open or uncertain

- **Desktop composition is not dumpable through the CLI.** The facts above come from
  `~/.dsh/profiles/desktop/{package.json,cordis.patch.yml}`, the web-app bundle patches and
  presets inside `app.asar`, and this session's log. The exact merged tree the Electron app holds
  (including any app-injected rows beyond the files) was not printed; only the effects (preset
  `standard`, sandbox/approval values, instruction headings, 29-skill catalogue) were observed.
- **Same-directory precedence between `AGENTS.md` and `CLAUDE.md` is not specified.** Both load,
  in candidate order; the observed choice of `build-agents` was the model's reasoning from the
  user-global file, not a documented harness rule. A different model or task could choose
  differently, so a conflicting `CLAUDE.md` is a real ambiguity for governance.
- **No hook or deny-rule mechanism was found**, but this is a negative result from 0.2.1-rc.2:
  the schema, the package inventory, the composed config and a live import probe. A future version
  could add one; re-check the schema on upgrade.
- **`--patch` config replacement is wholesale, not a deep merge.** The deny experiment replaced the
  `permission` row's config (dropping `presets`/`defaultPreset` to schema defaults) and the hook
  experiment replaced `tools` config. This is documented but easy to trip over; overlays should
  repeat every field they need.
- **The approval policy under `headless` with `ask` is fail-closed but untested end to end** for a
  request that reaches the approval seam (the write tests were denied by the sandbox before
  approval). No answerer exists in headless; whether a tool blocks or returns `unavailable` depends
  on the consumer.
- **Nested instruction discovery and refresh were not live-tested.** The README documents
  discovery of a deeper `AGENTS.md` after a first-party `read`/`write`/`edit` and on resume; the
  tests used a flat scratch directory with no `.git`.
- **User-level skill roots were not written to.** `$DSH_HOME/skills` and `~/.agents/skills` are
  documented roots; the desktop catalog proves `~/.agents/skills` loads, but this session did not
  modify user config. `$DSH_HOME/skills` does not exist on this machine.
- **`.claude/skills` is not scanned by dsh** (confirmed by the negative control). Whether the
  generator should deploy skills to `.dsh/skills` or `.agents/skills`, or duplicate into
  `.claude/skills`, is a distribution decision that belongs to
  [How the generator turns a repository's state into its governance](https://github.com/Habit130/agent-repo-governance/issues/17).
- **`githubConnectionTimeoutMs`** is the only GitHub-related schema key found; it configures the
  plugin-manager's registry probe, not authentication. No evidence of any dsh-owned GitHub token
  setting.
