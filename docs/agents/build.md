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
| `materialized-version` | Version 1 from the real store, rendered into tally and compared exactly, and its record parsed; #41's seam-3 checks join it | linux |
| `record` | Version 1's record template, rendered with sample confirmed values and read back; confirmed values the parser would refuse, refused at rendering | linux |
| `parser-fixtures` | Every registered parser against every shared parser fixture, one test per parser and fixture | linux |
| `release-check` | Seam E: every fixture in `tests/fixtures/release-check/` | linux |
| `standins` | The stand-in GitHub and the Codex stand-in, a stray call included | macos |

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
subcommands (`store`, `change-note`, `render`, `compare`, `materialize`) print JSON and exit
0 on good facts, 1 when exact comparison finds differences, and 2 on a refusal, with the
reason under `error`.

- **Exact comparison in a governed worktree** is one command:
  `python3 generator/govern-repository/scripts/govern.py compare --worktree <path>`. It reads
  the repository and default branch from the worktree's `origin`, and compares the installed
  version unless `--version` names another.
- **Unreleased versions** are rendered or compared only with `--allow-unreleased`, which a
  test, scenario or live-check runner passes for its own run. The generator's procedure
  never passes it.
- **Exact comparison** checks content and mode of every fixed file, every fixed part between
  its markers, and the record up to its one top-level `confirmed:` key, after which only
  indented values, blank lines and comments may follow. It leaves the confirmed values,
  which are the repository's own, and skeletons, which become repository-owned content.
- **Rendering a fixed part** writes the whole template when the target is absent, replaces
  the one well-formed marker block when there is one, and refuses anything else. A skeleton
  is written only when its target is absent. Repairing or rebuilding markers is #50's.
- **One template per target path.** A mixed file's template holds its fixed part between the
  markers and its skeleton text after them. The record template ends at its `confirmed:`
  key, and rendering writes the confirmed values below it. Rendering refuses confirmed
  values, or a template, whose record wouldn't parse.
- **Writes stay inside the destination.** Rendering and materializing refuse a target whose
  parent is a symlink or not a directory before writing anything.
- **The change note** opens with `urgency: urgent` or `urgency: when convenient`, then
  `must-act: yes` or `must-act: no`, then a blank line and the plain-Chinese body. Its parser
  and fixtures: `govlib/store.py` and `tests/fixtures/change-notes/`.

## Parsers

One parser per side (#44 §5): the generator's library holds the machine side's, and the gate
script holds the governed repository's, which #55 builds.

- **The record**: `govlib/record.py`, whose docstring defines the format in full. A list key
  with no items is null in YAML, and the record reads it as an empty list, which is how
  rendering writes one. Text that YAML could read as null, a boolean or a number doesn't
  parse unless double-quoted, and rendering double-quotes every confirmed value.
- **The PR body's `Risk:` and `Reverts:` lines**: `govlib/prbody.py`. Only lines that start
  with `Risk:` or `Reverts:` count, inside comments and code fences too, and a CRLF body
  reads as LF.
- **The shared parser fixtures**: `tests/fixtures/parsers/`, with every fixture's expected
  result in `expected.json`, where the inputs `git diff --check` would flag sit as inline
  texts. The `parser-fixtures` suite runs each fixture against every parser in `PARSERS` in
  `tests/suites/parsers.py`. A parser registers as one more `Parser` there, whose adapters
  return the shapes that file's docstring gives, so registering changes no fixture or
  expected result. A record that doesn't parse expects only "doesn't parse".

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
