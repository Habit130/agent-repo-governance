# AC-52: headless resume and run-only skill sources

Research and probes for AC-52-v1, round 1. Sources read on 2026-10-31 UTC;
local versions: Claude Code 2.1.314 and OpenCode v2.2.2. The research helper's
returned date used the session's displayed 2026-10-30; the execution clock and
the reads in this record are 2026-10-31 UTC.

## Primary sources

- Claude Code [CLI reference](https://code.claude.com/docs/en/cli-reference)
  and [headless guide](https://code.claude.com/docs/en/headless): `-p --resume
  <session-id>` resumes a particular conversation. `--session-id` binds the
  first turn. `--fork-session` would create another conversation and is omitted.
  The installed `claude --help` confirms these flags.
- Claude Code [plugin creation](https://code.claude.com/docs/en/plugins/create),
  [loading](https://code.claude.com/docs/en/plugins/loading#name-conflicts) and
  [skills](https://code.claude.com/docs/en/skills): `--plugin-dir` loads a
  session-only plugin, whose skill is invoked as `/plugin:skill`. A skill with
  `disable-model-invocation: true` remains user-invocable. This does not replace
  the ordinary `/skill` ID: the namespaced invocation selects the run's copy.
- The same CLI help documents `--tools` (available built-in tools),
  `--allowedTools` (approval, not a tool whitelist), `--strict-mcp-config` and
  `--mcp-config`. The probe exposes only Skill and Read, allows Skill, and
  selects an empty MCP configuration. It changes no user settings.
- `--bare` in 2.1.314 is an opt-in flag, not the print-mode default. Its help
  says it skips OAuth/keychain reads; it is not used for subscription probes.
- OpenCode V2 [CLI commands](https://opencode.ai/v2/docs/cli/commands#run):
  `opencode run --session <id>` continues that session, or creates it when
  absent. The probe therefore checks the returned ID and a marker known only
  to the first turn. `--fork` and `--continue` are not used.
- OpenCode V2 [skills](https://opencode.ai/v2/docs/skills): explicit `skills`
  array entries register after discovered sources; later registrations of the
  same path-derived ID win. `@govern-repository` explicitly loads that ID even
  with `disable-model-invocation: true`. This is an actual same-ID override,
  unlike Claude Code's namespaced selection.
- OpenCode V2 [configuration](https://opencode.ai/v2/docs/config) and
  [permissions](https://opencode.ai/v2/docs/permissions): V2 uses a `skills`
  array, ordered permissions and a separate `external_directory` check. A
  refusal is a stop, not permission to add an allow rule or restructure a call.
- OpenCode v2.2.2 source, tag commit
  `098aa7fd6e02b03d6fc410f0b052038c7d4c5e81`:
  [server-process.ts](https://github.com/anomalyco/opencode/blob/v2.2.2/packages/cli/src/server-process.ts#L122-L134)
  maps `OPENCODE_CONFIG_CONTENT` into inline configuration;
  [config.ts](https://github.com/anomalyco/opencode/blob/v2.2.2/packages/core/src/config.ts#L255-L316)
  parses it after ordinary project configuration and before managed settings;
  [skill.ts](https://github.com/anomalyco/opencode/blob/v2.2.2/packages/core/src/config/plugin/skill.ts#L80-L157)
  registers explicit sources last and replaces by ID;
  [standalone.ts](https://github.com/anomalyco/opencode/blob/v2.2.2/packages/cli/src/services/standalone.ts#L17-L30)
  inherits the launch environment for the private server. `opencode run --help`
  confirms `--standalone`, `--session` and `--format json` locally.

## Probe boundary

`tests/scenarios/headless_probe.py` creates a temporary git repository and a
run-only `govern-repository` skill. Its first turn asks a plain Chinese question
and keeps a randomly generated marker private. Its next turn must return the
marker from the same session. No repository or GitHub writes are requested of
the model. Stand-in `gh` is first on PATH; token environment variables are
removed and real `gh` has an empty configuration. Parent harness markers are
cleared before launching the inner harness. The real home supplies harness
login, never fixture machine facts. Harness runs are sequential.

### Observed: Claude Code

- Invocation: `python3 tests/scenarios/headless_probe.py claude`.
- First turn: `/ac52-probe:govern-repository` with `--plugin-dir`; result was
  `habit，是否继续 resume probe？`.
- Second turn: `claude -p --resume` with the same plugin and recorded answer;
  returned exactly the private marker. Both results named session
  `a8e73693-c08f-48e6-8168-dfae65b911cf`, exited 0, reported no error or
  permission denial, and reported zero subagents. No model was pinned.
- This proves the run-only source's explicit invocation and same-session resume,
  not the production procedure or a complete Seam B run.

### OpenCode

The first separate probe used an explicit `skills` source in run-only inline
config and the private server, preserving the configured model and existing
permissions. Both turns exited 0 in `ses_0a0c755ddca747f088ecf62a10`; the first
loaded the scratch skill through the Skill tool, and the second returned the
private marker. There was no refused operation and no GitHub call.

However, the first turn's unsolicited glob searched the delivery checkout,
not the temporary repository. A check of the captured tool outputs failed
`FAIL probe isolation: a tool searched the delivery repository instead of the
scratch repository`. This result proves resume and skill selection only; it
does not prove isolated scenario operation.

The source explains the discrepancy:
[run/run.ts](https://github.com/anomalyco/opencode/blob/v2.2.2/packages/cli/src/run/run.ts#L71-L74)
selects `process.env.PWD` before `process.cwd()` and changes directory to it.
Python's `subprocess.run(cwd=...)` does not rewrite inherited `PWD`. The probe
now synchronizes both at the child-process boundary, and asks the first turn to
name its system-context working directory as well as its confirmation. That
assertion independently catches a wrong location without supplying its answer
in the skill text. This is a runner correction, not a permission workaround.

### Stop: OpenCode does not load the skill in the isolated repository

After synchronizing `PWD`, a fresh run in session
`ses_b7f69ed477c04456893bff33f9` searched the empty fixture checkout (no files
found), then returned, verbatim:

> habit，当前没有收到 `@govern-repository` 的具体指令，也未在工作区找到对应文件。请提供该命令的内容，或说明希望对仓库执行什么治理任务。

The harness exited 0 but the probe exited 1, correctly refusing to count that
response as a loaded skill or a confirmation. No second turn was sent. No
permission refusal or GitHub call was observed. The earlier OpenCode success
in the wrong directory cannot establish the contract's isolated-scenario path.

The exact cause of the skill-loading failure is **unresolved**. The V2 docs
promise explicit `@skill-id` loading, but the v2.2.2
[noninteractive submission](https://github.com/anomalyco/opencode/blob/v2.2.2/packages/cli/src/run/noninteractive.ts)
sends the message through `session.prompt` as text. Whether server-side mention
expansion or skill registration explains this failure has not been established.
No alternative invocation, permission change or further model run was tried
after this failure. This meets the handoff's stop for inability to establish the
PR skill source in the required harness. Product implementation has not begun;
CRIT-9/10 red tests and Seam B remain unrun.

The probe's later directory assertion has not been rerun under Claude Code;
the successful original Claude Code result above remains narrower evidence.

## AC-52-v2 diagnostic: provider limit before any model turn

Ran once on 2026-11-02 under OpenCode v2.2.5, at probe commit `a1ff88d`. The handoff
allowed one fresh session and at most two submissions. Source for the changes below is
OpenCode v2.2.5
[noninteractive.ts](https://github.com/anomalyco/opencode/blob/v2.2.5/packages/cli/src/run/noninteractive.ts)
and [skill tool](https://github.com/anomalyco/opencode/blob/v2.2.5/packages/core/src/tool/plugin/skill.ts).

The probe now asks for the `skill` tool by ID and reports one Pass or Fail per assertion:
exit code, session ID, reply after the last tool call, error events, permission refusal,
tool outcomes, location, tool input, selected source and stand-in calls. A noninteractive
refusal is an `auto-rejecting` warning plus a failed tool, not a `permission` event, so
both are inspected. The evidence directory is resolved because OpenCode reports canonical
`/private/...` paths on macOS. These assertions were checked against synthetic events and
the shapes in the earlier run logs, without a model.

Session `ses_ad5c93ec2eac46b5bb2f078aa0` exited 1 on the first submission. Its only events
were `step_start` and an `error` of type `provider.free-limit`, status 429, "Free usage
limit reached", `retryAfterMs` 85325000 (about 23.7 hours). stderr was empty. No text, tool
call, permission request or stand-in call occurred, so no second submission was sent.

This is a provider failure, not a skill-loading result. The model produced no turn, so the
explicit `skill` tool request is **untested**: the run neither confirms nor refutes the
hypothesis that CLI text lacks structured skill loading, and it says nothing about
registration of the scratch source or same-session recall.

Later read-only checks found the cause of the limit. The session export names model
`opencode/pulse-alpha-free`. The user configuration sets `small_model` but no `model`, and
the probe passes no `--model`, so
[Model.default](https://github.com/anomalyco/opencode/blob/v2.2.5/packages/core/src/model.ts#L300-L305)
falls back to the first available text model. The interface's recent-model list is not
consulted by that path. Paid providers are connected, so sign-in is not the cause.

## AC-52-v3 diagnostic: explicit skill-tool load on a pinned model

Ran once on 2026-11-03 UTC under OpenCode v2.2.5, at probe commit `e247082`. The handoff
allowed one fresh session and at most two submissions, each with `--model xai/grok-4.7`.
The probe now lists models with `opencode models --standalone` in its own clean environment
before any submission, and stops unless the exact line `xai/grok-4.7` appears. It reads each
turn's model from `opencode session export`, because `--format json` events carry none.

The precheck passed, and session `ses_4d185999469d4b76af4db49f6f` passed every assertion.

- **First submission:** the model called `skill` once with ID `govern-repository`; the tool
  completed and reported the run-only source's directory. The reply after the tool call was
  exactly the Chinese confirmation, followed by the temporary repository's absolute path.
- **Second submission:** `继续 resume probe` in the same session returned exactly the private
  marker, which was not in the prompt, with no tool call and so no skill reload.
- **Model:** all three stored assistant messages ran on provider `xai`, model `grok-4.7`. The
  store also records `variant: default`, though the flag named no variant.
- **Failure signals:** exit 0 on both turns, stderr empty, no error event, no stored message
  error, no `auto-rejecting` warning, and no stand-in call log.

This is the first real v2.2.5 skill-tool event, and `a1ff88d`'s assertions read its shape
without change. The selected directory is `state.metadata.metadata.directory`.

**Establishes:** on this model, an explicit request for the `skill` tool by ID loads a run-only
skill that has `disable-model-invocation: true`, in the right directory, and the same session
recalls it on resume. So the scratch source registers and the permission check allows the load.

**Does not establish:** that a bare skill mention or the normal invocation works in a CLI run,
that other models or any unpinned run behave the same, or that one run is repeatable. The
hypothesis that CLI text lacks structured skill loading was not tested, because this run sent
no bare mention. CRIT-1's normal invocation evidence, CRIT-5/7/8 and Seam B stay unmet.
