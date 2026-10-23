# Which tools can run a skill against fixture repositories in Claude Code and OpenCode

Research for [Which tools can run a skill against fixture repositories and check the result in Claude Code and OpenCode](https://github.com/Habit130/agent-repo-governance/issues/39),
child of [Map: governance model and generator v1](https://github.com/Habit130/agent-repo-governance/issues/4).

- Date: 2026-10-22
- Harnesses: Claude Code `2.1.309` (native build, `/Users/habit/.local/share/claude/versions/2.1.309`); OpenCode `v2.1.2` (Homebrew formula `opencode-v2`, `/opt/homebrew/Cellar/opencode-v2/2.1.2/bin/opencode`)
- Method: read the ticket and the map; read the harnesses' own help output; read the official docs pages cited below; read the installed `skill-creator` plugin files; ran live one-shot sessions in throwaway directories under `/tmp`, including two `claude plugin eval` suites. No credential file, keychain entry or token was read. No GitHub repository was created or deleted; GitHub facts come from the REST docs and local `gh`.
- Cost of the live runs in this document: about USD 0.03 in total, as reported by the harnesses' own cost fields.

Every fact below carries the command, the output, the doc quote or the installed file it rests on. Where a statement is an inference rather than a direct observation, it says so. Where a question is still open, it appears in [Open items](#open-items).

---

## Short answer

Claude Code has a purpose-built harness; OpenCode has a general non-interactive runner and no grader.

| Tool | Runs a skill on a fixture | Checks the result | Answers the skill's question | Isolated from habit's real home |
| --- | --- | --- | --- | --- |
| `claude plugin eval` | Yes: `scaffold_script` builds the fixture workspace, plugin supplies the skill, `--runs` repeats | Built in: `regex`, `tool_used`, `tool_order`, `file_exists`, `llm`, `baseline`; no-plugin baseline and Δ; JSON result; CI exit codes | **No.** The `AskUserQuestion` tool is not present in the child session; observed | Yes, natively: temp home, cwd and Claude Code config per run; no `CLAUDE.md`, `.claude/` or other plugins load |
| `claude -p` | Yes: cwd is the fixture; `/skill-name` in the prompt expands | No grader: assert on exit code, JSON result, `structured_output`, created files, or hook verdicts in your own script | **No.** Denied in Manual mode, removed under `--permission-prompts none` | **No.** A fresh `HOME` or `CLAUDE_CONFIG_DIR` loses the login; `--bare` needs an API key and drops skill discovery |
| Anthropic `skill-creator` | No fixture concept. Test cases run as **subagents in a Claude session**, not as CLI runs | A grader subagent writes `grading.json`; optional blind comparator and analyzer | **No.** Subagents have no `AskUserQuestion` | No; it inherits the session |
| Claude Agent SDK | Yes, but you write the driver and the checks | Your own assertions on the result message | **Yes.** `canUseTool` receives `AskUserQuestion`; the callback can return an answer | Whatever the driver gives it |
| `opencode run` | Yes: cwd is the fixture; project and compatibility skill roots load; `@skill-id` names a skill | No grader: parse the NDJSON event stream, inspect created files, and `opencode stats` for cost | **No.** The `question` tool returns an explicit non-interactive cancellation | Yes, with `HOME` + `XDG_*` + `--standalone`; provider credentials must be re-supplied |
| OpenCode evaluation feature | **None.** No `eval` command, no grader, no baseline | — | — | — |

For the generator and the install, the practical split is: `claude plugin eval` for file-level generator fixtures, a hand-written `claude -p` (or `opencode run`) script when the real project configuration must load, and a plain shell harness with a throwaway `HOME` for the install. Nothing available here answers a question the skill asks.

---

## 1. Claude Code: `claude -p`

### 1.1 What it runs

`claude -p` (or `--print`) runs one non-interactive session in the current directory and prints the reply. From `claude --help` (2.1.309):

```
-p, --print  Print response and exit (useful for pipes).
```

The headless page states: "Claude Code exits with code 0 on success and a non-zero code when the run fails, so your scripts can branch on the exit status", and SIGTERM gives exit 143 ([headless](https://code.claude.com/docs/en/headless)).

Flags that matter for fixtures and checking, from `claude --help` and the [CLI reference](https://code.claude.com/docs/en/cli-reference):

| Flag | Relevance |
| --- | --- |
| `--output-format text\|json\|stream-json` | Result capture. `json` prints one result object. |
| `--json-schema <schema>` | Validated structured output in `structured_output`. |
| `--permission-mode acceptEdits\|auto\|bypassPermissions\|manual\|dontAsk\|plan` | Without one, a run starts in Manual mode and denies calls that need approval. |
| `--allowedTools` / `--disallowedTools` | Per-tool approval; rule syntax such as `Bash(git *)`. |
| `--permission-prompts host\|none` | Who answers permission prompts; `none` removes person-answering tools. |
| `--add-dir` | Extra readable/writable directories; loads their `.claude/skills/`, not their settings. |
| `--plugin-dir`, `--plugin-url` | Load a plugin for the session; skills become `/plugin:skill`. |
| `--settings`, `--setting-sources user,project,local` | Which settings tiers load. |
| `--append-system-prompt`, `--system-prompt`, `--system-prompt-file` | Prompt control (`--system-prompt-file` is hidden from `--help`). |
| `--max-turns`, `--max-budget-usd` | Run and cost bounds (`--max-turns` is hidden from `--help`, documented). |
| `--session-id`, `--resume`, `--no-session-persistence` | Replay and cleanup. |
| `--bare`, `--safe-mode`, `--tools`, `--agents` | Minimal mode / customizations off / built-in tool list / inline agent definitions. |

The headless page adds a security fact that matters for fixture repositories: "Without `--bare`, a `-p` session runs the hooks in a project's `.claude/settings.json` and connects the servers in its `.mcp.json`, even in a folder you've never trusted." A fixture repo is therefore executable code in this mode.

### 1.2 Supplying the fixture and the skill

- **cwd is the fixture.** Project `.claude/`, `CLAUDE.md` and `.mcp.json` load by default; the run writes wherever permissions allow.
- **A skill ships in the fixture** in `.claude/skills/<name>/SKILL.md`, or in a plugin passed with `--plugin-dir`, or in a directory added with `--add-dir` (skills are the one `.claude/` component `--add-dir` loads; `permissions.additionalDirectories` in settings loads none).
- **User-invoked skills work in headless mode.** The headless page says: "User-invoked skills and custom commands work. Include `/skill-name` in the prompt string and Claude Code expands it before running." Only the first stacked skill expands; the rest of the line becomes its arguments.
- **Model-invoked skills** need the `Skill` tool, which is permission-required; grant it with `--allowedTools Skill` or a permissive mode.
- **`--bare`** is the minimal mode: it skips hooks, plugins, skills discovery, `CLAUDE.md`, MCP servers and memory. Skills still resolve by `/skill-name` from `--add-dir` `.claude/skills/`, but Claude is not shown the skill list. It also never reads OAuth or the keychain, so Anthropic auth must be `ANTHROPIC_API_KEY` or an `apiKeyHelper` passed with `--settings`.

Live check, a fixture repository in `/tmp` with `.claude/skills/probe/SKILL.md`, `input.txt` and a `CLAUDE.md`:

```
$ cd /tmp/wf-probe-7CvBiM/cc-fixture/repo
$ env -u CLAUDECODE claude -p "/probe Run the probe." \
    --permission-mode acceptEdits --allowedTools "Read,Write" \
    --model haiku --max-turns 8 --output-format json
{"subtype":"success","is_error":false,"num_turns":4,
 "result":"DONE","total_cost_usd":0.004802440000000001,
 "permission_denials":[],"terminal_reason":"completed", ...}
$ cat out.txt
VALUE=FIXTURE-VALUE
```

Exit code 0. Without `--permission-mode` (or an allow rule) the `Write` call would be denied: since v2.1.302 a `-p` run with no mode set starts in Manual mode, where "a call that needs approval is denied unless something approves it, such as a `PermissionRequest` hook or a `--permission-prompt-tool`" (headless).

### 1.3 Checking the result

Nothing is graded for you. The checks available to a script:

- **Exit code**: 0 success, 1 failure, 143 on SIGTERM.
- **The `json` result object**: `result`, `is_error`, `subtype`, `num_turns`, `session_id`, `total_cost_usd`, `usage`, `model_usage`, `permission_denials`, `terminal_reason`. The SDK's `ResultMessage` reference is the authoritative field list; `subtype` is one of `success`, `error_during_execution`, `error_max_turns`, `error_max_budget_usd`, `error_max_structured_output_retries` ([python SDK reference](https://code.claude.com/docs/en/agent-sdk/python#resultmessage)).
- **`--json-schema`**: the validated object lands in `structured_output`; when Claude declines, the field is absent.
- **`stream-json`**: NDJSON events; the last line is a `result` message. Denials appear as `permission_denied` system messages and in `permission_denials`.
- **Hooks**: a `Stop` hook can block stopping and feed a verdict back; a `PermissionRequest` hook can approve or deny. This is the only in-run grading and steering mechanism.
- **The workspace itself**: your script checks the files the skill wrote.

Observed result of an auth failure, useful as a shape reference: exit 1, `is_error: true`, `terminal_reason: "api_error"`, `result: "Not logged in · Please run /login"`, `total_cost_usd: 0`.

### 1.4 Cost

- `total_cost_usd` plus a per-model breakdown is in the `json` result; the docs call these client-side estimates and warn not to bill from them.
- `--max-budget-usd` stops a run at an estimated spend; restored totals from `--resume` do not count toward it.
- Observed: one haiku run with a skill, four turns and a file write cost **USD 0.0048**; one haiku run that only searched for a missing tool and hit the turn cap cost **USD 0.0054**.
- No documented per-run average; the plugin-eval docs give a six-run example at USD 0.41 ([plugin evals](https://code.claude.com/docs/en/plugin-evals#create-your-first-eval-suite)).

### 1.5 Can a run answer a question the skill asks? No

The docs are explicit in three places:

- `AskUserQuestion` is under "Actions no mode auto-approves": "Tools that require user interaction: the built-in `AskUserQuestion` tool and MCP tools marked `requiresUserInteraction`" ([permission modes](https://code.claude.com/docs/en/permission-modes#actions-no-mode-auto-approves)).
- In `dontAsk`: "`AskUserQuestion` … are denied even when an allow rule matches".
- With `--permission-prompts none`: "Claude Code removes the tools that need an answer from a person, such as `AskUserQuestion`, so Claude can't call them." In a `-p` run with no host, "these requests are denied either way" (headless).

Live check in a scratch directory, asking Claude to use the tool:

```
$ env -u CLAUDECODE claude -p "Call the AskUserQuestion tool to ask exactly: 'Proceed with the probe?' ..." \
    --allowedTools AskUserQuestion --model haiku --max-turns 3 --output-format json
```

The transcript shows `ToolSearch {"query":"select:AskUserQuestion"}` returning `"No matching deferred tools found"`; the model retried the search and hit the turn cap. Exit 1, `terminal_reason: "max_turns"`, `permission_denials: []`, cost USD 0.0054. So the tool was not merely denied: it was not available, and the model had no channel to ask.

`--permission-prompt-tool` covers *permission* prompts only, not `AskUserQuestion`. The only documented way to answer a question is the Agent SDK's `canUseTool` callback (§4).

### 1.6 Can a run use a throwaway home or configuration directory? Not without losing login

Two live checks, both in a scratch fixture:

| Attempt | Result |
| --- | --- |
| `CLAUDE_CONFIG_DIR=/tmp/.../iso-config claude -p ...` | exit 1, `is_error: true`, `result: "Not logged in · Please run /login"`; a fresh config dir was created and nothing else |
| `HOME=/tmp/.../fakehome claude -p ...` | exit 1, `is_error: true`, `result: "Not logged in · Please run /login"`; `fakehome/.claude/` and `fakehome/.claude.json` were created |

So a plain `claude -p` harness cannot fence `~/.agents/`, `~/.claude/` or global instruction files while staying logged in. The two documented alternatives:

- **`--bare` + `ANTHROPIC_API_KEY`** (or `apiKeyHelper` via `--settings`): never reads OAuth or the keychain and skips user discovery, but also skips the skill list, plugins, `CLAUDE.md` and hooks; explicit `/skill-name` still works from `--add-dir` skills. This is suitable only with an API key.
- **`claude plugin eval`** (§2), which builds the isolation itself.

Inference (not documented): plugin eval can authenticate in a temp config because it pre-seeds `.claude.json` and relies on the machine credential; a hand-rolled copy of that arrangement was not attempted here.

---

## 2. Claude Code: `claude plugin eval`

`claude plugin eval` exists in 2.1.309 (`claude plugin eval --help`) and is documented at [code.claude.com/docs/en/plugin-evals](https://code.claude.com/docs/en/plugin-evals). Requirements: "Claude Code v2.1.269 or later", a plugin manifest (`plugin.json` or `.claude-plugin/plugin.json`) or a skills-directory plugin, and the normal credentials: "Every eval run and every judge grader is a real model call on your account."

### 2.1 What a run is

From the docs: "For each run of a case, Claude Code starts a fresh, isolated non-interactive session with only your plugin loaded, sends the prompt, and lets Claude work until it finishes or hits the case's turn or time limit." Each run is "a `claude -p` child process" in "a temporary home directory, working directory, and Claude Code configuration".

A case is a directory under `evals/` (or another configured eval dir) with `prompt.md`, `case.yaml`, or both, plus at least one grader. Layout:

```
my-plugin/
├── .claude-plugin/plugin.json
├── skills/...
└── evals/
    ├── <case>/
    │   ├── prompt.md          # frontmatter: case and run fields; body: the prompt
    │   ├── case.yaml          # optional: context.*, or the whole case
    │   ├── graders/<name>.md  # one grader per file
    │   ├── mocks/             # optional MCP mocks
    │   └── <fixtures, scripts, transcripts>
    └── results/<timestamp>/{aggregate-result.json,report.html,mock-recordings/}
```

`prompt.md` frontmatter fields (unknown keys are an error): `schema_version`, `name`, `description`, `tags`, `plugins`, `runs` (default 3), `expected_outcome`, `model`, `max_turns` (default 10), `timeout_seconds` (default 300), `allowed_tools`, `append_system_prompt`, `env` (only `EVAL_*` keys).

`case.yaml` adds `context.scaffold_script`, `context.history_file`, `context.add_dirs`, `execution.prompt` and `graders`; it requires `schema_version: "1.1"` and `name`.

### 2.2 Supplying the fixture

"Each run starts in an empty workspace." The fixture comes from `case.yaml`:

- `context.scaffold_script`: a Bash script in the case directory. "It runs as you, outside the agent's sandbox, and only when you pass `--scaffold`." Its environment is minimal: `PATH`, `HOME` set to the run's temporary home, `TMPDIR`, `TERM=dumb`; 120-second limit; a non-zero exit fails the run. "Use the script for files and git state only, since project configuration it writes isn't loaded."
- `context.add_dirs`: directories inside the case directory that Claude may read, read-only.
- `context.history_file`: a `.jsonl` transcript to resume.

A skill under test ships in the plugin (`skills/<name>/SKILL.md`), because "Nothing personal or project-level loads": no user settings, hooks, `CLAUDE.md`, MCP servers, other plugins, memory or skills, and "no `.claude/` directory, `CLAUDE.md`, or `.mcp.json` loads from above the workspace or inside it, even one a `scaffold_script` wrote".

### 2.3 Checking the result

Six grader types, "There are no custom-code graders" (plugin-evals, "Choose and weight graders"):

| Type | Options | Passes when |
| --- | --- | --- |
| `regex` | `pattern`, `flags`, `match`, `target` | JS regex matches; `match: not_contains` or `count:N` |
| `tool_used` | `tool`, `input_match`, `min`, `max` | call count in range |
| `tool_order` | `before`, `after` | first matching call order |
| `file_exists` | `path`, `exists` | a file **Claude created** matches the glob |
| `llm` | `criteria`, `focus` | judge votes PASS in at least 2 of 3 votes |
| `baseline` | `baseline_file`, `criteria` | judge finds the run at least as good as a reference transcript |

`target`/`focus` accept `last_message` (default), `trace`, `files` (created paths only), `{ source: file, path: <path> }` (file contents; images for a judge) and `mock_calls`. Graders see neither the case directory nor the prompt.

The suite runs a **no-plugin baseline by default** when a plugin resolves: "a case's runs are repeated with no plugin loaded", giving `WITH`, `W/OUT` and `Δ`. `--ablation none` halves the cost when a delta is unnecessary. `--threshold` (default 1.0) decides the exit code.

Live check, the same probe plugin (skill `probe`, scaffold writes `input.txt` and `git init`, graders `tool_used Skill` and `regex` over `out.txt`):

```
$ cd /tmp/wf-probe-7CvBiM/plugin
$ env -u CLAUDECODE claude plugin eval . --trust-plugin --scaffold \
    --allow-tools Write --runs 1 --ablation none \
    --model haiku --judge-model haiku --no-publish --json result.json
$ jq '{cases, aggregates, costUsd}' result.json
"fixture-case": score 1, passRate 1
  with run: turns 5, error null, graders:
    out-file    passed: "matched VALUE=FIXTURE-VALUE"
    skill-fired passed: "Skill called 1x (expected 1..∞)"
costUsd: 0.00301342
```

Two operational facts from the same run:

- A case file that fails to load (a blank `init` template left beside the real case) makes the command **exit 1 even when the graded case scored 1.0**: `1 case file(s) failed to load`.
- Without `--scaffold`, the workspace is unstaged, the file grader errors (`path "out.txt" does not exist`) and the case scores 0.5; the harness warns on stderr.

### 2.4 Cost

- Docs: a suite makes "roughly cases × runs agent runs with the plugin and the same number again for the no-plugin baseline, plus three short judge calls per `llm` or `baseline` grader per run".
- `--max-cost-usd` is a list-price ceiling checked before each run; hitting it exits 2 with `partial: true` and `partialReason: cost_ceiling`, and paid graders are skipped for runs already started.
- `-j/--concurrency 1-8` shortens wall-clock; each run is a full `claude` child on the same credential and rate limit.
- Observed: one haiku case, one run, no baseline, two free graders, 5 turns → **USD 0.0030**. The `ask`-probe run (two cases, one failed without `--scaffold`) cost USD 0.0036.

### 2.5 The question problem: measured

A case with `allowed_tools: [AskUserQuestion, Skill]` and a skill instructing one `AskUserQuestion` call:

```
NO-ANSWER=AskUserQuestion tool is unavailable in this session (ToolSearch found no matching tool).
```

The transcript (`--keep-temp`, `out/trace.jsonl`) shows `Skill` loaded, then `ToolSearch {"query":"select:AskUserQuestion"}` → `"No matching deferred tools found"`. The run ended in 4 turns, no error, and its last message passed the regex grader. So even though the docs list `AskUserQuestion` among the read-only tools a case may allow, the child `claude -p` session has no such tool. **A generator run that waits for habit's confirmation cannot complete inside `claude plugin eval`.**

### 2.6 Isolation: what a run can and cannot touch

Each run gets a temp `HOME`, cwd and Claude Code config. Observed in a kept run directory (`--keep-temp`):

```
/private/tmp/e-w8z3Nw/
├── config/          # temp Claude Code config: settings.json (DISABLE_AUTOUPDATER), .claude.json, projects/
├── sealed/home/     # temp HOME: cwd/, .gitconfig, .config/git, .aws placeholders
├── sealed/tmp/      # temp TMPDIR
└── out/trace.jsonl
```

Consequences, from the docs:

- Your settings, hooks, `CLAUDE.md`, MCP servers, other plugins, memory and skills are absent; `add_dirs` is read-only.
- Managed policy still applies.
- The Artifact tool is off; the case definitions are hidden from the agent.
- Bash grants run under Claude Code's OS sandbox: "Writes are confined to the run's workspace, your home directory and Claude Code configuration are unreadable, and network access is limited to domains you grant." So a skill that installs into `~/.agents/` cannot do so: the temp home is unreadable to the agent, and shell writes are confined to the workspace. The install is not testable here.
- There is no inherited `gh` authentication: the temp home has no `gh` config, and the child environment withholds everything but a small allowlist (model-provider variables, most `ANTHROPIC_*`/`CLAUDE_CODE_*`, and `EVAL_*`). A generator fixture that inspects real GitHub state cannot do so unless the case passes a token through `EVAL_*` and the skill knows to read it, and network access is granted.
- `--trust-plugin` is required when stdin/stdout is not a terminal or `--json` is used; the first run in an untrusted directory otherwise refuses with exit 1.

### 2.7 Exit codes and result document

| Code | Meaning |
| --- | --- |
| 0 | Every case at or above `--threshold` |
| 1 | Below threshold, a case failed to load, no cases, untrusted, invalid option, or a run ended on an API error |
| 2 | `--max-cost-usd` hit, or the credential was rejected (`partial: true`) |
| 130 / 143 | Interrupted / terminated |

The JSON document (`--json [path]` or `aggregate-result.json`) has `schemaVersion: 1`, `partial`/`partialReason`, `aggregates.overallScore`/`casesPassed`/`casesTotal`/`meanDelta`, `cases[].aggregates.score`/`delta`, `cases[].arms.with[].error`/`aborted`/`skippedPaidGraders`, `costUsd`, `durationSeconds`, `claudeVersion`. The with-minus-without delta never changes the exit code.

### 2.8 Limits worth knowing

- Needs a plugin manifest; a bare skill directory needs one added (or must be a skills-directory plugin).
- Project configuration never loads, so a skill that depends on `AGENTS.md`/`CLAUDE.md` being *loaded* is not faithfully exercised; a skill that *reads* those files with `Read` is.
- `Bash`, `Write`, `Edit`, `WebFetch`, `WebSearch` are removed unless granted with `--allow-tools`; case `allowed_tools` and a skill's `allowed-tools` cannot widen that.
- No custom-code grader; `file_exists` counts only files Claude created (not scaffold files or edited files), so grade contents with `{ source: file, path }`.
- Report publishing can be suppressed with `--no-publish`; `--json` is quiet.

---

## 3. Anthropic `skill-creator`

Installed at `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator` (plugin `skill-creator`; `plugin.json` has `name`, `description`, `author` and **no version field**). Public copy: [github.com/anthropics/skills/tree/main/skills/skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator). Docs: [Run evals with skill-creator](https://code.claude.com/docs/en/skills#run-evals-with-skill-creator), [agentskills.io/skill-creation/evaluating-skills](https://agentskills.io/skill-creation/evaluating-skills).

**The test cases are not CLI runs.** `SKILL.md:171`: "For each test case, spawn two subagents in the same turn — one with the skill, one without." The run prompt is prose: skill path, task, input files, output directory. This only works inside a Claude Code session, not from a shell harness.

The `claude` CLI is used only for description-trigger evaluation:

- `scripts/run_eval.py:70-76`:
  ```
  claude -p <query> --output-format stream-json --verbose --include-partial-messages
  ```
  with `cwd=project_root` and `CLAUDECODE` removed from the environment. It writes a temporary command stub into `.claude/commands/` and detects whether the stream shows a `Skill`/`Read` tool call naming that stub.
- `scripts/improve_description.py:26`: `claude -p --output-format text` with the prompt on stdin.

Grading is a **subagent** following `agents/grader.md`, writing `grading.json` with `expectations[].{text,passed,evidence}`, `summary`, `execution_metrics` and `timing` (schema in `references/schemas.md`). There is no `--json-schema` call anywhere in the plugin, no dollar cost field (only `total_tokens`/`duration_ms` scraped from completion notifications), and no fixture or isolation concept: `evals.json` `files` is consumed by the subagent workflow, not by `run_eval.py`. Trigger evaluation runs in parallel (`ProcessPoolExecutor`, default 10 workers) but inherits the user's whole Claude Code environment.

For this ticket: skill-creator is an authoring and iteration loop, not a fixture acceptance harness. It cannot run a skill against a prepared repository under CLI control, cannot grade files against assertions in a scripted way, and cannot answer `AskUserQuestion` (unavailable in subagents).

---

## 4. Claude Code: the Agent SDK is the only question-answering host

[Handle user input](https://code.claude.com/docs/en/agent-sdk/user-input) documents both permission requests and clarifying questions arriving at `canUseTool`:

> "Both trigger your `canUseTool` callback, which pauses execution until you return a response."

> "When Claude needs more direction … it calls the `AskUserQuestion` tool. This triggers your `canUseTool` callback with `toolName` set to `AskUserQuestion`. The input contains Claude's questions as multiple-choice options, which you display to the user and return their selections."

If you restrict tools, "include `AskUserQuestion` in that array. Otherwise, Claude won't be able to ask clarifying questions." The callback can stay pending indefinitely — which is exactly why a CLI runner cannot service it and an SDK driver can.

Cost accounting in the SDK is the `ResultMessage` (`total_cost_usd`, `usage`, `num_turns`, `is_error`, `subtype`, `permission_denials`). Skills and plugins load in SDK sessions ([SDK skills](https://code.claude.com/docs/en/agent-sdk/skills), [SDK plugins](https://code.claude.com/docs/en/agent-sdk/plugins)).

So: answering the generator's confirmation is possible, but it means writing a small SDK driver (TypeScript or Python) that launches the skill, answers the one question through `canUseTool`, and asserts on the result. No installed tool does this out of the box; whether an SDK package is already available on this Mac was not checked.

---

## 5. OpenCode: `opencode run`

### 5.1 Version and shape

`opencode v2.1.2` is the v2 rewrite (Homebrew `opencode-v2`). Relevant subcommands from `opencode --help`: `run`, `session`, `stats`, `serve`, `api`, `debug`, `plugin`, `auth`, `models`. There is **no `eval` subcommand**, and the v2 docs navigation (`https://opencode.ai/llms.txt`) lists no evaluation page.

`opencode run` sends one message and prints the reply; `--help`:

```
--model, -m string   Model to use in the format provider/model#variant
--agent string       Agent to use
--format choice      Output format (choices: default, json)
--file, -f string    File to attach to the message
--auto               Auto-approve permissions that are not explicitly denied
--standalone         Run with a private server instead of the background service
--session, -s string Session ID to continue, or to create if it does not exist
--fork, --continue, --title, --thinking
```

The CLI docs: "`opencode run` … is designed for scripts, CI jobs, and other workflows that need model output directly in the terminal", and `--format json` "Emit newline-delimited JSON for scripts" ([CLI commands](https://opencode.ai/v2/docs/cli/commands/)).

### 5.2 Supplying the fixture and the skill

- **cwd is the fixture.** `opencode run` has no directory flag; the CLI's directory argument (`opencode ~/project`) is for opening a project, and `run`'s usage is `[<message...>]`. Run it from inside the fixture.
- **Skills** ([Skills](https://opencode.ai/v2/docs/skills/)) are discovered from, in increasing precedence:
  - global `~/.config/opencode/skills`, and compatibility `~/.claude/skills`, `~/.agents/skills`;
  - project `.opencode/skills`, and compatibility `.claude/skills`, `.agents/skills`, searched from the cwd up to the project root;
  - explicit `skills` entries in `opencode.json(c)`.
  A skill is a root-level `<name>.md` or a directory containing `SKILL.md`; the **ID comes from the path**, not the frontmatter `name`. `metadata.opencode/autoinvoke: false` (or `disable-model-invocation: true`) hides it from the model but leaves it loadable.
- **Explicit invocation**: "To load a skill yourself, mention it in your prompt as `@skill-id`." The model can also call the `skill` tool with the exact ID. In a run, `@probe` worked.
- **Project config loads**: `opencode.json(c)` in the project root or `.opencode/`, merged from the farthest ancestor to the cwd, then `.opencode` overrides direct files; global `~/.config/opencode/opencode.json(c)` below, system `/Library/Application Support/opencode` above ([Config](https://opencode.ai/v2/docs/config/)). A fixture repository can therefore carry its own permissions, agents, plugins, and skills.

Live fixture check: `/tmp/.../oc-fixture/repo` with `.opencode/skills/probe/SKILL.md`, `input.txt`, `git init`:

```
$ opencode run --standalone --format json -m deepseek/deepseek-flash "@probe Run the fixture probe on this workspace."
TOOLS: skill {'id': 'probe'} completed
       read  input.txt completed
       write out.txt completed
TEXT: DONE
STEP_FINISH cost 0.0009565080000000000 tokens {...}
STEP_FINISH cost 0.0004450560000000000 ...
STEP_FINISH cost 0.0001194180000000000 ...
$ cat out.txt
VALUE=FIXTURE-VALUE
```

Exit 0. Total of the three step costs: **USD 0.00152**.

### 5.3 Checking the result

No grading exists; a script parses the stream and inspects the workspace:

- `--format json` emits NDJSON events keyed by `type`: `step_start`, `text`, `tool_use`, `step_finish`, `error`. `tool_use` carries `part.tool` and `part.state.status`/`error`; `step_finish` carries `cost` and `tokens`; `text` carries the reply.
- Exit code is 0 on a completed run and 1 on a startup/provider error. Observed: `provider.no-route` prints an `error` event and exits 1; a permission rejection does **not** fail the run (exit 0) and is reported only in the tool state.
- `opencode session export` dumps a session as JSON; `opencode stats --json --cost` reports cost and token details; `opencode session list --format json` lists sessions.
- Result checks are therefore the same kind of work as a `claude -p` harness: write assertions over events, transcripts and files.

### 5.4 Cost

`step_finish` carries a per-step `cost` (USD, provider-priced) and token counts; summing the stream gives the run cost. `opencode stats --cost --json` aggregates usage. There is no cost-ceiling flag on `run` and no documented per-run estimate. Observed costs: USD 0.0015 for the fixture run, USD 0.0001–0.0002 for short question/permission probes using `deepseek/deepseek-flash`.

### 5.5 Questions and permissions in a non-interactive run: refused

**Question tool.** The `question` tool "pauses execution and presents one or more questions to the user" and needs `question` permission; "A client must support the interactive form, and dismissing it cancels the question" ([Tools](https://opencode.ai/v2/docs/tools/)). Live:

```
$ opencode run --standalone --format json -m deepseek/deepseek-flash \
    "Call the question tool exactly once to ask: 'Proceed?' ..."
{"type":"tool_use", ... "tool":"question","state":{"status":"error",
 "error":"This non-interactive run cannot ask the user questions, so the question was cancelled. Continue without an answer; make reasonable assumptions and state them." ...}}
{"type":"text", ... "text":"NO-ANSWER=question tool errored: non-interactive run cannot ask user questions"}
```

Exit 0. The model continues without an answer. This is the one place a harness tells the model exactly what happened.

**Permissions.** `ask` rules are decided by the client. In `run` with no interactive client, a matching `ask` rule is rejected immediately:

```
{"type":"tool_use", ... "tool":"write","state":{"status":"error",
 "error":"This non-interactive run cannot ask the user for permission, so the request was rejected. Continue without this action."}}
```

With `--auto`, the same `ask` rule was approved and the file was written. In the `deny` run no file was created, but the only tool call was a `shell` attempt that the run's global `ask` rule rejected, so the `deny` rule itself was not separately observed. Action names matter: a rule on `write` did not match; the tool maps to the `edit` action ([Tools](https://opencode.ai/v2/docs/tools/)).

The docs put the burden on the client: "Non-interactive clients must decide how to handle approval requests; configured deny rules always remain enforced" ([Permissions](https://opencode.ai/v2/docs/permissions/)). `run` has no flag to supply canned answers, so the generator's confirmation cannot be answered here either.

### 5.6 Isolation: paths are easy, credentials and the shared server are not

`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME` and `HOME` all move the paths; `opencode debug paths` shows it:

```
$ HOME=/tmp/oc XDG_CONFIG_HOME=/tmp/oc/conf XDG_DATA_HOME=/tmp/oc/data \
  XDG_STATE_HOME=/tmp/oc/state XDG_CACHE_HOME=/tmp/oc/cache opencode debug paths
home   /tmp/oc
data   /tmp/oc/data/opencode
config /tmp/oc/conf/opencode
state  /tmp/oc/state/opencode
cache  /tmp/oc/cache/opencode
db     /tmp/oc/data/opencode/opencode.db
```

Two problems, both observed:

- **No provider credential.** The isolated run answered `{"type":"error", ... "error":{"type":"provider.no-route","message":"Model unavailable: deepseek/deepseek-flash"}}` and exited 1. Credentials live under the data directory or in provider environment variables. The docs' CI example passes a provider key as a secret (`ANTHROPIC_API_KEY`) with `--standalone` ([commands](https://opencode.ai/v2/docs/cli/commands/)), and config supports `{"providers":{"anthropic":{"settings":{"apiKey":"{env:ANTHROPIC_API_KEY}"}}}}` substitution ([config](https://opencode.ai/v2/docs/config/)). So isolated runs must be given credentials; they cannot inherit habit's stored ones without touching the real data dir.
- **The shared background server.** "By default, OpenCode discovers or starts one shared background server for your user account. Every local OpenCode client connects to that server, which owns sessions, configuration, integrations, permissions, and tool execution" ([CLI intro](https://opencode.ai/v2/docs/cli/)). With an isolated environment and the real user's server running, `opencode debug config` failed: "Managed service port 49374 on 127.0.0.1 is already in use by another process." `opencode run --standalone` starts a private server and worked. **Use `--standalone` for every isolated fixture run.**

Isolation is otherwise effective for files: the isolated tree contained only `conf/`, `data/`, `state/`, `cache/` and the fixture; no real `~/.agents/` or `~/.claude/` was written. But there is no OS sandbox around the agent's shell tool, so a skill that writes to an absolute path outside the fixture still can (with real permissions) unless the fixture's `permissions`/agents config denies it. The fixture repo's own `.opencode/opencode.json` is loaded, which is both a tool (pin permissions for a test) and a hazard (an untrusted fixture can change permissions and plugins).

### 5.7 OpenCode has no evaluation feature

Evidence: `opencode --help` lists no `eval` subcommand; the docs index (`opencode.ai/llms.txt`) has no evaluation or benchmark page; `opencode run --help` offers no grader, baseline, threshold or report option; the binary's plugin system is for runtime plugins, not tests. The only built-in "check" surfaces are session export and `stats`.

---

## 6. GitHub fixture repositories

Facts below are from the REST docs and the local `gh` (2.98.0, authenticated as `Habit098`). No repository was created or deleted for this ticket.

### 6.1 Who can create and delete, and with what token

A token creates a repository **for the authenticated user** (`POST /user/repos`); there is no way to create a repository under another personal account. So fixtures created by the agent account belong to `Habit098`, and fixtures created "under Habit130" require Habit130's own session (browser or a token of Habit130) — the agent cannot create them.

| Operation | Classic token | Fine-grained token |
| --- | --- | --- |
| Create a repository for the authenticated user | `public_repo` for public, `repo` for private | "Administration" (write) **or** "Repository creation" (write) |
| Delete a repository | `delete_repo` | "Administration" (write) |
| Create/update/delete a ruleset | `repo` (Administration) | "Administration" (write) |
| Add a collaborator | `repo` | "Administration" (write) |
| Create a commit status | `repo:status` (or `repo`) | "Commit statuses" (write) |

Sources: [create a repository](https://docs.github.com/en/rest/repos/repos#create-a-repository-for-the-authenticated-user), [delete a repository](https://docs.github.com/en/rest/repos/repos#delete-a-repository), [rulesets](https://docs.github.com/en/rest/repos/rules), [collaborators](https://docs.github.com/en/rest/collaborators/collaborators), [commit statuses](https://docs.github.com/en/rest/commits/statuses).

The local consequence is concrete: `gh auth status` shows the machine token's scopes are `gist`, `read:org`, `repo`, `workflow` — **no `delete_repo`**. The `repo` scope covers creation; deletion is the blocked half until the token gains `delete_repo` (`gh auth refresh -s delete_repo`, which needs habit's authorization) or a fine-grained token with Administration write replaces it. `gh repo delete owner/repo --yes` states the same requirement in its help text, and with no repository argument `--yes` is ignored and it still prompts.

Creating under Habit130 from the agent account is not possible. Two workable shapes:

- Fixtures owned by `Habit098`, created and deleted by the agent token (deletion needs the scope above).
- Fixtures created by habit's own session (or with habit's token), which no agent should hold.

### 6.2 Rulesets

Rulesets are available "in public repositories with GitHub Free … and in public and private repositories with GitHub Pro, GitHub Team, and GitHub Enterprise Cloud" ([gated-feature note](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)). So a **public** throwaway repository gets rulesets on any plan; a **private** one needs Pro. The plan is not visible here: `gh api user` returned `"plan": null` for the authenticated account, and Habit130's plan is not exposed to this token.

Rulesets are repository administration: "People with admin access to a repository … can create, edit, and delete rulesets for a repository." The owner of a fixture repo can therefore set up and remove its ruleset without help.

`gh ruleset` only reads (`check`, `list`, `view`); creating one is a REST call:

```
POST /repos/{owner}/{repo}/rulesets
{
  "name": "fixture-gate",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [{ "context": "governance-gate" }]
      } },
    { "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      } }
  ]
}
```

The documented fields used above: `target` is `branch`, `tag` or `push`; `enforcement` is `disabled`, `active` or `evaluate`; `conditions.ref_name.include` accepts patterns plus `~DEFAULT_BRANCH` and `~ALL`; `rules[]` includes `deletion`, `non_fast_forward`, `required_status_checks`, `pull_request`; `bypass_actors` takes actor types such as `RepositoryRole` (and docs note `OrganizationAdmin` "is not applicable for personal repositories"). Sources: [REST rules](https://docs.github.com/en/rest/repos/rules), [available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets). A new repository must have a commit (for example `auto_init: true`) before a branch condition matches.

A required status check is satisfiable without Actions by posting a commit status: `POST /repos/{owner}/{repo}/statuses/{sha}` with `context: "governance-gate"`, `state: "success"`. **Check runs are different:** the checks API is "only available to GitHub Apps. OAuth apps and authenticated users can view check runs … but they are not able to create them" ([checks availability](https://docs.github.com/en/rest/checks/runs)). A fixture that must exercise a real check-run producer needs a GitHub App; a fixture that only needs the required check to turn green can use a commit status.

### 6.3 Collaborators

`PUT /repos/{owner}/{repo}/collaborators/{username}` with `{"permission":"push"}` creates an invitation; it is not active until accepted. The invitee lists `GET /repos/{owner}/{repo}/invitations` and accepts with `PATCH /user/repository_invitations/{invitation_id}` **using the invitee's own token**; the owner cannot accept on their behalf. Deleting a pending invitation is `DELETE /repos/{owner}/{repo}/invitations/{invitation_id}`. Fine-grained tokens need "Administration" (write) to add a collaborator; the accept endpoint's fine-grained token list names GitHub App user access tokens ([collaborators](https://docs.github.com/en/rest/collaborators/collaborators), [invitations](https://docs.github.com/en/rest/collaborators/invitations)).

Consequences for fixtures:

- A fixture owned by `Habit098` that needs `Habit130` as collaborator needs one acceptance step by habit's account. Until then, the invitation is pending and `Habit130` has no access.
- Adding `Habit098` to a fixture owned by `Habit130` likewise leaves the agent waiting for an acceptance it cannot perform under its own token.
- Secret/credential material is not needed to add a public-repo collaborator; `push` permission is enough for the agent to branch, commit, push and open PRs in a fixture.

### 6.4 Limits that matter

| Limit | Figure | Source |
| --- | --- | --- |
| Primary REST rate limit, authenticated user | 5,000 requests/hour (shared by PATs, OAuth apps and app tokens acting for the user) | [rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) |
| Concurrent requests | 100 | secondary-rate-limit doc |
| Endpoint points | 900 points/minute; `POST`/`PATCH`/`PUT`/`DELETE` cost 5 points, most reads 1 | same |
| Content-generating requests | ~80/minute and 500/hour; "some endpoints have lower content creation limits" | same |
| Actions minutes, private repos | GitHub Free: 2,000 minutes/month; public repos free on standard runners | [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) |

Fixture work is a handful of mutations per repository (create, init commit, ruleset, collaborator, status), so the rate limits are not the constraint; the practical costs are the **scope change for deletion** and the **two-account acceptance step**. No documented per-account cap on repository creation beyond the secondary content limits was found; deletion is immediate and irreversible, so a fixture cleanup script should record the repository names it created rather than rediscovering them.

---

## 7. Isolation compared

| Need | `claude plugin eval` | `claude -p` (hand-rolled) | `opencode run` (hand-rolled) |
| --- | --- | --- | --- |
| Throwaway home/config | Built in per run | No; fresh `HOME`/`CLAUDE_CONFIG_DIR` loses login; `--bare` needs an API key | Yes via `HOME`/`XDG_*`; provider key must be passed |
| Real `~/.agents/` untouched | Yes; shell writes confined to workspace, temp home unreadable | Only if the skill never writes there (no fence) | Only if the skill never writes there (no fence) |
| Real harness settings/global instructions | Not loaded | Loaded | Loaded unless `XDG_CONFIG_HOME`/`HOME` moved |
| Fixture repo's own config | Not loaded (by design) | Loaded, including hooks and `.mcp.json` | Loaded, including `.opencode/` permissions and plugins |
| GitHub identity | None (`gh` unauth; env allowlist) | habit's real `gh` (Habit098) | habit's real `gh` (Habit098) |
| Answers a question | No | No | No |
| Built-in grading | Yes | No | No |
| Cost ceiling | `--max-cost-usd` | `--max-budget-usd` | None |

---

## 8. Constraints for later tickets

Facts, not decisions:

- **The generator's one confirmation cannot be answered by any of the real harnesses.** `claude plugin eval` has no `AskUserQuestion` in the child; `claude -p` denies or removes it; `opencode run` cancels it with an explicit message. Only an Agent SDK driver with `canUseTool` can answer it. Any fixture strategy has to either pre-answer in the prompt/state or use an SDK driver.
- **`claude plugin eval` is the only ready-made fixture harness.** It brings a scaffold, repeated runs, a no-plugin baseline, declarative graders, a cost ceiling, CI exit codes and per-run isolation. It needs the generator packaged as a plugin, and it cannot see `AGENTS.md`/`CLAUDE.md` as loaded configuration or call GitHub with habit's `gh` credentials.
- **`claude -p` is the faithful path.** It loads the real project configuration, but it is not isolated, starts in Manual mode (writes and shell need a permission mode or allow rules), and needs hand-written checks.
- **The install is a script, not a skill.** Neither agent harness has a script-fixture mode. `claude plugin eval`'s Bash sandbox confines writes to the run workspace, so the temp home cannot receive an install, and OpenCode has no sandbox at all. Install verification needs a separate shell-level harness with `HOME`/`XDG_*` overrides, plus the generator's machine check.
- **Isolation costs credentials.** Claude Code and OpenCode both store auth under the config/data directory a throwaway environment replaces. Fixture runs need either an API key in the environment or a deliberate reuse of the real credential store (which defeats the isolation goal for install writes).
- **Cost per fixture run is small but multiplicative.** Observed: USD 0.003 for one haiku plugin-eval run; USD 0.0015 for one OpenCode deepseek-flash run; a default plugin-eval suite is 3 runs × 2 arms per case. Budgets and `--runs 1 --ablation none` matter.
- **Version sensitivity.** Claude Code's plugin eval requires 2.1.269+ and is server-switchable ("plugin eval is currently unavailable" if Anthropic turns it off); OpenCode v2 is a rewrite whose flags (`--auto`, `--standalone`, `--format json`) may change. Re-check both on upgrade.

---

## Open items

- Does `claude plugin eval` pass any option that would let a child answer `AskUserQuestion`? No documented channel; one live run says the tool is absent. A future version could change this.
- Is the LLM-grader default model "haiku" (help text) or "the model Claude Code uses for background tasks" (docs)? The help says `--judge-model` default haiku; the docs say background model. Scores may differ across machines.
- Can a `claude plugin eval` case reach GitHub at all with a token passed through `EVAL_*` and a Bash grant? Not tested; the shell sandbox's network policy and the missing `gh` config make it doubtful.
- Does OpenCode's `--standalone` private server honor the caller's `HOME`/`XDG_*` for all session state (sessions, logs, repo cache)? Paths moved in `debug paths` and the isolated run wrote only inside the isolated tree, but the DB and server behavior were not audited beyond that.
- Does `opencode run` accept a directory argument after the message (`opencode run "..." /path`)? The docs use cwd; not tested because it could be read as message text.
- Which GitHub plan is Habit130 on? Rulesets on a public fixture need no paid plan; rulesets on a private fixture need Pro. `gh api user` does not expose the plan here.
- Can a collaborator with admin permission delete a user-owned fixture repository they do not own? The docs describe deletion as an admin-permission action but also identify the owner; only the owner-token path was checked (the scope requirement above). Not tested because no repository was created.
- Is there a documented per-account repository-creation cap? None was found; the secondary content limits are the documented bound.

---

## Sources

Claude Code (read 2026-10-22):

- [Headless mode](https://code.claude.com/docs/en/headless)
- [CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals)
- [Permission modes](https://code.claude.com/docs/en/permission-modes)
- [Tools reference](https://code.claude.com/docs/en/tools-reference)
- [Skills](https://code.claude.com/docs/en/skills)
- [Agent SDK: Handle user input](https://code.claude.com/docs/en/agent-sdk/user-input)
- [Agent SDK: Python reference](https://code.claude.com/docs/en/agent-sdk/python)
- Installed CLI `claude --help`, `claude plugin --help`, `claude plugin eval --help`, `claude plugin eval init --help` (2.1.309)
- Installed `skill-creator` plugin at `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator`

OpenCode (read 2026-10-22):

- [Skills](https://opencode.ai/v2/docs/skills/)
- [Permissions](https://opencode.ai/v2/docs/permissions/)
- [Tools](https://opencode.ai/v2/docs/tools/)
- [CLI commands](https://opencode.ai/v2/docs/cli/commands/)
- [CLI intro](https://opencode.ai/v2/docs/cli/)
- [Config](https://opencode.ai/v2/docs/config/)
- [Models](https://opencode.ai/v2/docs/models/)
- Installed `opencode --help`, `opencode run --help`, `opencode debug paths|config|agents`, `opencode session --help`, `opencode stats --help` (v2.1.2)

GitHub (read 2026-10-22):

- [Create a repository for the authenticated user](https://docs.github.com/en/rest/repos/repos#create-a-repository-for-the-authenticated-user)
- [Delete a repository](https://docs.github.com/en/rest/repos/repos#delete-a-repository)
- [REST API endpoints for rules](https://docs.github.com/en/rest/repos/rules)
- [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [REST API endpoints for collaborators](https://docs.github.com/en/rest/collaborators/collaborators)
- [REST API endpoints for repository invitations](https://docs.github.com/en/rest/collaborators/invitations)
- [REST API endpoints for commit statuses](https://docs.github.com/en/rest/commits/statuses)
- [REST API endpoints for check runs](https://docs.github.com/en/rest/checks/runs)
- [Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- Local `gh` 2.98.0: `gh --version`, `gh auth status`, `gh repo create --help`, `gh repo delete --help`, `gh ruleset --help`
