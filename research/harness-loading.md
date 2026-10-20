# How Claude Code and OpenCode load instructions, skills and permissions

## Question

How do Claude Code and OpenCode load instructions, skills, settings and permissions, according to their official documentation?

## Scope and versions

- Every source in this document is a primary source: vendor documentation or vendor release notes. No secondary source was used.
- Claude Code documentation was read on 2026-10-20. The top entry of the official changelog at access is version `2.1.304`, labelled `October 19, 2026` ([Claude Code changelog](https://code.claude.com/docs/en/changelog)).
- OpenCode documentation was read on 2026-10-20 from the pages under `https://opencode.ai/docs/`. The rendered pages state `Last updated: Oct 19, 2026` ([OpenCode Rules](https://opencode.ai/docs/rules/)). The latest stable GitHub release at access is `v1.19.3`, published 2026-10-16 ([OpenCode v1.19.3](https://github.com/anomalyco/opencode/releases/tag/v1.19.3)).
- The OpenCode site also advertises OpenCode v2 and publishes a separate page set under `/v2/docs`. This document uses the `/docs/` pages; the v2 split is recorded under Open gaps.
- This document records documentation statements and quotes. It makes no recommendations and draws no implications from them.

## 1. Instruction files and precedence

### Claude Code

#### Files and scopes

Claude Code documents four instruction-file scopes. The page says the table `lists them in load order, from broadest scope to most specific, so a project instruction appears in context after a user instruction` ([Claude Code memory](https://code.claude.com/docs/en/memory)):

| Scope | Location | Shared with |
| - | - | - |
| Managed policy | macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`; Linux and WSL `/etc/claude-code/CLAUDE.md`; Windows `C:\Program Files\ClaudeCode\CLAUDE.md` | All users in the organization |
| User instructions | `~/.claude/CLAUDE.md` | Only you, across all projects |
| Project instructions | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team members through source control |
| Local instructions | `./CLAUDE.local.md` | Only you, current project |

The same page says: `CLAUDE.md and CLAUDE.local.md files in the directory hierarchy above the working directory are loaded at launch. Files in subdirectories load on demand.` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

#### Load order and nesting

Claude Code loads `CLAUDE.md` and `CLAUDE.local.md` `from your current working directory and every directory above it`. For a session started in `foo/bar/`, it loads `foo/bar/CLAUDE.md`, `foo/CLAUDE.md`, and any `CLAUDE.local.md` files alongside them ([Claude Code memory](https://code.claude.com/docs/en/memory)).

The documented combination rule is: `All discovered files are concatenated into context rather than overriding each other.` ([Claude Code memory](https://code.claude.com/docs/en/memory)). The page states the ordering as `content is ordered from the filesystem root down to your working directory` and, within each directory, `CLAUDE.local.md is appended after CLAUDE.md` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

Files in subdirectories under the working directory are discovered but not loaded at launch: `Claude Code loads each one once Claude reads, writes, or edits another file in that subdirectory` ([Claude Code memory](https://code.claude.com/docs/en/memory)). The page also says that project-root `CLAUDE.md` survives compaction: after `/compact`, `Claude re-reads it from disk and re-injects it into the session` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

Directories added with `--add-dir` do not load their memory files by default. The page says: `By default, CLAUDE.md files from these directories are not loaded.` Loading them requires `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` ([Claude Code memory](https://code.claude.com/docs/en/memory)). `claudeMdExcludes` can skip specific `CLAUDE.md` files in large repositories ([Claude Code memory](https://code.claude.com/docs/en/memory)).

The docs describe `CLAUDE.md` content as context rather than enforcement: `Claude treats them as context, not enforced configuration.` They add that `CLAUDE.md content is delivered as a user message after the system prompt, not as part of the system prompt itself.` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

#### Imports

`CLAUDE.md` files can pull in other files: `CLAUDE.md files can import additional files using @path/to/import syntax.` Imported files are `expanded and loaded into context at launch alongside the CLAUDE.md that references them`; relative paths resolve `relative to the file containing the import, not the working directory`, and imports can recurse `with a maximum depth of four hops` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

Import parsing skips Markdown code spans and fenced code blocks, so a path in backticks is not imported. A path with spaces needs a backslash before each space, and a path wrapped in quotes `isn't imported at all` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

An import in a project-level memory file is external when it resolves outside the working directory. Claude Code shows an approval dialog the first time it encounters such imports and keeps them disabled if declined ([Claude Code memory](https://code.claude.com/docs/en/memory)).

#### AGENTS.md

Claude Code can read `AGENTS.md` in place of `CLAUDE.md`. The page states: `By default, Claude reads AGENTS.md only when you have no CLAUDE.md in your working directory or above it.` A `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` in the working directory or any directory above it counts for that check; the user-level `~/.claude/CLAUDE.md`, the managed `CLAUDE.md`, and `.claude/rules/` files do not count ([Claude Code memory](https://code.claude.com/docs/en/memory)).

The documented file-selection results are ([Claude Code memory](https://code.claude.com/docs/en/memory)):

| Repository has | Claude reads |
| - | - |
| `AGENTS.md`, and no `CLAUDE.md` or `CLAUDE.local.md` in the working directory or above it | `AGENTS.md` |
| `AGENTS.md` and a `CLAUDE.md` or `CLAUDE.local.md` in the working directory or above it | `CLAUDE.md` files only |
| A `CLAUDE.md` that imports `AGENTS.md` | `CLAUDE.md`, with `AGENTS.md` included through the import |

`Reading AGENTS.md directly requires Claude Code v2.1.277 or later.` The docs also list `AGENTS.local.md`, `AGENTS.override.md`, and anything under a `.agents/` directory as `Not read` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

The behavior is configurable through the **Project instructions** setting. The documented values are ([Claude Code memory](https://code.claude.com/docs/en/memory)):

| Value | What Claude reads |
| - | - |
| `claude-md-or-agents-md` | `CLAUDE.md` files, or `AGENTS.md` files when no `CLAUDE.md` or `CLAUDE.local.md` exists in the working directory or above it; this is the default |
| `claude-md-and-agents-md` | Both, with each directory's `CLAUDE.md` files first and its `AGENTS.md` after them |
| `claude-md` | `CLAUDE.md` files only |
| `managed-only` | Only the organization's managed `CLAUDE.md` and auto memory at launch |

The setting can be changed with `/config`, or through `pluginConfigs` under `cc-plugin-agents-md@builtin` in `~/.claude/settings.json`, a `--settings` file, or managed settings. The docs say Claude Code `ignores it in project and local settings files` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

Because `CLAUDE.local.md` counts for the check, the page notes: `adding one to keep your own uncommitted instructions in a project that relies on AGENTS.md stops Claude from reading AGENTS.md for you.` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

An `AGENTS.md` read directly through the setting differs from a `CLAUDE.md` in three documented places: `InstructionsLoaded` hooks do not fire for it, `--add-dir` directories do not contribute their `AGENTS.md`, and an external `@path` import loads only if external imports were already approved ([Claude Code memory](https://code.claude.com/docs/en/memory)).

#### `.claude/rules/`

Claude Code also loads markdown files from `.claude/rules/`. The page says `All .md files are discovered recursively` and `Rules without paths frontmatter are loaded at launch with the same priority as .claude/CLAUDE.md` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

Rules can be scoped with YAML frontmatter: `Rules can be scoped to specific files using YAML frontmatter with the paths field.` A path-scoped rule `loads when Claude uses the Read, Write, or Edit tool on a matching file`, or when Claude views a matching file with a Bash command that counts as a read ([Claude Code memory](https://code.claude.com/docs/en/memory)). `paths` is the only field Claude Code reads from a rule; other fields are ignored ([Claude Code memory](https://code.claude.com/docs/en/memory)).

User-level rules in `~/.claude/rules/` `apply to every project on your machine`, and `Claude Code loads user-level rules before project rules, so a project rule appears later in Claude's context than a user rule.` The docs state: `Neither set overrides the other` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

#### Auto memory

Claude Code documents a second, separate mechanism: `Auto memory lets Claude accumulate knowledge across sessions without you writing anything.` It is stored per repository under `~/.claude/projects/<project>/memory/`, and its `MEMORY.md` index is loaded into every conversation up to `the first 200 lines` or `the first 25KB, whichever comes first` ([Claude Code memory](https://code.claude.com/docs/en/memory)). `Auto memory is on by default in local sessions.` ([Claude Code memory](https://code.claude.com/docs/en/memory)).

### OpenCode

#### Files and scopes

OpenCode's Rules page states: `You can provide custom instructions to opencode by creating an AGENTS.md file.` A project-root `AGENTS.md` applies when working in that directory or its subdirectories, and `~/.config/opencode/AGENTS.md` `gets applied across all opencode sessions` ([OpenCode Rules](https://opencode.ai/docs/rules/)).

For Claude Code compatibility, OpenCode documents these fallbacks ([OpenCode Rules](https://opencode.ai/docs/rules/)):

- Project rules: `CLAUDE.md` in the project directory, `used if no AGENTS.md exists`
- Global rules: `~/.claude/CLAUDE.md`, `used if no ~/.config/opencode/AGENTS.md exists`
- Skills: `~/.claude/skills/`

Three environment variables disable the compatibility layers: `OPENCODE_DISABLE_CLAUDE_CODE=1` for all `.claude` support, `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1` for `~/.claude/CLAUDE.md` only, and `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` for `.claude/skills` only ([OpenCode Rules](https://opencode.ai/docs/rules/)).

#### Discovery and precedence

OpenCode says it `looks for rule files in this order` ([OpenCode Rules](https://opencode.ai/docs/rules/)):

1. `Local files by traversing up from the current directory (AGENTS.md, CLAUDE.md)`
2. `Global file at ~/.config/opencode/AGENTS.md`
3. `Claude Code file at ~/.claude/CLAUDE.md (unless disabled)`

The page states: `The first matching file wins in each category. For example, if you have both AGENTS.md and CLAUDE.md, only AGENTS.md is used. Similarly, ~/.config/opencode/AGENTS.md takes precedence over ~/.claude/CLAUDE.md.` ([OpenCode Rules](https://opencode.ai/docs/rules/)).

The page describes local discovery as traversal up from the current directory. It does not describe loading an `AGENTS.md` from a subdirectory below the current directory ([OpenCode Rules](https://opencode.ai/docs/rules/)).

#### Additional instruction files

OpenCode can load extra instruction files through the `instructions` array in `opencode.json` or `~/.config/opencode/opencode.json` ([OpenCode Rules](https://opencode.ai/docs/rules/)):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["CONTRIBUTING.md", "docs/guidelines.md", ".cursor/rules/*.md"]
}
```

The array accepts paths, glob patterns, and remote URLs; `Remote instructions are fetched with a 5 second timeout`, and `All instruction files are combined with your AGENTS.md files` ([OpenCode Rules](https://opencode.ai/docs/rules/)).

OpenCode does not automatically parse `@` references in `AGENTS.md`: `While opencode doesn't automatically parse file references in AGENTS.md, you can achieve similar functionality in two ways:` The documented ways are the `instructions` field and explicit instructions telling the model to use its Read tool on references ([OpenCode Rules](https://opencode.ai/docs/rules/)).

## 2. Skills

### Claude Code

#### Discovery paths

Claude Code says: `Create a SKILL.md file with instructions, and Claude adds it to its toolkit. Claude uses skills when relevant, or you can invoke one directly with /skill-name.` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

The documented skill locations are ([Claude Code skills](https://code.claude.com/docs/en/skills)):

| Location | Path | Loads in |
| - | - | - |
| Enterprise | `.claude/skills/<skill-name>/SKILL.md` in the managed settings directory | All users on deployed machines |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | All your projects on the machine |
| Project | `.claude/skills/<skill-name>/SKILL.md` | Sessions in the repository |
| Nested | `<subdir>/.claude/skills/<skill-name>/SKILL.md` | Sessions started in or below `<subdir>`, or after Claude works on files there |
| Additional directory | `.claude/skills/<skill-name>/SKILL.md` in an `--add-dir` directory | That session |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` | Wherever the plugin is enabled, as `/plugin-name:skill-name` |
| claude.ai account | Skills enabled for the account | Cowork, cloud, and signed-in terminal sessions |

Discovery walks upward: `Claude Code loads project skills from .claude/skills/ in the directory where you start it and in every parent directory up to the repository root`. Skills below the start directory are lazy-loaded: `Skills in a .claude/skills/ directory below where you started don't load at startup.` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

When names collide, enterprise beats personal, and personal beats project. A plugin skill is namespaced separately, so `A plugin skill and a skill at any of the locations above` both load ([Claude Code skills](https://code.claude.com/docs/en/skills)). A `deploy` skill at the repository root and another in `apps/web/.claude/skills/` both stay available; `/deploy` runs the root skill and `/apps/web:deploy` runs the nested one ([Claude Code skills](https://code.claude.com/docs/en/skills)).

Legacy command files still work: `A file at .claude/commands/deploy.md and a skill at .claude/skills/deploy/SKILL.md both create /deploy` ([Claude Code skills](https://code.claude.com/docs/en/skills)). A skill folder can also load as a plugin if it contains `.claude-plugin/plugin.json` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

#### Frontmatter

Claude Code reads YAML frontmatter from `SKILL.md`. `Claude Code reads the frontmatter only when the opening --- is the file's first line.` Otherwise it treats the whole file as skill content. `All fields are optional. Only description is recommended so Claude knows when to use the skill.` A field name must match exactly; `Claude Code ignores a field it doesn't recognize without reporting an error` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

The documented fields are ([Claude Code skills](https://code.claude.com/docs/en/skills)):

| Field | Documented effect |
| - | - |
| `name` | Command name in the `/` menu; defaults to the directory name |
| `description` | What the skill does and when to use it; Claude uses it to decide when to apply the skill |
| `when_to_use` | Additional trigger guidance, appended to `description` |
| `argument-hint` | Autocomplete hint |
| `arguments` | Named positional arguments for `$name` substitution |
| `disable-model-invocation` | `true` prevents Claude from loading the skill automatically |
| `user-invocable` | `false` hides the skill from the `/` menu and prevents `/name` |
| `allowed-tools` | Tools Claude can use without asking during the invoking turn |
| `disallowed-tools` | Tools removed while the skill is active |
| `model` | Model override while the skill is active |
| `effort` | Effort-level override |
| `context` | `fork` runs the skill in a forked subagent context |
| `agent` | Subagent type when `context: fork` is set |
| `background` | With `context: fork`, whether to wait for the result |
| `hooks` | Hooks registered when the skill is invoked |
| `paths` | Glob patterns that limit automatic activation |
| `shell` | Shell for `` !`command` `` and code blocks |
| `metadata` | Free-form map read by your tooling; Claude Code does not act on it |
| `license` | Accepted but not acted on |
| `compatibility` | Accepted but not acted on |

#### Invocation controls

`By default, both you and Claude can invoke any skill.` Two fields restrict that ([Claude Code skills](https://code.claude.com/docs/en/skills)):

- `disable-model-invocation: true`: `Claude can't invoke the skill on its own.`
- `user-invocable: false`: `Only Claude can invoke the skill.`

The documented effect table is ([Claude Code skills](https://code.claude.com/docs/en/skills)):

| Frontmatter | You can invoke | Claude can invoke | When loaded into context |
| - | - | - | - |
| Default | Yes | Yes | Description always in context; full skill loads when invoked |
| `disable-model-invocation: true` | Yes | Not on its own | Description not in context; full skill loads when invoked |
| `user-invocable: false` | No | Yes | Description always in context; full skill loads when invoked |

The `skillOverrides` setting controls visibility from settings instead of frontmatter. Its documented states are `"on"`, `"name-only"`, `"user-invocable-only"` (hidden from Claude but listed in the `/` menu), and `"off"` (hidden from both) ([Claude Code skills](https://code.claude.com/docs/en/skills)).

#### Invocation syntax

For a direct user invocation, `put its name at the start of your message`. `/deploy staging` runs the skill; after plain text, `go ahead and /deploy to staging` does not run it directly but counts as permission for that message ([Claude Code skills](https://code.claude.com/docs/en/skills)).

Model invocation is description-based: Claude uses the `description` `to decide when to apply the skill`, and skill descriptions are loaded into context while `full skill content only loads when invoked` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

Plugin skills are invoked under their namespace: `my-plugin/skills/review/SKILL.md` becomes `/my-plugin:review`, or `/my-plugin:fancy` when the frontmatter sets `name: fancy` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

`allowed-tools` grants permission only for the invoking turn, and `The grant clears when you send your next message.` Workspace trust does not gate the field: `Claude Code applies a project skill's allowed-tools even in a -p run in a folder you've never trusted.` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

### OpenCode

#### Discovery paths

OpenCode says `Agent skills let OpenCode discover reusable instructions from your repo or home directory` and that skills are `loaded on-demand via the native skill tool` ([OpenCode Skills](https://opencode.ai/docs/skills/)).

The documented locations are ([OpenCode Skills](https://opencode.ai/docs/skills/)):

- `.opencode/skills/<name>/SKILL.md`
- `~/.config/opencode/skills/<name>/SKILL.md`
- `.claude/skills/<name>/SKILL.md`
- `~/.claude/skills/<name>/SKILL.md`
- `.agents/skills/<name>/SKILL.md`
- `~/.agents/skills/<name>/SKILL.md`

For project-local paths, `OpenCode walks up from your current working directory until it reaches the git worktree` and loads matching `skills/*/SKILL.md` under `.opencode/`, `.claude/skills/`, and `.agents/skills/` along the way. Global definitions load from the three global paths ([OpenCode Skills](https://opencode.ai/docs/skills/)).

#### Frontmatter

`Each SKILL.md must start with YAML frontmatter.` The required fields are `name` and `description`; the optional fields are `license`, `compatibility`, and `metadata` ([OpenCode Skills](https://opencode.ai/docs/skills/)).

The page instructs: `Put OpenCode-specific behavior in metadata instead of adding custom top-level fields.` The recognized metadata keys are ([OpenCode Skills](https://opencode.ai/docs/skills/)):

- `opencode/slash`: `set to "true" to expose the skill as a /name command in the TUI`
- `opencode/autoinvoke`: `set to "false" to keep the skill out of model-facing auto-selection guidance`

`name` must be 1-64 characters, lowercase alphanumeric with single hyphen separators, must not start or end with `-`, must not contain `--`, and `Match the directory name that contains SKILL.md`. The equivalent regex is `^[a-z0-9]+(-[a-z0-9]+)*$`. `description` must be 1-1024 characters ([OpenCode Skills](https://opencode.ai/docs/skills/)).

#### Invocation controls

OpenCode lists available skills in the `skill` tool description, as `<available_skills>` entries containing the name and description. The agent loads one by calling `skill({ name: "git-release" })` ([OpenCode Skills](https://opencode.ai/docs/skills/)).

The two metadata controls separate user and model invocation ([OpenCode Skills](https://opencode.ai/docs/skills/)):

- `metadata["opencode/slash"]` set to `"true"` exposes the skill as a `/name` command in the TUI.
- `metadata["opencode/autoinvoke"]` set to `"false"` removes the skill from `<available_skills>`; such skills `can still be selected manually and loaded by exact name`.

#### Permissions

Skill access is controlled by `permission.skill` in `opencode.json`; each entry resolves to `allow`, `deny`, or `ask` ([OpenCode Skills](https://opencode.ai/docs/skills/)):

```json
{
  "permission": {
    "skill": {
      "*": "allow",
      "pr-review": "allow",
      "internal-*": "deny",
      "experimental-*": "ask"
    }
  }
}
```

The documented behavior is: `allow` means `Skill loads immediately`; `deny` means `Skill hidden from agent, access rejected`; `ask` means `User prompted for approval before loading`. Patterns support wildcards ([OpenCode Skills](https://opencode.ai/docs/skills/)).

Permissions can be overridden per custom agent in agent frontmatter, or per built-in agent in `opencode.json`. Skills can be disabled entirely by setting `skill: false` under `tools`; then `the <available_skills> section is omitted entirely` ([OpenCode Skills](https://opencode.ai/docs/skills/)).

## 3. Packaging and distribution

### Claude Code

#### Plugins

Claude Code documents plugins as `a directory of skills, agents, hooks, MCP servers, or other components that Claude Code installs and loads as one unit` ([Claude Code plugins overview](https://code.claude.com/docs/en/plugins/overview)). The manifest is `a JSON file at .claude-plugin/plugin.json`; it `gives the plugin its name and can add a version, a description, and other metadata` ([Claude Code plugins overview](https://code.claude.com/docs/en/plugins/overview)).

The documented component paths include `skills/`, `agents/`, `hooks/hooks.json`, and `.mcp.json` ([Claude Code plugins overview](https://code.claude.com/docs/en/plugins/overview)). Plugin skills are namespaced as `/plugin-name:skill-name` ([Claude Code plugins overview](https://code.claude.com/docs/en/plugins/overview)).

#### Marketplaces

`A marketplace is a repository or directory with a .claude-plugin/marketplace.json file that lists plugins and where to fetch each one.` It is `a catalog, not a hosted store.` ([Claude Code plugins overview](https://code.claude.com/docs/en/plugins/overview)).

The marketplace file requires `a name, an owner, and a plugins array`. Each plugin entry needs a `name` and a `source`; a relative path string points inside the marketplace directory, and a source object points outside it ([Claude Code create marketplace](https://code.claude.com/docs/en/plugins/create-marketplace)).

A marketplace is registered with `/plugin marketplace add` from a GitHub repository, a git URL, a local directory or file, or a hosted `marketplace.json` ([Claude Code plugin install](https://code.claude.com/docs/en/plugins/install)). A plugin is then installed as `<plugin>@<marketplace>` or from the `/plugin` panel ([Claude Code plugin install](https://code.claude.com/docs/en/plugins/install)).

#### Install scopes and project-committed plugins

The three install scopes are documented as ([Claude Code plugin install](https://code.claude.com/docs/en/plugins/install)):

- User scope: `enabled for you in every project on this machine`; the entry goes in `~/.claude/settings.json`.
- Project scope: `enabled for everyone who works in this repository`; the entry goes in `.claude/settings.json`, which you commit.
- Local scope: `enabled for you in this repository only`; the entry goes in `.claude/settings.local.json`.

Committing the project entry does not download the plugin for collaborators: `each collaborator also runs claude plugin install <name>@<marketplace> --scope project once` ([Claude Code plugin install](https://code.claude.com/docs/en/plugins/install)).

A plugin can also be shared through a repository without a marketplace: `To share a plugin through a repository, list it under enabledPlugins in .claude/settings.json or place it under .claude/skills/. Claude Code doesn't scan a project's .claude/plugins/ directory.` ([Claude Code plugin loading](https://code.claude.com/docs/en/plugins/loading)).

`--plugin-dir` loads a plugin from a folder for one session, and `claude plugin install` installs from the shell ([Claude Code plugin install](https://code.claude.com/docs/en/plugins/install)). `extraKnownMarketplaces` and `enabledPlugins` can be declared in project settings; the `extraKnownMarketplaces` entries wait for workspace trust ([Claude Code settings](https://code.claude.com/docs/en/settings)).

Organizations can allowlist or block marketplaces, force-install plugins, and turn off session-only loading through managed settings ([Claude Code plugins overview](https://code.claude.com/docs/en/plugins/overview)).

#### Configured skill paths

Plugin skills load from `<plugin>/skills/<skill-name>/SKILL.md` and are available `wherever the plugin is enabled` ([Claude Code skills](https://code.claude.com/docs/en/skills)). An `--add-dir` directory contributes its `.claude/skills/` to that session; the `permissions.additionalDirectories` setting `grants file access only and loads none of these` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

A skill folder becomes a plugin when it contains `.claude-plugin/plugin.json`, and then loads as `<name>@skills-dir` ([Claude Code skills](https://code.claude.com/docs/en/skills)).

### OpenCode

#### Plugins

OpenCode documents two plugin sources: local JavaScript or TypeScript files in `.opencode/plugins/` or `~/.config/opencode/plugins/`, and npm packages named in the `plugin` array in `opencode.json` ([OpenCode Plugins](https://opencode.ai/docs/plugins/)):

```json
{
  "plugin": ["opencode-helicone-session", "opencode-wakatime", "@my-org/custom-plugin"]
}
```

`npm plugins are installed automatically using Bun at startup` and cached in `~/.cache/opencode/node_modules/`; local plugins load directly from the plugin directory ([OpenCode Plugins](https://opencode.ai/docs/plugins/)). The `opencode plugin <module>` command installs a plugin and updates the config, with `--global` selecting global config ([OpenCode CLI](https://opencode.ai/docs/cli/)).

Plugins load in this documented order ([OpenCode Plugins](https://opencode.ai/docs/plugins/)):

1. Global config
2. Project config
3. Global plugin directory
4. Project plugin directory

`All hooks run in sequence`; duplicate npm packages with the same name and version load once, while a local plugin and an npm plugin with similar names `are both loaded separately` ([OpenCode Plugins](https://opencode.ai/docs/plugins/)).

A plugin is `a JavaScript/TypeScript module that exports one or more plugin functions`; it receives a context object and returns a hooks object. It can add custom tools through the `tool` helper, and plugin tools take precedence over a built-in tool with the same name ([OpenCode Plugins](https://opencode.ai/docs/plugins/)).

The OpenCode Plugins page documents local directories and npm packages as the two load sources. It does not describe a marketplace catalog, and the Ecosystem page lists community plugins with repository links ([OpenCode Plugins](https://opencode.ai/docs/plugins/), [OpenCode Ecosystem](https://opencode.ai/docs/ecosystem/)).

#### Configured skill paths

OpenCode's skill paths are the six directories listed in Section 2: `.opencode/skills/`, `~/.config/opencode/skills/`, `.claude/skills/`, `~/.claude/skills/`, `.agents/skills/`, and `~/.agents/skills/` ([OpenCode Skills](https://opencode.ai/docs/skills/)).

`OPENCODE_CONFIG_DIR` names a custom config directory that is `searched for agents, commands, modes, and plugins just like the standard .opencode directory` ([OpenCode Config](https://opencode.ai/docs/config/)). The docs do not state that this directory is searched for skills ([OpenCode Config](https://opencode.ai/docs/config/)).

## 4. Project-committed settings

### Claude Code

#### Settings files and precedence

Claude Code reads settings from four files ([Claude Code settings](https://code.claude.com/docs/en/settings)):

| Scope | File | Who it affects |
| - | - | - |
| User | `~/.claude/settings.json` | You, in every project on the machine |
| Shared project | `.claude/settings.json` | Everyone working in the folder; commit it in a git repository |
| Project local | `.claude/settings.local.json` | You, in one project |
| Managed | `managed-settings.json` and other managed sources | Everyone the organization deploys it to |

Claude Code also keeps a fifth file, `~/.claude.json`, that it writes for itself. It holds sign-in session data, MCP server configurations, per-project state such as trust decisions, and global config keys; the docs say `you don't need to edit it` ([Claude Code settings](https://code.claude.com/docs/en/settings)).

The documented precedence, highest first, is ([Claude Code settings](https://code.claude.com/docs/en/settings)):

1. Managed settings
2. Command line (`--settings <file-or-json>`)
3. Project local settings (`.claude/settings.local.json`)
4. Shared project settings (`.claude/settings.json`)
5. User settings (`~/.claude/settings.json`)

`When the same key appears in more than one place, Claude Code uses the value from the highest level that sets it.` List keys such as `permissions.allow` merge instead of overriding: `Claude Code combines the lists instead of picking one` ([Claude Code settings](https://code.claude.com/docs/en/settings)).

The docs say `.claude/settings.json` is for `Team permissions, hooks, plugins, and the environment variables the project needs`, and `.claude/settings.local.json` is for `Personal overrides for one project, and testing before you share` ([Claude Code settings](https://code.claude.com/docs/en/settings)).

`permissions.allow` rules and `permissions.additionalDirectories` entries in a project's `.claude/settings.json` are applied `only after you accept the workspace trust dialog for that folder`. `deny` and `ask` rules are not affected ([Claude Code permissions](https://code.claude.com/docs/en/permissions)).

Some keys cannot take effect from a repository file: `permissions.defaultMode` values `auto` and `bypassPermissions` `don't take effect from project or local settings` ([Claude Code settings](https://code.claude.com/docs/en/settings)).

#### Permissions

Claude Code defines three permission rule kinds ([Claude Code permissions](https://code.claude.com/docs/en/permissions)):

- `Allow` rules `let Claude Code use the specified tool without manual approval.`
- `Ask` rules `prompt for confirmation whenever Claude Code tries to use the specified tool.`
- `Deny` rules `prevent Claude Code from using the specified tool.`

`Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome, and rule specificity doesn't change the order.` ([Claude Code permissions](https://code.claude.com/docs/en/permissions)).

`Permission rules are enforced by Claude Code, not by the model.` ([Claude Code permissions](https://code.claude.com/docs/en/permissions)). Rules follow the format `Tool` or `Tool(specifier)`, such as `Bash(npm run build)` or `Read(./.env)` ([Claude Code permissions](https://code.claude.com/docs/en/permissions)).

The documented permission modes are ([Claude Code permissions](https://code.claude.com/docs/en/permissions)):

| Mode | Documented behavior |
| - | - |
| `default` | `Prompts for permission on first use of each tool` |
| `acceptEdits` | Automatically accepts file edits and common filesystem commands |
| `plan` | Reads files and runs read-only shell commands but does not edit source files |
| `auto` | Runs without routine prompts; a background classifier checks actions |
| `dontAsk` | Auto-denies every call that would otherwise prompt |
| `bypassPermissions` | Skips permission prompts except actions no mode auto-approves |

`disableBypassPermissionsMode` and `disableAutoMode` can prevent `bypassPermissions` or `auto` from being used; the docs say these are `most useful in managed settings where they can't be overridden` ([Claude Code permissions](https://code.claude.com/docs/en/permissions)).

#### Hooks

`Hooks are defined in JSON settings files.` They are configured with an event, a matcher group, and one or more handlers ([Claude Code hooks](https://code.claude.com/docs/en/hooks)).

The documented hook locations and scopes are ([Claude Code hooks](https://code.claude.com/docs/en/hooks)):

| Location | Scope | Shareable |
| - | - | - |
| `~/.claude/settings.json` | All your projects | No |
| `.claude/settings.json` | Single project | Yes, can be committed |
| `.claude/settings.local.json` | Single project | No |
| Managed policy settings | Organization-wide | Yes, admin-controlled |
| Plugin `hooks/hooks.json` | When plugin is enabled | Yes |
| Skill frontmatter | Rest of the session after invocation | Yes |
| Subagent frontmatter | While that subagent runs | Yes |

`Hook entries merge across settings levels rather than replacing each other` ([Claude Code hooks](https://code.claude.com/docs/en/hooks)). `disableAllHooks` turns off hooks, but `a "disableAllHooks": false in a project's .claude/settings.json overrides a true in your user settings` ([Claude Code hooks](https://code.claude.com/docs/en/hooks)). Managed settings can restrict hooks with `allowManagedHooksOnly` ([Claude Code hooks](https://code.claude.com/docs/en/hooks)).

Project skill hooks follow the workspace trust rule for settings hooks; project subagent frontmatter hooks `run only after you accept the workspace trust dialog` for the folder the agent file came from ([Claude Code hooks](https://code.claude.com/docs/en/hooks)).

### OpenCode

#### Config files and precedence

OpenCode supports `JSON` and `JSONC` config files ([OpenCode Config](https://opencode.ai/docs/config/)). Its documented precedence order, later overriding earlier, is ([OpenCode Config](https://opencode.ai/docs/config/)):

1. Remote config (`.well-known/opencode`)
2. Global config (`~/.config/opencode/opencode.json`)
3. Custom config (`OPENCODE_CONFIG` env var)
4. Project config (`opencode.json` in project)
5. `.opencode` directories (agents, commands, plugins)
6. Inline config (`OPENCODE_CONFIG_CONTENT` env var)
7. Managed config files
8. macOS managed preferences

`Configuration files are merged together, not replaced. Settings from the following config locations are combined.` ([OpenCode Config](https://opencode.ai/docs/config/)).

The project config is `opencode.json` in the project root. `When OpenCode starts up, it first looks for a config file in the current directory, then traverses up to the nearest Git directory.` The page says the file is `safe to be checked into Git` and documents `permission`, `agent`, `plugin`, and `instructions` as keys in it ([OpenCode Config](https://opencode.ai/docs/config/)).

The `.opencode` and `~/.config/opencode` directories use plural subdirectory names: `agents/`, `commands/`, `modes/`, `plugins/`, `skills/`, `tools/`, and `themes/`. Singular names are `also supported for backwards compatibility` ([OpenCode Config](https://opencode.ai/docs/config/)).

#### Permissions

OpenCode's `permission` config decides whether an action runs automatically, prompts, or is blocked. Each rule resolves to ([OpenCode Permissions](https://opencode.ai/docs/permissions/)):

- `"allow"` — `run without approval`
- `"ask"` — `prompt for approval`
- `"deny"` — `block the action`

Permissions can be set globally with `*` and overridden per tool. A string applies one action to all uses; an object maps patterns to actions ([OpenCode Permissions](https://opencode.ai/docs/permissions/)):

```json
{
  "permission": {
    "shell": {
      "*": "ask",
      "git *": "allow",
      "npm *": "allow",
      "rm *": "deny",
      "grep *": "allow"
    }
  }
}
```

`Rules are evaluated by pattern match, with the last matching rule winning.` The page states: `A common pattern is to put the catch-all "*" rule first, and more specific rules after it.` ([OpenCode Permissions](https://opencode.ai/docs/permissions/)).

The documented defaults are permissive: `Most permissions default to "allow"`, while `doom_loop` and `external_directory` default to `"ask"`. `read` is `"allow"`, but `.env` files are denied by default ([OpenCode Permissions](https://opencode.ai/docs/permissions/)).

`external_directory` controls tool calls that touch paths outside the working directory where OpenCode was started ([OpenCode Permissions](https://opencode.ai/docs/permissions/)). The available permission keys include `read`, `edit`, `glob`, `grep`, `shell`, `task`, `skill`, `lsp`, `question`, `webfetch`, `websearch`, `external_directory`, and `doom_loop` ([OpenCode Permissions](https://opencode.ai/docs/permissions/)).

Agent permissions `are merged with the global config, and agent rules take precedence` ([OpenCode Permissions](https://opencode.ai/docs/permissions/)). `--auto` automatically approves requests that are not explicitly denied; explicit `"deny"` rules `are still enforced` ([OpenCode Permissions](https://opencode.ai/docs/permissions/)).

#### Hooks

OpenCode documents hooks as plugin event subscriptions: `Plugins allow you to extend OpenCode by hooking into various events and customizing behavior.` ([OpenCode Plugins](https://opencode.ai/docs/plugins/)).

The documented events include `tool.execute.before`, `tool.execute.after`, `permission.asked`, `permission.replied`, `session.created`, `session.idle`, `shell.env`, `file.edited`, and `command.executed` ([OpenCode Plugins](https://opencode.ai/docs/plugins/)). A plugin can modify tool arguments before execution, as in the documented `tool.execute.before` example ([OpenCode Plugins](https://opencode.ai/docs/plugins/)).

Project plugins load from `.opencode/plugins/`; global plugins load from `~/.config/opencode/plugins/` ([OpenCode Plugins](https://opencode.ai/docs/plugins/)). The config reference documents `plugin` as an array of npm packages and documents no separate `hooks` key ([OpenCode Config](https://opencode.ai/docs/config/)).

## 5. Subagents, non-interactive or headless runs, and GitHub integrations

### Claude Code

#### Subagents

`Subagents are specialized AI assistants that handle specific types of tasks.` `Each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions`, and Claude delegates to one when a task `matches a subagent's description` ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)).

The documented subagent scopes and priorities are ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)):

| Location | Scope | Priority |
| - | - | - |
| Managed settings | Organization-wide | 1 (highest) |
| `--agents` CLI flag | Current session | 2 |
| `.claude/agents/` | Current project | 3 |
| `~/.claude/agents/` | All your projects | 4 |
| Plugin's `agents/` directory | Where plugin is enabled | 5 (lowest) |

Only `name` and `description` are required in subagent frontmatter. The documented fields include `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `omitClaudeMd`, `effort`, `isolation`, `color`, `initialPrompt`, and `experimental` ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)).

Subagent files are markdown with YAML frontmatter and a system prompt body; the body becomes the system prompt ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)). Plugin subagents do not support the `hooks`, `mcpServers`, or `permissionMode` fields; these are `ignored when loading agents from a plugin` ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)).

Claude uses each subagent's `description` to decide when to delegate. Explicit invocation options are naming the subagent in natural language, `@`-mentioning it in the typeahead, typing `@agent-<name>`, or using `--agent <name>` to run the whole session as that subagent ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)).

A non-fork subagent starts with its own system prompt, a task message, `every level of the CLAUDE.md hierarchy` the main conversation loads, a git status snapshot, preloaded skills, and a sibling roster ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)). Setting `omitClaudeMd: true` removes the user, project, and local `CLAUDE.md` files from its initial context ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)).

#### Non-interactive runs

`Add the -p (or --print) flag to any claude command to run it non-interactively.` ([Claude Code headless](https://code.claude.com/docs/en/headless)).

`--bare` reduces startup time by `skipping auto-discovery of hooks, skills, custom commands, subagents, installed plugins, MCP servers, auto memory, and CLAUDE.md`. Without it, `claude -p` `discovers and loads them as an interactive session would, including anything configured in the working directory or ~/.claude` ([Claude Code headless](https://code.claude.com/docs/en/headless)).

Common non-interactive flags are `--allowedTools` for auto-approval, `--permission-mode` for a permission baseline, and `--output-format` for structured output. A call that needs approval in a Manual-mode `-p` run `is denied unless something approves it` ([Claude Code headless](https://code.claude.com/docs/en/headless)).

`--agents` accepts inline JSON, and in non-interactive mode it `also accepts the path to a JSON file holding the same object` ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)).

#### GitHub Actions

`Claude Code GitHub Actions is a GitHub Action that runs Claude Code inside your repository's workflows.` Mentioning `@claude` in a pull request or issue comment lets Claude `analyze code, implement changes, and push commits` ([Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)).

The action has two documented modes ([Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)):

- Interactive mode: `when the workflow provides no prompt input`, Claude waits for `@claude` in an issue or pull request comment, a pull request review, or a new issue's body or title.
- Automation mode: `when the workflow provides a prompt input`, Claude runs without waiting for a mention.

In both modes the action checks the triggering actor: on issue and pull request events, the user `must have write access to the repository`, and on every event the action `rejects a bot actor unless you list it in allowed_bots` ([Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)).

Setup is either `/install-github-app` or manual installation of the Claude GitHub App, an `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` secret, and a workflow file in `.github/workflows/` ([Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)).

### OpenCode

#### Subagents

OpenCode documents `two types of agents`: `primary agents` and `subagents`. Primary agents `handle your main conversation`; subagents are `specialized assistants that primary agents can invoke for specific tasks` and can also be invoked by `@ mentioning` them ([OpenCode Agents](https://opencode.ai/docs/agents/)).

The documented user-facing built-in agents are `Build` and `Plan` (primary), and `General`, `Explore`, and `Scout` (subagents). The page also lists hidden system agents `Compaction`, `Title`, and `Summary` ([OpenCode Agents](https://opencode.ai/docs/agents/)).

Agents can be configured in JSON under the `agent` key or as markdown files in `~/.config/opencode/agents/` or `.opencode/agents/` ([OpenCode Agents](https://opencode.ai/docs/agents/)). For markdown files, `The markdown file name becomes the agent name.` The `description` option is `required`; `mode` is `primary`, `subagent`, or `all`, defaulting to `all` ([OpenCode Agents](https://opencode.ai/docs/agents/)).

Documented agent options include `model`, `prompt`, `temperature`, `steps`, `disable`, `permission`, `tools` (deprecated), and `hidden`. `hidden: true` hides a subagent from the `@` autocomplete menu but it `can still be invoked by the model via the Task tool if permissions allow` ([OpenCode Agents](https://opencode.ai/docs/agents/)).

Subagents are invoked `Automatically by primary agents for specialized tasks based on their descriptions` or manually by `@ mentioning` one, as in `@general help me search for this function` ([OpenCode Agents](https://opencode.ai/docs/agents/)).

`subagent_depth` controls nesting: the default is `1`, which `allows primary agents to launch subagents but prevents those subagents from launching additional subagents`; `2` allows one more level and `0` prevents all launches ([OpenCode Config](https://opencode.ai/docs/config/)).

#### Non-interactive runs

`Run opencode in non-interactive mode by passing a prompt directly` with `opencode run [message..]` ([OpenCode CLI](https://opencode.ai/docs/cli/)).

The `run` command accepts `--agent`, `--model`, `--format` (`default` or `json`), `--attach` to a running `opencode serve`, `--file`, `--continue`, `--session`, and `--auto` ([OpenCode CLI](https://opencode.ai/docs/cli/)).

`opencode serve` starts `a headless OpenCode server for API access`, with no TUI ([OpenCode CLI](https://opencode.ai/docs/cli/)). `opencode run --attach http://localhost:4096` attaches to a running server to avoid MCP cold starts ([OpenCode CLI](https://opencode.ai/docs/cli/)).

#### GitHub

OpenCode's GitHub integration responds to `/opencode` or `/oc` in issue and pull request comments; `OpenCode will execute tasks within your GitHub Actions runner` ([OpenCode GitHub](https://opencode.ai/docs/github/)).

Installation is `opencode github install`, which sets up the GitHub app, workflow, and secrets, or manual setup with the `anomalyco/opencode/github@latest` action in `.github/workflows/opencode.yml` ([OpenCode GitHub](https://opencode.ai/docs/github/)).

The action's documented inputs include `model` (required), `agent`, `prompt`, `mentions` (defaults to `/opencode,/oc`), `variant`, `oidc_base_url`, and `use_github_token` ([OpenCode GitHub](https://opencode.ai/docs/github/)). Supported events are `issue_comment`, `pull_request_review_comment`, `issues`, `pull_request`, `schedule`, and `workflow_dispatch`; `issues`, `schedule`, and `workflow_dispatch` require a `prompt` ([OpenCode GitHub](https://opencode.ai/docs/github/)).

## Open gaps

- **OpenCode v2 docs.** The site banner says `New OpenCode v2 is now available` and links to `/v2/docs`. At access, `/v2/docs/skills/`, `/v2/docs/config/`, `/v2/docs/permissions/`, `/v2/docs/agents/`, `/v2/docs/plugins/`, and `/v2/docs/cli/` returned HTTP 200, while `/v2/docs/rules/` and `/v2/docs/github/` returned HTTP 404. The inspected v2 pages use terms such as skill catalogs and `policies` ([OpenCode v2 skills](https://opencode.ai/v2/docs/skills/), [OpenCode v2 permissions](https://opencode.ai/v2/docs/permissions/)). This document records the `/docs/` pages and does not merge v2 facts into them.
- **OpenCode nested instruction files.** The Rules page describes local discovery as traversal up from the current directory and does not describe loading `AGENTS.md` from subdirectories below the working directory ([OpenCode Rules](https://opencode.ai/docs/rules/)).
- **OpenCode plugin marketplace.** The Plugins page documents local directories and npm packages, and the Ecosystem page lists community plugins with repository links; neither page describes a marketplace catalog or install scopes ([OpenCode Plugins](https://opencode.ai/docs/plugins/), [OpenCode Ecosystem](https://opencode.ai/docs/ecosystem/)).
- **OpenCode config directory and skills.** `OPENCODE_CONFIG_DIR` is documented as searched for `agents, commands, modes, and plugins`; the page does not list `skills` ([OpenCode Config](https://opencode.ai/docs/config/)).
- **Claude Code AGENTS.md availability.** Direct `AGENTS.md` reading requires v2.1.277 or later and is unavailable in sessions where the built-in plugin is disabled or, for some sessions after an upgrade, until the next session; the docs list these cases ([Claude Code memory](https://code.claude.com/docs/en/memory)).
- **Claude Code page dates.** The Claude Code documentation pages read do not state an individual last-updated date. The version used here is the top changelog entry at access, `2.1.304` dated `October 19, 2026` ([Claude Code changelog](https://code.claude.com/docs/en/changelog)).
- **Documentation-only scope.** No vendor source code, runtime experiment, or third-party write-up was used; negative statements describe what the cited pages do not say, not what the software cannot do.

## Sources

All URLs were accessed on 2026-10-20.

| Source | URL | Version or date read |
| - | - | - |
| Claude Code: How Claude remembers your project | https://code.claude.com/docs/en/memory | Read 2026-10-20; Claude Code docs at `2.1.304` (2026-10-19) |
| Claude Code: Extend Claude with skills | https://code.claude.com/docs/en/skills | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Settings | https://code.claude.com/docs/en/settings | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Configure permissions | https://code.claude.com/docs/en/permissions | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Hooks reference | https://code.claude.com/docs/en/hooks | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Create custom subagents | https://code.claude.com/docs/en/sub-agents | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Run Claude Code programmatically | https://code.claude.com/docs/en/headless | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Claude Code GitHub Actions | https://code.claude.com/docs/en/github-actions | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Plugins overview | https://code.claude.com/docs/en/plugins/overview | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Install and manage plugins | https://code.claude.com/docs/en/plugins/install | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Create a marketplace | https://code.claude.com/docs/en/plugins/create-marketplace | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Plugin loading reference | https://code.claude.com/docs/en/plugins/loading | Read 2026-10-20; Claude Code docs at `2.1.304` |
| Claude Code: Changelog | https://code.claude.com/docs/en/changelog | Read 2026-10-20; top entry `2.1.304`, `October 19, 2026` |
| OpenCode: Rules | https://opencode.ai/docs/rules/ | Read 2026-10-20; page states `Last updated: Oct 19, 2026`; release `v1.19.3` (2026-10-16) |
| OpenCode: Agent Skills | https://opencode.ai/docs/skills/ | Read 2026-10-20; OpenCode `/docs/` set |
| OpenCode: Config | https://opencode.ai/docs/config/ | Read 2026-10-20; OpenCode `/docs/` set |
| OpenCode: Permissions | https://opencode.ai/docs/permissions/ | Read 2026-10-20; OpenCode `/docs/` set |
| OpenCode: Agents | https://opencode.ai/docs/agents/ | Read 2026-10-20; OpenCode `/docs/` set |
| OpenCode: Plugins | https://opencode.ai/docs/plugins/ | Read 2026-10-20; OpenCode `/docs/` set |
| OpenCode: CLI | https://opencode.ai/docs/cli/ | Read 2026-10-20; OpenCode `/docs/` set |
| OpenCode: GitHub | https://opencode.ai/docs/github/ | Read 2026-10-20; OpenCode `/docs/` set |
| OpenCode: Ecosystem | https://opencode.ai/docs/ecosystem/ | Read 2026-10-20; OpenCode `/docs/` set |
| OpenCode: Release v1.19.3 | https://github.com/anomalyco/opencode/releases/tag/v1.19.3 | Published 2026-10-16 |
