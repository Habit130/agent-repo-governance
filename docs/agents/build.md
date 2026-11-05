# Build and Verification

The executable paths and the non-obvious ordering that delivery sessions need. Human-facing
setup stays in the README. What a PR needs by what it changes: `AGENTS.md`, Verification by
change.

## Required order

Run these in order, and every one must pass. Steps 2 to 6 are CI's steps in its order; step
7 prints the exact comparison that the `materialized-version` suite asserts in CI.

| Step | Command | Evidence / notes |
| --- | --- | --- |
| 1. Whitespace | `git diff --check origin/main...HEAD` | Also `git diff --check` before committing. |
| 2. Stored form | `python3 tests/run.py stored-form` | One PASS line, or one FAIL line per stored path that could load or fails to decode. |
| 3. Release check | `python3 tests/run.py release-check --base "$(git merge-base origin/main HEAD)" --head HEAD` | One PASS or FAIL line per rule, then INFO lines for new and changed fixtures. Use the merge-base: a newer `origin/main` would read its own new fixtures as removed. |
| 4. Linux suites | `python3 tests/run.py suites --job linux` | unittest's verbose output, ending `OK`. |
| 5. Python 3.9 and bash 3.2 | `/usr/bin/python3 tests/run.py py39` | Fails unless the interpreter is 3.9; parses every script as 3.9 and runs `/bin/bash -n` on every shell entry. |
| 6. Every suite under 3.9 | `/usr/bin/python3 tests/run.py suites --all` | The 3.9 compatibility run of every suite. |
| 7. Exact comparison | `python3 tests/run.py exact-comparison` | Renders version 1 into the tally sample repository and prints exact comparison's JSON; `differences` must be empty. |
| 8. Committed whitespace | `git show --format= --check HEAD` | After committing. |
| 9. Scope | `git diff --stat origin/main...HEAD` and `git status --short` | Inspect against the frozen contract. |

`tests/run.py suites <name>...` runs single suites while working.

## Suites

`SUITES` in `tests/run.py` names each suite, its module under `tests/suites/` and its job.
Later deliveries add theirs there, under the job #44 §11 names.

| Suite | Covers | Job |
| --- | --- | --- |
| `stored-form` | Stored form's round trip, materializing, and the stored-form check failing on planted paths | linux |
| `store` | Version 1's manifest, the change-note parser fixtures, released and installed versions | linux |
| `render` | Rendering's placeholders, confirmed values and unreleased versions, into a temporary directory and a worktree | linux |
| `compare` | Exact comparison naming each difference | linux |
| `materialized-version` | Version 1 from the real store, rendered into tally and compared exactly, and its record parsed; each fixed file's notice, the Markdown form an HTML comment on line 1 (`MARKDOWN_NOTICE`); the mixed files' markers, well formed at version 1, with their notice as the first line inside them (`MIXED_NOTICE`) and their skeleton text after the end marker left uncompared; `AGENTS.md`'s sections in order and its bytes within `AGENTS_BUDGET`; `.cursor/BUGBOT.md` equal to its notice, a blank line and `AGENTS.md`'s Code Review Rules section, heading included; every path pointer in a Markdown file version 1 writes naming a file version 1 writes, with what stays outside in `UNROUTED`; no root `CLAUDE.md`, `AGENTS.override.md` or `.codex/` written; the `build.md` skeleton written with no notice and left uncompared; the role files' skill lists against #41 §13 and the relied-on list; the PR template's comment lines, continuation lines included, none starting with `Risk:` or `Reverts:`, and its one `Risk:` line, once filled, read by both parsers; `triage-labels.md` against the manifest's labels; Merge watch's workflow and script with the notice, their mode and exact comparison; planted mismatches failing; later templates' seam-3 checks join it | linux |
| `record` | Version 1's record template, rendered with sample confirmed values and read back; confirmed values the parser would refuse, refused at rendering | linux |
| `parser-fixtures` | Every registered parser against every shared parser fixture, one test per parser and fixture | linux |
| `gate` | Seam 1: every case in `tests/fixtures/gate/cases/` built into git and judged; the failure lines, the pattern rules, the rendered workflow, a sibling script importing the parser, and the entry fetching the head and posting through the stand-in | linux |
| `merge-watch` | Seam 2: every case in `tests/fixtures/merge-watch/cases/` judged on its recorded event and GitHub answers, its records exact and compared field by field with `issue-tracker.md`'s format; the gate's parser imported from beside the script; the rendered workflow's triggers, `workflows` glob and six permissions, and it not being a required check; the entry reading and posting through the stand-in | linux |
| `release-check` | Seam E: every fixture in `tests/fixtures/release-check/` | linux |
| `skill-copies` | Refreshing, verifying and listing changes against a local stand-in upstream, a planted one-byte change failing; the copies check on the real tree and on planted mismatches; both Codex key detectors on every shape in `tests/fixtures/machine/codex-policy-shapes.json`, one test per shape and detector | linux |
| `standins` | The stand-in GitHub and the Codex stand-in, a stray call included | macos |
| `machine-install` | Seam C: every install fixture of #44's Testing Decisions, the machine rules, forward-only refusals and the ready command against a local origin | macos |
| `machine-check` | Seam C: each machine-check item failing on its own with the home unchanged, Codex absent, personal skills' Codex problems only reported, and the Codex key detector's shapes | macos |
| `machine-list` | Seam C: the list's lines, header, private mark, miss count, sandbox skip and account refusal | macos |
| `machine-wizard` | Seam C: the account wizard in a throwaway home against the stand-in GitHub, whose logins take effect there; the walkthrough's steps, calls and last line, the machine check's identity item on its end state, a rerun changing nothing, each stop and the next run picking up, planted credential shapes in every answer and file it reads, and `machine/wizard.sh` from a fresh clone of a local origin | macos |
| `owner` | Seam D: every case in `tests/fixtures/owner/cases/` run through the rendered owner script against the stand-in, its writes, bodies and report lines exact; the token refusal, the embedded program parsed as 3.9, and the owner-script command against a local origin | macos |
| `live-runner` | The live-check runner offline: the probe registry, the owner probes reading Seam D's reports and the stand-in's agent view, the gate probes judging recorded setups and rejections, Merge watch's probes against a small sandbox of their own with the real script judging their Merge summary, the result comment, and habit's commands under `/bin/bash`; the real gate attempts command with test-local git and gh stand-ins, stopping at each possible success, carrying on after preparation failures, and its captured stopped and healthy output through `gate-rulesets`; the cut's `reset` and `end-to-end` against a local bare sandbox and the stand-in, the plugin's own `mode` reading Initialize, each refusal leaving nothing behind; the reset staging exactly the seed's tree, the plugin holding the committed generator under `cut`, habit's start line under `/bin/bash` with every scenario setting the generator reads unset | macos |
| `generator-core` | Seam A: every case in `tests/fixtures/generator/cases/` through the one entry, against the stand-in GitHub, synthetic stores and installed fixture homes, its exit codes and facts as `generator_support.py`'s docstring defines them; in every case no stand-in call writes but the invitation's acceptance and the worktree and home are unchanged; each probed harness's names judged as ADR 0013 requires; drift's target against `tests/target_state.py`, and the agent account's recorded view of a Gate in place; the handover rule, the skill files' four conditions and the identity hash, and the scenario settings | macos |
| `scenario-runner` | Seam B's runner with no model: the stand-in accepting a run's writes, the issue's block parsed, each assertion on planted evidence, and the three-run rule | macos |

## Scenarios

`python3 tests/scenarios/runner.py <scenario> --harness claude|opencode [--runs N] [--out DIR]`
runs a scenario in a logged-in harness on habit's Mac, one run at a time. Its docstring gives
the fixture shape. The scenarios are `initialize-planted`, `upgrade` and `repair-files` under
`tests/scenarios/fixtures/`: each Claude Code scenario runs three times, and the OpenCode
smoke scenario is one run of `initialize-planted`. The Builder, until Initialize Execution,
runs them and posts the results naming the head. Each OpenCode submission passes exactly
`--model xai/grok-4.7`, and `opencode models --standalone` must list it first. Each Claude
Code submission passes `--model claude-sonnet-5-5 --effort medium`, habit's choice, and a run
fails unless every main-thread message ran on it and no message ran on Opus. A run's
permissions are its own: `--tools` and `--allowedTools` in Claude Code, `permission` in the
run's `OPENCODE_CONFIG_CONTENT` in OpenCode, never `--auto`. A failed resume records #40's
fallback and stops. `tests/scenarios/headless_probe.py` holds the resume and interface-entry
probes, and the runner reuses its clean environment. CI runs no model.

## CI

`.github/workflows/ci.yml` runs on every PR, with no path filter, in two jobs whose names stay
stable: they become required checks when habit confirms them at this repository's
Initialize. Until then no required check names exist on the default branch, and Acceptance
or the pre-merge check confirms both jobs are green on the head.

- **`linux`**, on `ubuntu-24.04` with its `python3`: steps 2 to 4. The checkout is the PR's
  merge commit, so the release check compares `HEAD^1` with `HEAD`.
- **`macos`**, on `macos-15`: steps 5 and 6 with `/usr/bin/python3`, which is Python 3.9.6
  there, beside `/bin/bash` 3.2.57.
- Both use no model, credential, network, GitHub writes, third-party actions or package
  installs. The only token is the checkout's read-only `GITHUB_TOKEN`, not kept in the
  checkout. Standard runners are free on a public repository, per GitHub's
  [runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

## The generator's command line

`generator/govern-repository/scripts/govern.py` is the generator's one entry. Its
subcommands (`store`, `change-note`, `render`, `compare`, `materialize`, `owner-command`,
`handover`, `identity`, `mend-markers`, and the mechanical core's `preconditions`, `mode`, `inspect` and `accept-invitation`) print JSON
and exit 0 on good facts; 1 when exact comparison finds differences, a precondition fails or
the mode is stop; and 2 on a refusal, with the reason under `error`.

- **Damaged markers** are mended before rendering: `mend-markers --worktree <path>` gives each
  fixed part's file whose markers `mode` reports damaged one well-formed block at the record's
  version, so `render` can fill it. Intact governance text gets its markers back; edited text
  is rebuilt, keeping the text before the begin marker and the repository's own part from
  the line the template puts after its end marker, or from the one end marker left. It lists
  each file's `repair` and the non-version lines it `dropped`, and refuses, writing nothing,
  when the repository's own text can't be told apart: with the begin marker gone, text above
  the version's first line, or with the end marker gone, neither it nor the line after it left.
  A path through a symlinked directory is refused too. It is tested in `generator-core`.

- **Relied-on skill names** in a version manifest must be a list of unique lowercase,
  hyphenated strings. Each entry's type and spelling are checked before deduplicating;
  objects and lists receive the same JSON refusal as other malformed entries, with no
  traceback or store writes. `tests/fixtures/stores/relied-on-skills.json` records the
  S-1 miss and the rejected and accepted CLI inputs; the `store` suite also checks stderr
  and snapshots every fixture-store file's bytes and mode.
- **Exact comparison in a governed worktree** is one command:
  `python3 generator/govern-repository/scripts/govern.py compare --worktree <path>`. It reads
  the repository and default branch from the worktree's `origin`, and compares the installed
  version unless `--version` names another.
- **Literal default branches** use Git's rules, not a punctuation allowlist. Both render
  and compare run `git check-ref-format refs/heads/<name>` as an argument vector without
  a shell, plus Git's branch-only leading-`-` and `HEAD` restrictions. They never use
  `--branch`, which expands `@{-n}` using checkout history, or normalize the spelling.
  A name containing the exact substring `${{` is explicitly unsupported: both commands
  return exit 2 and a JSON `error` identifying the unsupported Actions-expression marker
  before writes. This is the chosen support boundary, not a claim of platform
  impossibility; no expression-based encoding (including a static string expression) is
  generated. Dollar signs and braces without that substring remain supported.
- **Branch filter encoding has two layers.** In the Gate and Merge watch workflow templates,
  a bare `@@default_branch@@` on its own six-space-indented list-item line represents one
  complete filter scalar. Actions `+` and leading `!` are escaped with backslashes, then
  JSON-compatible double quoting encodes the YAML scalar (quotes, backslashes and YAML
  line breaks included). For example `release+stable` becomes YAML `"release\\+stable"`,
  whose decoded filter is `release\+stable`. Gate's one filter and Merge watch's two
  filters use the same path in rendering and comparison. Prose uses retain the unescaped
  literal name; ordinary `main` retains its previous rendered bytes. Substitution is a
  single pass: inserted values never become template source. The existing three token
  names and unknown/leftover-token refusal remain unchanged, and render plans every file
  before writing any of them.
  `tests/fixtures/stores/branch-names.json` records S-2's miss, hand-written expected
  filters and nearby nonmatches, invalid Git names, unsupported marker inputs and token
  safeguards. The `render` suite exercises both real CLIs against synthetic and real v1
  stores, plants mismatches at all three filter sites, and keeps complete no-write
  snapshots including `.git` and its objects.
  Primary sources read 2026-11-02: [Git naming and shorthand rules](https://git-scm.com/docs/git-check-ref-format#_description),
  [Git's branch-only checks](https://github.com/git/git/blob/master/refs.c) (`check_branch_ref`),
  [Actions branch filters and filter grammar](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#filter-pattern-cheat-sheet),
  [YAML quoted scalar escapes](https://yaml.org/spec/1.2.2/#73-flow-scalar-styles).
  Git forbids the filter operators `*`, `?`, `[` and backslash in literal branch names;
  `+` repeats the preceding character, and leading `!` negates a filter. YAML quoting
  alone does not escape those filter operators.
- **Unreleased versions** are rendered or compared only with `--allow-unreleased`, which a
  test or live-check runner passes for its own run. The generator's procedure never passes
  it. A scenario needs none, since its synthetic store carries a change note.
- **Scenario settings.** Three environment settings only the scenario runner sets:
  `GOVERN_SCENARIO_STORE` and `GOVERN_SCENARIO_HOME` replace the `--store` and `--home`
  defaults, and `GOVERN_SCENARIO_REPOSITORY` names the repository in place of a local
  `origin`, which `git remote get-url` can't show as GitHub. Absent, the entry behaves as
  without them, and the skill text names none of them, so no skill file changes for a run.
- **Exact comparison** checks content and mode of every fixed file, every fixed part between
  its markers, and the record up to its one top-level `confirmed:` key, after which only
  indented values, blank lines and comments may follow. It leaves the confirmed values,
  which are the repository's own, and skeletons, which become repository-owned content.
- **Rendering a fixed part** writes the whole template when the target is absent, replaces
  the one well-formed marker block when there is one, and refuses anything else. A skeleton
  is written only when its target is absent. `mode` reports damaged markers; restoring or
  rebuilding them is the write phase's (#52).
- **One template per target path.** A mixed file's template holds its fixed part between the
  markers and its skeleton text after them. The record template ends at its `confirmed:`
  key, and rendering writes the confirmed values below it. Rendering refuses confirmed
  values, or a template, whose record wouldn't parse.
- **Writes stay inside the destination.** Rendering and materializing refuse a target whose
  parent is a symlink or not a directory before writing anything.
- **The mechanical core** (#44 §6.1 to §6.3) runs before habit's confirmation and writes
  nothing, to GitHub or to the checkout, except `accept-invitation`. Each takes `--worktree`
  (default: the current directory); `preconditions` and `inspect` take `--home` (default: ~),
  `preconditions` and `mode` take `--store` (default: the store beside the entry). The
  modules' docstrings define the facts: `govlib/preconditions.py`, `drift.py`,
  `inspection.py`, `workflows.py`.
  - **The harness comes first** in all four, and a refusal prints the harness facts under
    `harness` with exit 2. `govlib/harness.py` passes only when `CLAUDECODE` (Claude Code)
    or `OPENCODE` (OpenCode) is set, not both, and no `CODEX_…` or `DSH_…` variable is, the
    homes `CODEX_HOME`, `DSH_HOME` and `DSH_AGENTS_HOME` aside. Each harness's shell was
    probed by name on 2026-10-29, and the names are recorded in
    `tests/fixtures/generator/harness-probes.json` with each harness's version.
  - **`preconditions`** reports every §6.1 item together with habit's checklist. It runs the
    installed machine check, `~/.agents/governance/machine/scripts/machine.py check --home`,
    and reads the managed skills from `~/.agents/governance/installed.json`. On a private
    repository its `private` item takes #17's read through `govlib/rules.py` (#53): the
    rulesets list at Initialize, the default branch's rules otherwise, after-merge included.
    It passes only on rulesets available or every Gate and Merge rule type listed; the Pro
    refusal, a missing type and any case it can't decide fail, each with the Chinese lines
    habit hears and the English line the issue records under `rules_in_effect`.
  - **`mode`** gives the mode and, at Upgrade and Repair, drift against the record's version:
    exact comparison with GitHub's default branch, the markers with whether the generator's
    text between them is intact, and GitHub state against `govlib/target.py`, which Seam A
    checks against `tests/target_state.py`.
  - **Every GitHub read in `mode` gets one retry** (`github.Retried`, CRIT-10). One that stays
    failed sits under `drift.github.unreadable`, and an inactive ruleset the agent read but
    can't place sits under `unplaced`; either keeps the outcome from reading as no drift.
  - **`handover`** takes a saved `mode` report, `--mode-facts <file>`, and
    `--required-checks-changed` when habit's answer changed them. It prints `owner_command`
    and the Chinese lines habit hears with the command; `mode` reports the same rule under
    `drift.handover` before the answer. It is the only place that rule lives, and
    `tests/fixtures/generator/handover.json` holds its table.
  - **`accept-invitation`** accepts the agent account's pending invitation to the
    repository, the one write before habit's answer.
  - **No credential value is printed** (#41 §10). `inspect` names each credential shape it
    finds by type and location, and the entry passes every JSON it prints through
    `govlib/secrets.py`'s `redact`, which replaces each shape with its type, so a command's
    text, a title or an error carries none. A private key is redacted from its header to its end
    marker, or to the text's end without one, and in a document's shell block its lines are
    never read as commands.
- **GitHub's facts the core relies on**, as the agent account, a write collaborator, read on
  2026-10-29 from Habit130/governance-sandbox and Habit130/agent-repo-governance, and from
  GitHub's REST reference pages for rules, branches and invitations the same day:
  - `GET repos/{r}` gives `permissions` and the five merge settings; `security_and_analysis`
    is null, and `actions/permissions` and `actions/permissions/workflow` answer 403. That is
    the blind spot the owner script checks.
  - `GET repos/{r}/rulesets/{id}` returns `bypass_actors` as null (the reference: "only
    returned if the user making the API request has write access to the ruleset"), and adds
    `pull_request` parameters the owner script never sends.
  - `GET repos/{r}/rules/branches/{b}` lists each active rule on the branch with its
    `ruleset_id`; rules of `evaluate` or `disabled` rulesets aren't returned, so whether such
    a ruleset applies is reported as unknown unless its patterns name the branch outright.
  - `GET repos/{r}/branches/{b}` returns `protection.enabled`, undocumented: `true` on
    python/cpython's `main`, which has classic protection and no ruleset, and `false` on the
    two repositories above, protected by rulesets only. It is the classic-protection fact;
    `.../protection` needs admin.
  - On a private repository, #17's revision (phase 1 on Free, phase 2 on Pro, and its lapse
    simulation, run 2026-10-23 and 2026-10-26): `GET repos/{r}/rulesets` and
    `GET repos/{r}/rules/branches/{b}` answer 403 "Upgrade to GitHub Pro or make this
    repository public to enable this feature." when the rules can't bind, and 200 when they
    can, the rules read listing `deletion`, `non_fast_forward`, `pull_request`,
    `required_status_checks` and `update`; the agent's push, force-push and merge were
    accepted in the first case and rejected in the second. Seam A's stand-in answers both
    reads that way under `rulesets_forbidden`.
  - `GET user/repository_invitations` lists the agent's open invitations;
    `PATCH user/repository_invitations/{id}` accepts one and answers 204.
- **The change note** opens with `urgency: urgent` or `urgency: when convenient`, then
  `must-act: yes` or `must-act: no`, then a blank line and the plain-Chinese body. Its parser
  and fixtures: `govlib/store.py` and `tests/fixtures/change-notes/`.

## The machine area

`machine/scripts/machine.py` is the one entry for the install, the machine check, the
governed-repository list and the account wizard (#44 §8, §9). Its subcommands, `install
--source <tree> --home <dir>`, `check`, `list` and `wizard`, print Chinese reports and exit 0
when nothing failed, 1 when an item or line failed or the wizard stopped at a step, and 2 on a
refusal that wrote nothing. `machinelib/__init__.py` names the layout; `install.py`'s and
`wizard.py`'s docstrings give the steps.

- **The ready command** is the one line in `machine/ready.sh`. habit runs it in Claude Code
  with the `!` prefix after a merge that changes the machine; agents never run it, the
  internal entry or the check against habit's home:

  ```text
  /bin/bash -c 'set -eu; d="$(mktemp -d)"; trap "rm -rf \"\$d\"" EXIT; git clone --quiet --filter=blob:none https://github.com/Habit130/agent-repo-governance.git "$d/src"; /usr/bin/python3 "$d/src/machine/scripts/machine.py" install --source "$d/src" --home "$HOME"'
  ```

  The clone keeps history, since forward-only needs the installed commit to be an ancestor.
- **The account wizard** runs once on a new machine, before the first install, from the one
  line in `machine/wizard.sh`, which README.md and this file quote byte for byte. habit runs
  it in a terminal, never with Claude Code's `!`, because its logins need the terminal; agents
  never run it, `gh auth` commands or `ghm` against a real home:

  ```text
  /bin/bash -c 'set -eu; d="$(mktemp -d)"; trap "rm -rf \"\$d\"" EXIT; git clone --quiet --depth 1 https://github.com/Habit130/agent-repo-governance.git "$d/src"; /usr/bin/python3 "$d/src/machine/scripts/machine.py" wizard'
  ```

  It reads each login with `gh auth status --hostname github.com --active --json hosts`. From
  gh 2.98.0's source (`pkg/cmd/auth/status/status.go`, `internal/config/config.go`, read
  2026-11-04): with `--json` it always exits 0, no login prints `{"hosts":{}}`, the token is
  dropped from the output, a keychain token's `tokenSource` is `keyring`, a plain-text one's
  the `hosts.yml` path, and `scopes` is the `X-OAuth-Scopes` header, comma-separated.
  `gh auth login --web` stays interactive on a terminal and may ask whether to set up git's
  credential; either answer is fine, since the wizard runs `gh auth setup-git` itself. Its
   credential step conservatively models Git's `credential.c` and `urlmatch.c` (read
   2026-11-05): system and global helpers in config order; only an unconditional or exact
   `https://github.com[/]` / `github.com[/]` match may apply an empty reset. Only canonical
   literal lowercase DNS HTTPS hosts other than github.com are certainly excluded. Other
   URL spellings (including username/port qualifiers, parse failures, patterns, paths and
   normalization such as a trailing host dot) add uncertainty, never clear earlier helpers
   or prove gh's route; a later
   certain reset clears that uncertainty too. Residual uncertainty stops the step in Chinese.
   `fill` stops at the first helper that answers and `approve` stores to every one, so the
   step passes only with exactly gh's helper and no uncertainty (AC-48's Acceptance A1).
   Isolated real-Git regressions cover the false resets and no-op reruns. It reads outside any repository, so a
  conditional include (`includeIf`) stays unseen; the step's line says so when one exists. The
  `machine-wizard` suite never runs `ghm` or any `gh` inside a login shell: macOS's login
  profile reorders PATH, so a real gh there could reach the keychain.
- **Run on their own** from the installed copy: `/usr/bin/python3
  ~/.agents/governance/machine/scripts/machine.py check` and `... list`. The installed state
  is `~/.agents/governance/installed.json`; there the entry imports `govlib` from the
  installed generator.
- **Codex's real behaviour**, recorded under `tests/fixtures/machine/` from the ChatGPT app's
  CLI: `codex execpolicy check --rules <file> <words...>` takes no `--` (it would become a
  command word), exits 0 whatever the decision, and omits `decision` when no rule matches.
  `codex debug prompt-input` prints no budget warning; it shortens descriptions and drops
  entries silently, in name order, so the check compares the listed names with the home's skills.
- **Personal skills** (#44 §8, §9, changed by #70): a machine skill is a directory in
  `~/.agents/skills` named in the machine skill set; every other skill there and every skill
  in `~/.codex/skills` is personal. The install never writes inside a personal skill, nor
  through a link inside one, and adds no Codex user-only key anywhere: machine skills carry
  theirs in this repository. The check fails a machine skill's missing key, omitted entry or
  shortened description, and reports a personal skill's as a `说明` line that never fails. A
  machine skill whose key reads `unclear` is still looked for in Codex's list, so its omission
  fails; a personal one's is left out.
- **Codex's user-only key** is read by its effective value in one detector,
  `machinelib.skills.codex_policy`, which the copies share. Only `false` is user-only. Codex
  ignores an `agents/openai.yaml` that real YAML refuses (repeated keys, tabs, open quotes, a
  plain value continued after a comment or by a line holding `: `), or where a field it
  types, such as `interface`, `dependencies.tools` or a `policy` field, holds the wrong type.
  So a shape the detector can't read safely is `unclear`, flow collections, escapes and a
  value's next line that isn't plain text included, which fails a machine skill and never
  reads as user-only. `tests/fixtures/machine/codex-policy-shapes.json` is the shared shape
  set; a new shape the detector reads as `false` joins it and its real recording,
  `codex-prompt-input-policy-shapes.json`, re-recorded with the shape's skill.
  A block scalar's first nonblank content line fixes its content indentation for the
  whole scalar: deeper lines may return to it, but a line below it (even above the
  key's indentation) is `unclear`. Leading-blank, tab and hidden-policy refusals remain.
  AC-75-v1 fixes AC-71's Acceptance A1 miss with `block-indent-increase-and-return`
  (`false`, hidden) and `block-below-initial-indent` (`unclear`, listed). The generated
  `PolicyShapes` tests exercise both consumers and copies' byte-preserving acceptance
  or refusal. The 2026-11-02 recording uses the installed ChatGPT CLI,
  `codex-cli 0.166.0-alpha.5.1`, invoked as
  `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex debug prompt-input x`
  through `Home.run_codex`: synthetic HOME, XDG configuration/state/data/cache and
  TMPDIR, plus disposable CODEX_HOME and cwd, all inside scratch space. No model,
  authentication or network call is needed. All 130 shared shapes are present as
  inputs; `no-policy` is the listable control, and no old shape changes visibility.
  The recording normalizes only home, disposable CODEX_HOME and cwd paths as above.
- **Seam C suites** build the source tree from this checkout's `machine/` and generator with
  synthetic copies (`tests/suites/machine_support.py`), so the real recordings stay true
  when the copies change. They pass the Codex stand-in or a missing path, never the app,
  and put a `ghm` tripwire first on the path. Re-record a fixture home's Codex output with
  the real CLI when its skills change, replacing the scratch home's path with
  `/fixture-home`.

## Skill copies

`skill-copies/` holds the third-party skill copies (#44 §10, ADR 0020): upstream's `LICENSE`,
`provenance.json`, one whole upstream skill directory per copy under `skills/<name>/`, and the
scripts under `scripts/`. `scripts/copylib.py`'s docstring defines the manifest and the one
allowed change, the Codex user-only key appended to a user-invoked skill whose
`agents/openai.yaml` has no `policy` key. The copies read the key with the machine's detector
(The machine area, above).

- **The copies check**, `python3 tests/run.py copies`, fails unless the copies under
  `skills/`, the manifest's entries and the highest version's `relied_on_skills`
  (`govern-repository` aside) name the same skills, all from one upstream commit, and every
  user-invoked copy reads as user-only. The `skill-copies` suite runs it on the real tree in
  the `linux` job.
- **An update PR** refreshes every copy from one upstream commit with
  `python3 skill-copies/scripts/refresh.py --commit <sha>`, which replaces `skills/`,
  `LICENSE` and the manifest and refuses, writing nothing, when a relied-on skill is missing,
  a user-invoked one has no `agents/openai.yaml` or a policy that one appended block can't
  make user-only (one that isn't `false`, or `unclear`), or an upstream path fails stored form.
- **Verification**: `python3 skill-copies/scripts/verify.py` fetches each recorded commit and
  prints a PASS or FAIL line per copy and for the license, then each added Codex key. CI has
  no network, so Execution runs it on the PR head and Acceptance reruns it. For a planted
  change, pass `--copies` a modified copy of `skill-copies/` in a temporary directory.
- **The change list**: `python3 skill-copies/scripts/changes.py --to <newer sha>` prints, in
  plain Chinese, what changed per copy since the recorded commit, quoting up to ten changed
  lines per file, for the Merge summary; `--from` names another older commit.
- Only these evidence runs reach GitHub, read-only. Suites pass `--upstream` a local
  repository built at test time instead.

## Parsers

One parser per side (#44 §5): the generator's library holds the machine side's, and the gate
script, `generator/govern-repository/store/1/templates/dot-github/governance/gate.py`, holds
the governed repository's. Both register in the `parser-fixtures` suite.

- **The gate script's interface.** In a governed repository it is
  `.github/governance/gate.py`, and a script beside it, such as Merge watch's
  `merge_watch.py` or the owner script's embedded Python, runs `import gate`. A script run
  by path finds it on its own directory; embedded Python first puts `.github/governance/`
  on `sys.path`. Set
  `sys.dont_write_bytecode = True` before the import, so no `__pycache__` lands in the
  governed tree. The module's docstring gives the gate's rules and the pattern rules.
  - `parse_record(data)` takes the record's bytes and returns it in the shape
    `tests/suites/parsers.py`'s docstring gives, or raises `gate.RecordError`.
  - `parse_body(body)` returns `{"risk": ..., "reverts": ...}` in that docstring's shapes.
  - `matches(pattern, path)` matches a sensitive-path pattern against a root-relative path.
  - `verdict(repo, author, owner, body, default_head, head)` is Seam 1. It returns
    `{"passed", "failures", "pure_revert"}`, and each failure is one line led by its rule.
- **Its template loads as it is**, since its one token sits in its first line, a comment:
  `PARSERS` in `tests/suites/parsers.py` loads it by path.
- **The record**: `govlib/record.py`, whose docstring defines the format in full. A list key
  with no items is null in YAML, and the record reads it as an empty list, which is how
  rendering writes one. Text that starts like a number, or that YAML could read as null or
  a boolean, doesn't parse unless double-quoted, and rendering double-quotes every
  confirmed value.
- **The PR body's `Risk:` and `Reverts:` lines**: `govlib/prbody.py`. Only lines that start
  with `Risk:` or `Reverts:` count, inside comments and code fences too, and a CRLF body
  reads as LF.
- **The shared parser fixtures**: `tests/fixtures/parsers/`, with every fixture's expected
  result in `expected.json`, where the inputs `git diff --check` would flag sit as inline
  texts. The `parser-fixtures` suite runs each fixture against every parser in `PARSERS` in
  `tests/suites/parsers.py`. A parser registers as one more `Parser` there, whose adapters
  return the shapes that file's docstring gives, so registering changes no fixture or
  expected result. A record that doesn't parse expects only "doesn't parse".

## Merge watch

Version 1's fixed templates `.github/workflows/merge-watch.yml` and
`generator/govern-repository/store/1/templates/dot-github/governance/merge_watch.py` (#41 §9).
The script's docstring gives what it records, from which facts, and how an unreadable fact
yields a false miss record; it never blocks anything and is never a required check.

- **Seam 2** is `merge_watch.decide(event_name, event, agent_account, read)`, where `read`
  answers a REST path with GitHub's list, every page joined, or raises `ReadError`. Its
  output is the records to open. A new case joins `tests/fixtures/merge-watch/cases/` and is
  never renamed; the suite's docstring gives a case's shape.
- **GitHub's facts it relies on**, from github/docs at `6cbe641`, read 2026-10-30:
  - `on.workflow_run.workflows` takes the patterns of the workflow syntax's Filter pattern
    cheat sheet ("You can use special characters in path, branch, tag, and workflow name
    filters"): `**` matches any characters, `/` included, and `!` at a pattern's start
    negates the positive patterns before it. `["**", "!merge-watch"]` matches every
    workflow but Merge watch, whose `name:` is `merge-watch`; a workflow without one is
    named by its file path.
  - `workflow_run` fires only for a workflow file on the default branch, its `branches`
    filter names the branch the triggering run ran on, and chaining stops at three levels.
  - Bugbot's check run comes from the app `cursor` (PR #85's head `bfec87b`), and Cursor
    concludes a finished review `success`, `neutral` (findings, a newer commit's
    cancellation, or an internal error) or `failure` (findings, when set to fail on them),
    and never `skipped` (Cursor's Bugbot docs, CI check statuses, read 2026-10-30); the Codex
    review bot keeps one summary comment per PR by `chatgpt-codex-connector[bot]`, edited in
    place, holding `<!-- codex-review-state:v1 {...} -->` (PRs #66 to #85).
  - The list endpoint `commits/{ref}/statuses` gives each status's `creator`, newest first;
    the combined `commits/{ref}/status` doesn't, so the script reads the list (GitHub's REST
    reference for commit statuses, read 2026-10-30).
- **The live check** is below, under Merge watch's live check.

## The owner script and live checks

The owner script is version 1's fixed template
`generator/govern-repository/store/1/templates/dot-github/governance/owner.sh` (#44 §7). Its
docstring gives the preconditions, the order of writes and the exit codes (0 in place, 1 an
item failed or missing, 2 stopped before any write).

- **Its shape.** Line 1 is `#!/bin/bash`, so step 5's `/bin/bash -n` finds it; line 2 is the
  notice; its mode is `100755` in the manifest and the index. The bash entry feeds the Python
  program to `/usr/bin/python3 -I` through a quoted heredoc, so step 5 never parses that
  program: the `owner` suite parses it as 3.9. `@@version@@` in the notice is its only token.
- **The owner-script command** has one home, `govlib/owner.py`, and prints with
  `python3 generator/govern-repository/scripts/govern.py owner-command --repository <owner/name>`.
  habit runs it with the `!` prefix; agents never run it or the script against real GitHub.
  For `OWNER/NAME` it reads:

  ```text
  /bin/bash -c 'set -eu; d="$(mktemp -d)"; trap "rm -rf \"\$d\"" EXIT; git clone --quiet --depth 1 --no-checkout https://github.com/OWNER/NAME.git "$d/r"; git -C "$d/r" checkout --quiet --detach origin/HEAD; env -u GH_TOKEN -u GITHUB_TOKEN -u GH_ENTERPRISE_TOKEN -u GITHUB_ENTERPRISE_TOKEN GH_CONFIG_DIR="$HOME/.config/gh-maintainer" /bin/bash "$d/r/.github/governance/owner.sh"'
  ```

- **GitHub's facts it relies on**, read 2026-10-28: the GitHub Actions app's id 15368 from
  `GET /apps/github-actions`; the admin role's bypass actor id 5 from GitHub's own exported
  rulesets in `github/docs` at `57f571f`, since no prose states it; the repository-level
  Actions policy endpoints `/repos/{owner}/{repo}/actions/policies` and their allowlist-only
  `restrict_action_events` rule, from the same commit. GitHub returns rulesets and policies
  with fields the script never sent and leaves `update` bare, so it compares only what the
  target declares. Ruleset ref patterns are Ruby's `File.fnmatch` with `FNM_PATHNAME`
  (`github/docs` at `57f571f`, "Using `fnmatch` syntax", read 2026-10-29). The script
  decides which rulesets apply to the default branch with a step-by-step port of Ruby's
  `fnmatch`, `fnmatch_helper` and `bracket`. `tests/fixtures/owner/ref-patterns.json` records
  Ruby's own answers, which Seam D checks row by row. GitHub refuses a backslash and doesn't
  support complementing a set with `^` (same source), so a ruleset whose pattern has either is
  never removed: the report fails it and names the reason. The live probe `owner-state` asks
  `/usr/bin/ruby` itself instead of sharing the port.
- **Seam D** (`tests/suites/test_owner.py`) runs each case as `owner_support.py`'s docstring
  defines it. `tests/target_state.py` is #41 §7 written independently of the script; Seam D's
  recorded bodies and the live probes both compare against it. A new case joins
  `tests/fixtures/owner/cases/` and is never renamed.
- **Live checks** run through `tests/live/live.py` as the agent account, in the two
  sandboxes only. Its docstring lists the subcommands; `tests/live/probes/__init__.py` gives
  the one probe shape, and a live-check delivery adds its probes as a module there without
  changing the runner. One check, for a sandbox:
  1. habit runs `live.py sandbox-command`'s line once, then connects Bugbot (the Cursor
     GitHub App's repository access) and the Codex review bot (its connector's repository
     list) for both sandboxes. `live.py seed --sandbox <s>` then accepts the invitation and
     seeds the empty default branch from `tests/fixtures/repositories/sandbox/`, whose
     `fixture.json` holds the sandboxes' fixed confirmed values.
  2. `live.py prepare --pr <n> --sandbox <s> --probe <name>...`, at this checkout's pushed
     PR head, opens the sandbox PR, with a record under `live-checks/` so one exists even
     when the render is unchanged, and prints habit's commands: the pinned merge command,
     the owner-script command, then each probe's commands, each saving its output in the
     check directory.
  3. After habit's steps, `live.py probe --state <dir>/prepared.json --probe <name>... --post`
     posts the result comment, naming the commit. The owner probes need one run without
     `--post` between habit's two owner-script runs (`probes/owner.py`).

## The gate's live check

`tests/live/probes/gate.py` holds the gate's probes (#41 §8): `gate-trigger`, `gate-reruns`,
`gate-source` and `gate-rulesets`, run together, with the input `owner_report` that every check
takes. Its docstring gives the setup, the probe PRs and what each assertion reads.

- **Three steps after habit's merge and owner-script run:** `live.py probe` without `--post`
  sets the check up as the agent account; habit runs `gate-rulesets`' one command; then
  `live.py probe --post` judges. The setup writes the targets of habit's command to
  `gate_targets.txt` in the check directory.
- **The entry is `tests/live/gate_attempts.py`.** `gate-rulesets` prints a thin shell
  invocation of `/usr/bin/python3` with `--repository`, `--branch` and `--targets` pointing
  at the existing targets file. The entry owns preparation, dispatch, stop classification
  and the final ref read; subprocess argument vectors are separate from shell quoting.
  Absolute entry paths and quoted values let the command run from an unrelated directory.
  Importing, setting up or judging a probe never invokes the entry.
- **The attempts stay with habit.** The agent's direct push to the default branch, its
  force-push and its merges are habit's command, run as the agent account with `gh`. Claude
  Code's auto mode refused them to the agent on 2026-10-30. The probes never push to the
   default branch, force-push or merge.
- **Stop on the first success.** If an attempted push or merge exits 0, the command runs no
  later attempt and exits 3. Its output keeps that attempt's `exit=0`, prints
  `stop-after: <attempt>` with Chinese advice, and retains `== account` and `== after`;
  the latter reads refs after the stop. habit then stops as for a product question, rather
  than rerunning the command. `gate-rulesets` fails the success and each skipped attempt
  explicitly, and still reads both refs and every probe PR from GitHub. A clone, checkout
  or amend failure prints `never-reached:`: the push never reached GitHub, so it is neither
  a success nor a rejection; later attempts still run. When every attempt is rejected,
  the command keeps its section headers and `exit=` lines, prints no stop and exits 0.
- **Offline coverage** in `live-runner` executes the same generated invocation under bash
  with test-local `git` and `gh`, verifies every call's executable and complete arguments,
  and judges the captured protocol. It covers all six success positions, preparation
  failures, missing targets (exit 2 before tool calls), healthy rejections and quoted paths.
  It also appends the runner's unchanged `2>&1 | tee` capture decoration: the output's
  stop marker, not the outer pipeline status, tells the judge which attempts were skipped.
  These stand-in runs make no claim about live protection behavior; real attempts remain
  habit-only.
- **The private sandbox (#53)** takes the same probes, unchanged: `prepare --sandbox private`
  and the same `--probe` names. They read the repository, default branch and confirmed checks
  from the context, and `gate-trigger` expects the event policy skipped (`已跳过`) there.
- **GitHub's facts they rely on**, read on 2026-10-30 from `Habit130/governance-sandbox`,
  and from github/docs at `6cbe641`:
  - A `pull_request_target` run's `head_sha` is the PR head. Its job checks out the default
    branch, whose commit the gate's log line names. The job's own check run and the
    script's posted one are both `governance-gate` from GitHub Actions (app 15368), in
    different check suites.
  - A body edit (`edited`) runs the gate again on the same head. The first run's failing
    check run stays on the head, but a merge rejection then names no required check.
  - Skip instructions in a commit message don't stop `pull_request_target`
    (`skip-workflow-runs.md`). With no app pinned, a same-name check and status must both
    pass (`troubleshooting-required-status-checks.md`).
  - GraphQL's `isRequired` reads `true` for the agent's same-name status, so it is no
    evidence of what satisfies a pinned check. The agent's own merge state always reads
    `BLOCKED`, because the Merge ruleset restricts updates.
  - The rejections, quoted:
    - A direct push gets `GH013` with one `- ` line per rule: `Changes must be made
      through a pull request.`, `Required status check "governance-gate" was not set by
      the expected GitHub app.` and `Cannot update this protected ref.`
    - A force-push to another branch gets `Cannot force-push to this branch`.
    - A merge gets HTTP 405, `Repository rule violations found`, with
      `Required status check "governance-gate" is failing.` while the gate fails, and
      `Cannot update this protected ref.`

## Merge watch's live check

`tests/live/probes/merge_watch.py` holds Merge watch's probes (#41 §9, seam 4):
`merge-watch-clean` for a head with every review, and `merge-watch-miss` for a planted miss.
Its docstring gives each step and what each assertion reads.

- **The planted miss is the render PR.** It is declared high and nothing reviews it, so its
  merge always leaves a `missing-review` record, and `merge-watch-miss` judges that record.
  Miss records in a sandbox count nowhere (#44 §12).
- **Two sandbox merges, in this order after `prepare --probe merge-watch-clean --probe
  merge-watch-miss`:**
  1. habit merges the render PR and runs the owner-script command.
  2. `live.py probe` without `--post` opens the probe PR, requests Bugbot, posts the agent's
     `Reviewer` status and writes `merge_watch_codex.txt`.
  3. habit runs the printed Codex review bot request.
  4. `live.py probe` waits for both bots, posts the Merge summary and reports `READY`. Give
     it 40 minutes in the background: two 15-minute waits for Bugbot and 10 for the Codex
     review bot. It
     writes `merge_watch_merge.txt` only on `READY`.
  5. habit runs the printed pinned merge, which refuses until that file exists.
  6. `live.py probe --post` judges. Each sandbox PR's head is fixed by then; a new head would
     reset all four facts.
- **Merge watch's run decides CRIT-1, not the agent's reading.** A failed read counts as
  absent, so a push run that says `No miss in this push event.`, with no `UNREADABLE` line,
  has read all four facts with its own token.
- **A bot that doesn't answer stops the check.** After one Bugbot request and one retry, or
  a Codex wait that runs out, the run fails naming what came back. That is an environment
  blocker and never a reduction. The Merge summary lists every kind as `clear`, so no kind
  counts without being read.
- **Reading a run's log.** GitHub redirects it to Azure Blob Storage. On 2026-10-31 `gh` 2.98
  timed out in the TLS handshake with that host from habit's machine, while `curl` reached
  it, and `GODEBUG=tlsmlkem=0` cleared it. When the probes report that a log couldn't be
  read with `TLS handshake timeout`, run `live.py probe` with that variable set.
- **Not covered:** `workflow_run`. Planting a red default branch would take a new sandbox
  workflow, and neither #41's seam 4 nor #61's criteria ask for it.
- **The private sandbox (#53)** takes the same probes, unchanged: `prepare --sandbox private`
  and the same `--probe` names. They read the repository and default branch from the
  context, and habit's commands name that repository.
- **GitHub's facts they rely on**, from github/docs at `85c3298`, read 2026-10-31:
  `github-token-scope-descriptions.md` lists `contents`, `pull-requests`, `issues`, `checks`,
  `statuses` and `actions` as the permissions behind what the script reads and writes, and
  sets every unlisted permission to `none`. A run's log comes from
  `actions/jobs/<id>/logs`, the gate's read, through `gh api --allow-escape-sequences`.

## Version 1's cut and the end-to-end run

Version 1 is released once `generator/govern-repository/store/1/change-note.md` is on the
default branch (#44 §4). From then on the release check freezes `store/1/` byte for byte, a
defect becomes a later version, and a version's templates, manifest and note arrive in one PR.
`govern.py change-note <path>` reads a note's two fields.

The cutting PR's end-to-end run (#44 §11) is an Initialize of the public sandbox, after CI, the
Required order and the scenarios pass on the head. Every result names the head, so a later
push reruns them, the live checks and this run, with a fresh reset.

1. **The reset.** `live.py reset --sandbox public` opens a sandbox PR whose commit holds exactly
   the materialized seed, `tests/fixtures/repositories/sandbox/repo/`, checked against the
   seed's `git write-tree`. It prints habit's two steps, in this order: the pinned merge once the
   PR's checks pass, then disabling the Gate ruleset in the browser, Merge and History staying
   active. The Gate ruleset has no bypass, so the sandbox's still-governed default branch judges
   the reset PR; its `Risk: high` line clears every floor the removed paths carry. Gate is
   disabled afterwards because the Initialize PR can't report `governance-gate` until its gate
   workflow is on the default branch. The reset reads the public sandbox only.
2. **The launch.** `live.py end-to-end --pr <n> --sandbox public` refuses, leaving nothing
   behind, unless this checkout is clean at the PR's head, the sandbox's default branch holds
   the seed's tree, Gate is disabled with Merge and History active, and no directory above its
   new one under the system temporary directory holds an `AGENTS.md`, `CLAUDE.md` or
   `CLAUDE.local.md`, which a session there would load. It clones the sandbox afresh. Beside the
   clone it builds the session-only plugin `cut` from the head's committed generator
   (`git archive`), checks the plugin's identity hash against the head's, and has the plugin's
   own `mode` read the sandbox as Initialize. It writes `end-to-end.json`, the before state with
   the rulesets' enforcement included, and prints habit's line.
3. **habit's run.** habit starts Claude Code with that line in a terminal of their own, never
   with `!`. The line sets no `GOVERN_SCENARIO_` setting, so the run reads real GitHub as the
   agent account on the real machine. habit types `/cut:govern-repository`: the bare name
   resolves the installed copy. habit answers the confirmation, which lists the three rulesets
   for the owner script to replace. Then habit follows that run's Builder through the high path:
   Bugbot, habit's Codex review bot request, a Reviewer on another vendor, the high-risk
   report, the pinned merge, saying merged, and the owner-script command, which makes Gate
   active again.
4. **The outcomes.** Execution posts each step's outcome on the cutting PR, naming the head.
   The issue's `generator_identity` equals `end-to-end.json`'s identity; the Initialize PR's
   head carries a completed Bugbot check, the Codex review bot's completed marker, the
   Reviewer's Comment review and `Reviewer` status, and the high-risk report; habit's squash
   merge, Merge watch's push run on it, and the rulesets after the owner-script run. The live
   checks for the owner script, the gate and Merge watch then run through `prepare` and
   `probe` as the run's probes. If the runner can't take that order, they run before the
   reset, and the handback records why.

After the merge habit runs the install (README.md), which brings released version 1 to the
machine, and this repository's first Initialize follows as its own generator run. The cut's
record that habit reads says to run the install, that version 1 was cut, and its urgency
(#44 §8, Trigger).

## Operational constraints

- Everything tracked under `generator/`, `skill-copies/`, `machine/` and `tests/` is in stored
  form (#44 §3): a segment starting with `.` is stored as `dot-…`, and `AGENTS.md`,
  `AGENTS.override.md`, `CLAUDE.md`, `CLAUDE.local.md`, `opencode.json` and
  `opencode.jsonc` get `.stored`. The stored-form check fails otherwise.
- Suites build their git repositories under the system temporary directory, isolated from
  user and system git config, and reach GitHub and Codex only through `tests/standins/`.
- For governance deliveries, verify paths, links, headings, router targets, unresolved
  rendering placeholders, the root instruction budget (near 100 lines and below 12 KiB),
  and ignore behavior with `git check-ignore`. Template prompts are intentional;
  frozen contract bodies must have every prompt filled. Parse changed JSON when present.
- Local read-only checks run autonomously. GitHub operations require repository access
  and follow the frozen contract and `delivery.md`. Preserve unrelated work.
- No shared machine-level runtime, data store, deployment resource or product module
  boundary has been identified in this skeleton. Allocate any newly introduced shared
  resource explicitly before parallel writers use it.
- Engineering skills are installed in the local environment; availability in a session
  depends on its harness. If a listed skill is unavailable, report the gap and ask habit
  to launch it in an environment where it is available; never substitute a denied load.
