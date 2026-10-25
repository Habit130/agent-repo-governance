# AGENTS.md

This file holds agent-repo-governance-specific boundaries, workflow rules, review invariants and
context routing. Personal and global preferences load from each harness's user-level
configuration.

## Repository boundary

- This tool repository develops a personalized repository-governance system inspired by
  Anthropic code-review practices and mattpocock/skills, with consistent policy across
  the supported harnesses named in README.md.
- This initialization establishes this repository's operating contract only. Product
  implementation, skill installation and changes to other repositories are separate work.
- habit owns product and scope decisions and the final merge. Preserve pre-existing work;
  isolate delivery writes in an exclusive branch or worktree.

## Roles and risk

- Every writing session declares one role in its initiating prompt, independent of model and
  harness: **Orchestration**, **Execution** or **Acceptance**.
- **Orchestration** plans, freezes contracts, declares risk and dispatches; it does not
  implement or repair product code.
- **Execution** owns one frozen contract and its PR; it implements, verifies and repairs,
  and never edits the contract.
- **Acceptance** is a review session independent of the Execution session; it writes
  acceptance records only and fixes nothing.
- habit starts every session and every user-invoked skill, decides product and scope, and
  performs the final squash merge.
- Orchestration declares a low, medium or high risk tier at dispatch; Execution and
  Orchestration may raise it from the diff; only habit lowers it. Medium and high need a
  passing Acceptance. The low path serves daily deliveries only: first initialization and
  governance upgrades are high.

## Git and PR workflow

- `origin` = `https://github.com/Habit130/agent-repo-governance.git`, the write remote and PR target.
- The default branch is `main`; local `main` tracks `origin/main`.
- Start each delivery from the latest `origin` default branch on a `<type>/<kebab-slug>`
  branch. Do not stack PRs.
- One frozen issue, one branch and one PR per delivery; in spec mode the PR closes the spec
  and its tickets.
- Use English Conventional Commits. PR bodies follow `.github/PULL_REQUEST_TEMPLATE.md`.
- Agents may branch, commit, push, and create and update PRs. No agent merges, enables
  auto-merge, force-pushes, rewrites history, or resets destructively (discarding commits or
  uncommitted work the session does not own).
- habit squash-merges. Completion is recorded only after the result is verified on the
  default branch of `origin`.

## Verification by change

What a PR needs follows what it changes, not its tier (#44 §11). Each row binds once its tool
exists: CI now, scenarios with the scenario runner, live checks with the live-check runner.
Commands and CI jobs: `docs/agents/build.md`.

| The PR changes | It needs |
| --- | --- |
| Anything | Green CI: the `linux` and `macos` jobs on the head |
| The generator's skill text, templates or scripts, or the scenarios | Plus scenario results: each Claude Code scenario three times, plus the OpenCode smoke scenario |
| The gate workflow, Merge watch, the owner script, the target state, or the record format the gate reads | Plus a live check in the sandbox repository |
| Version 1's cut | All of the above, plus one end-to-end run in the sandbox repository |

- Until this repository's Initialize, Execution carries the Builder's duty: it runs the
  scenarios and live checks, posts results naming the commit they ran on, and reruns them
  after a later push that touches the second or third row.
- Acceptance, or the low-tier pre-merge check, carries the Reviewer's and the
  merge-summary writer's duties: it confirms every required result names the head and
  passed every assertion, judges each Chinese confirmation, and reruns only when results
  look inconsistent.
- The record habit reads (the high-tier report, the Acceptance record at medium, the
  pre-merge check at low) carries a Chinese verification block: one line each for CI,
  scenarios, and the live check or why none was needed; new fixtures with their miss
  records; anything not run, with the reason.
- A failing check never reaches habit: Execution repairs it before handing back, and a
  review that finds one fails the delivery.
- Fixtures are never removed or renamed; the release check enforces it. A PR that changes
  an expected result says so in its change note when it cuts a version, otherwise in its
  body. A miss that generator output or the install caused adds a fixture in its fix's PR.

## Code Review Rules

- Rate each finding P0, P1, P2, P3 or Pre-existing, with `path:line` evidence, its trigger,
  its impact and the safe path. P0 and P1 block; P2, P3 and Pre-existing never block.
  Detail, follow-up dispositions included: `docs/agents/review.md`.
- Report P1 if contradictory cross-harness rules break a supported governance operation;
  safe path: maintain one canonical policy and route harness-specific instructions to it.
- Report P1 if a supported workflow lets Execution change its frozen contract or lets an
  agent merge; safe path: return contract changes to Orchestration and merge decisions to habit.

## Agent skills

Load detailed guidance only when the task triggers it:

| Task | Required context |
| --- | --- |
| Issue tracker operations: create, read, claim, comment, publish specs and tickets | `docs/agents/issue-tracker.md` |
| Triage roles and tracker labels | `docs/agents/triage-labels.md` |
| Plan, dispatch, execute, hand back, accept, repair or merge a delivery; choose skills | `docs/agents/delivery.md` |
| Review a change, rate a finding, choose a risk tier | `docs/agents/review.md` |
| Build, lint, test, package or CI | `docs/agents/build.md` |
| Domain terms, boundaries or architectural decisions | `docs/agents/domain.md`, then relevant `GLOSSARY.md` and `docs/adr/` entries when present |

Follow only the rows relevant to the current task and any further pointers they contain.
