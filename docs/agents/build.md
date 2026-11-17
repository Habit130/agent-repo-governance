# Build and verification

A build document describes the current state only, and changes only when a command or
procedure changes. Keep historical counts and delivery narratives in Git history, issues
and PRs. Observed GitHub and review-bot behavior stays in the topic references.

What a PR needs by what it changes is `AGENTS.md`, This repository, Verification by
change. Human-facing setup stays in `README.md`.

## Commands

Run these in order, and every one must pass. Steps 2 to 6 are CI's steps in its order; step
7 prints the exact comparison that the `materialized-version` suite asserts in CI. None needs
a service or the network.

| Step | Command | Evidence / notes |
| --- | --- | --- |
| 1. Whitespace | `git diff --check origin/main...HEAD` | Also `git diff --check` before committing. |
| 2. Stored form | `python3 tests/run.py stored-form` | One PASS line, or one FAIL line per stored path that could load or fails to decode. |
| 3. Release check | `python3 tests/run.py release-check --base "$(git merge-base origin/main HEAD)" --head HEAD` | One PASS or FAIL line per rule, then INFO lines for new and changed fixtures. Use the merge-base: a newer `origin/main` would read its own new fixtures as removed. |
| 4. Linux suites | `python3 tests/run.py suites --job linux` | Whole verbose unittest output per suite, then each suite's result/count/duration and the total result/count/wall time. |
| 5. Python 3.9 and bash 3.2 | `/usr/bin/python3 tests/run.py py39` | Fails unless the interpreter is 3.9; parses every script as 3.9 and runs `/bin/bash -n` on every shell entry. |
| 6. Every suite under 3.9 | `/usr/bin/python3 tests/run.py suites --all` | Every suite in a separate 3.9 child; whole verbose output per suite, then per-suite and total summaries as in step 4. |
| 7. Exact comparison | `python3 tests/run.py exact-comparison` | Renders version 1 into the tally sample repository and prints exact comparison's JSON; `differences` must be empty. |
| 8. Committed whitespace | `git show --format= --check HEAD` | After committing. |
| 9. Scope | `git diff --stat origin/main...HEAD` and `git status --short` | Inspect against the ticket. |

`tests/run.py suites <name>...` runs single suites while working. For runner options and
coverage, read [Testing](../build/testing.md).

## CI

`.github/workflows/ci.yml` runs on every PR and on pushes to `main`, with no path filter,
in two jobs whose names stay stable: `linux` and `macos`, the required checks habit confirmed
at this repository's Initialize, beside the governance gate's `governance-gate`. Pushes to
other branches and tags don't run CI. A merge's push-triggered run tests the actual merged
combination and is the Builder's after-merge smoke check: record that run and its result;
green PR CI alone isn't that evidence. A failed default-branch run is observed by Merge
watch for a `red-default-branch` miss record. The governance workflows,
`governance-gate.yml` and `merge-watch.yml`, are the generator's (`AGENTS.md`, Governance files).

- **`linux`**, on `ubuntu-24.04` with its `python3`: steps 2 to 4. Checkout depth is two.
  On a PR, `HEAD` is GitHub's PR merge commit and `HEAD^1` is its base-branch parent;
  on a squash push to `main`, `HEAD` is the squash commit and `HEAD^1` is the previous
  `main`. The release check compares these two trees in both events. The offline
  `release-check` suite proves both shapes with real shallow fetches, including rejection
  of a frozen-template edit; it doesn't substitute for the hosted push run.
- **`macos`**, on `macos-15`: steps 5 and 6 with `/usr/bin/python3`, which is Python 3.9.6
  there, beside `/bin/bash` 3.2.57.
- Both use no model, credential, network, GitHub writes, third-party actions or package
  installs in their suites. Checkout is the existing pinned external action and needs
  GitHub/network access; its only token is the read-only `GITHUB_TOKEN`, not kept in the
  checkout. Standard runners are free on a public repository, per GitHub's
  [runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

## Actions secrets

CI uses no Actions secret: the only token is the checkout's read-only `GITHUB_TOKEN`, not
kept in the checkout.

Only habit writes Actions secrets (`AGENTS.md`, Secrets).

## Commands only habit runs

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
- **The owner-script command** has one home, `govlib/owner.py`, and prints with
  `python3 generator/govern-repository/scripts/govern.py owner-command --repository <owner/name>`.
  habit runs it with the `!` prefix; agents never run it or the script against real GitHub.
  For `OWNER/NAME` it reads:

  ```text
  /bin/bash -c 'set -eu; d="$(mktemp -d)"; trap "rm -rf \"\$d\"" EXIT; git clone --quiet --depth 1 --no-checkout https://github.com/OWNER/NAME.git "$d/r"; git -C "$d/r" checkout --quiet --detach origin/HEAD; env -u GH_TOKEN -u GITHUB_TOKEN -u GH_ENTERPRISE_TOKEN -u GITHUB_ENTERPRISE_TOKEN GH_CONFIG_DIR="$HOME/.config/gh-maintainer" /bin/bash "$d/r/.github/governance/owner.sh"'
  ```

- **Installed machine check**, against habit's home: `/usr/bin/python3
  ~/.agents/governance/machine/scripts/machine.py check`.
- **Sandbox setup and gate attempts:** habit runs `live.py sandbox-command`'s line and
  `gate-rulesets`' printed command, including its agent-account push and merge attempts.
  See [live checks](../build/live-checks.md) for setup, evidence and stop conditions.
- **Release Initialize:** habit runs the line printed by `live.py end-to-end`, then
  `/cut:govern-repository` in that Claude Code session. See [Releasing](../build/releasing.md).
- **Review requests, pinned merges, waivers and settings:** habit follows each printed
  command or browser step in [live checks](../build/live-checks.md) and
  [Releasing](../build/releasing.md). The normal delivery handoff is in `review.md`.
  Generator `preconditions` remains habit-run: it invokes the machine check against habit's home.

## Operational constraints

- Everything tracked under `generator/`, `skill-copies/`, `machine/` and `tests/` is in stored
  form (#44 §3): a segment starting with `.` is stored as `dot-…`, and `AGENTS.md`,
  `AGENTS.override.md`, `CLAUDE.md`, `CLAUDE.local.md`, `opencode.json` and
  `opencode.jsonc` get `.stored`. The stored-form check fails otherwise.
- Suites build their git repositories under the system temporary directory, isolated from
  user and system git config, and reach GitHub and Codex only through `tests/standins/`.
- For governance deliveries, verify paths, links, headings, router targets, unresolved
  rendering placeholders, and ignore behavior with `git check-ignore`. Template prompts
  are intentional. Parse changed JSON when present.
- The shared resources are the two sandbox repositories. Allocate one explicitly in the
  ticket before parallel writers use it (`AGENTS.md`, This repository).

## Topic index

| When the work needs | Read |
| --- | --- |
| Suite selection or coverage, draft development, parser contracts, Codex-policy or ref-pattern corpora | [Testing](../build/testing.md) |
| Generator commands, refusals, rendering, comparison or observed GitHub API behavior | [Generator command line](../build/generator.md) |
| Install, machine check, account wizard, Codex observations or refreshing skill copies | [Machine and skill copies](../build/machine.md) |
| Gate, Merge watch, owner script, sandbox preparation or live evidence | [Live checks](../build/live-checks.md) |
| Cutting a version, release Initialize, adoption checks or retired scenario reference | [Releasing](../build/releasing.md) |
