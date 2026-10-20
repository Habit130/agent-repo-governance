# Delivery Protocol

How one frozen contract moves from dispatch to a merged delivery. The issue is the only
acceptance-contract body. `review.md` owns severity, risk criteria and record formats;
`issue-tracker.md` owns tracker commands.

## Roles

Roles bound authority and are independent of model and harness: any model may hold any
role. A session declares one role in its initiating prompt. habit starts every session and
every user-invoked skill; a session that returns work to habit ends with a next-step block.

- **Orchestration** keeps issues, plans, ADRs, the glossary and governance documents current
  within habit's standing authorization; discussion alone is read-only. It declares risk,
  freezes contracts, dispatches, runs the low-tier pre-merge check, completes deliveries and
  opens follow-up and environment-improvement issues. New product, scope and risk-lowering
  decisions are habit's. It does not implement or repair product code. Delivery state lives
  in the tracker, so a replacement session starts by refreshing it.
- **Execution** owns one frozen contract, its branch or worktree and its PR. It claims the
  issue, implements, verifies, repairs, delegates bounded helpers and hands back evidence.
  It never edits the contract.
- **Acceptance** is a review session independent of the Execution session; a different
  model is not required. It reads the contract, every commit, the diff and the automated
  review, runs checks in its own temporary worktree (`review.md`), and writes acceptance
  records only. Implementation and repair return to Execution.
- **Helpers** are subagents. They inherit the caller's role, scope, permissions and secret
  rules, and the caller stays accountable. Each writer owns an exclusive scope; parallel
  writers each use their own worktree. Delegation creates no authority the caller lacks.
- **Switch**: after dispatch, habit may tell the Orchestration session to continue as
  Execution of that contract. The session records the switch on the issue and can no longer
  change that contract. Medium and high review stays a separate session.

## Risk tiers

Orchestration declares `low`, `medium` or `high` at dispatch, using the criteria in
`review.md`. Execution and Orchestration may raise the tier from the observed diff and
record why; only habit lowers it. The PR states the current tier.

| Tier | Path to merge |
| --- | --- |
| low | Orchestration pre-merge check, then habit squash-merges |
| medium | passing Acceptance record, then habit squash-merges |
| high | passing Acceptance record plus its report, which habit reads before reviewing, then habit squash-merges |

First initialization and governance upgrades are high; later governance changes are at
least medium. The low path serves daily deliveries only.

The **pre-merge check** is an Orchestration session confirming, on the exact head, that
required checks are green (CI, or the Verification output when there is no CI), the
evidence matrix passes every criterion, the automated review is clear (`review.md`), no
sensitive path is touched, and the diff stays inside the contract's scope. Without an
automated review, a fresh-context `code-review` subagent, pinned to the contract's base
with the issue as Spec, takes its place. The result is a PR comment that recommends merge
or names the blocker; habit decides.

## Modes

- **single**: one issue holds the contract. `implement` builds it and one PR closes it.
- **spec**: Orchestration turns a settled design into a spec (`to-spec`) and tickets
  (`to-tickets`). The spec carries the governance header; tickets keep their upstream body.
  `implement-spec` builds the tickets on one integration branch that Execution owns, and one
  PR closes the spec and its tickets.
- **exploration**: habit starts an Execution session, which self-calls `prototype` to answer
  one design question on a `prototype/<slug>` branch that is never merged. The issue
  (`.github/ISSUE_TEMPLATE/exploration.md`) states the question, allowed resources and run
  steps, and its handoff carries no risk field. Execution records the answer, limits and
  exact head on the issue; habit judges whether the question is answered. Exploration has no
  risk tier and no BASE criteria, grants no production writes, and never serves
  initialization or upgrades. Product work that follows needs its own contract.

Choose by size, context needs and independent delivery value; a small, clear task needs
neither spec nor tickets. Upstream `ask-matt` (habit-started) governs how skills sequence.

## Skills

Use upstream skills as published. habit starts user-invoked skills in every harness (`@name`
in OpenCode, `/name` in Claude Code); a session never loads one itself and asks habit when it
needs one. A denied skill load is never worked around by reading the skill's files or
altering permissions; the session asks habit. Self-called skills load when the task reaches
them, and any other model-invoked skill (for example `writing-for-agents` when editing
instructions) is self-called within the role's authority.

| Role | habit-started | Self-called |
| --- | --- | --- |
| Orchestration | `grill-with-docs`, `to-spec`, `to-tickets`, `wayfinder`, `triage`, `to-questionnaire`, `improve-codebase-architecture` | `research`, `prototype`, `code-review` (low-tier check) |
| Execution | `implement`, `implement-spec` | `tdd`, `diagnosing-bugs`, `codebase-design`, `prototype`, `pr`, `research` |
| Acceptance | none | `code-review`, `research`; read-only |
| habit, any session | `retro`, `handoff`, `ask-matt` | none |

## Dispatch

Orchestration prepares and habit starts. Before posting the handoff, Orchestration:

1. refreshes issues, PRs, branches, assignees, comments and shared state;
2. freezes the contract (below) and swaps `needs-triage` for `ready-for-agent`;
3. allocates the branch or worktree and every shared resource exclusively; an occupied
   resource pauses that allocation, so preserve existing work and allocate an unused one;
4. makes glossary and ADR changes from the discussion the first commit on the delivery
   branch, or ships them as a docs-only issue and PR at the tier `review.md` gives them when
   no delivery follows;
5. posts the handoff comment and ends with the next-step block that starts Execution.

`ready-for-agent` alone authorizes nothing: Execution starts only from a handoff comment
that habit launches.

## Contract

The issue holds the upstream body (`.github/ISSUE_TEMPLATE/delivery.md`) under a governance
header: `Risk`, `Mode`, `Verification` and `Baseline`. Criteria carry stable IDs `CRIT-<n>`,
numbered once and never reused, each with expected evidence. `Baseline` names the BASE
criteria by ID and the governance commit that defines them here.

- **BASE-EVIDENCE**: Execution maps every criterion to primary evidence and Pass/Fail;
  Acceptance, when the tier requires it, provides its own complete mapping.
- **BASE-VERIFY**: Every command in `Verification` succeeds in the stated order, with its
  output cited as evidence.
- **BASE-SEVERITY**: The PR introduces no confirmed P0/P1 (`review.md`), and every
  automated-review finding is confirmed or rejected with evidence.
- **BASE-SCOPE**: Work outside the contract's scope is untouched or recorded as deferred;
  excluded scope is not implemented.
- **BASE-DOCS**: Behavior, interface, workflow or constraint changes update the
  authoritative documentation in the same delivery.
- **BASE-PR**: The PR follows `.github/PULL_REQUEST_TEMPLATE.md`: it closes the contract
  issue (spec mode: the spec and its tickets), states the risk tier, and carries Summary,
  Evidence and Merge Danger with door, blast radius and revert.

### Freeze and versions

Posting the handoff freezes the contract and pins the SHA-256 digest of its body; in spec
mode it pins the spec and every ticket. Execution verifies each pinned digest at claim; a
mismatch stops work and goes to Orchestration.

```text
printf '%s\n' "$(gh issue view <n> --json body --jq .body | tr -d '\r')" | shasum -a 256
```

A change of scope, outcome or acceptance appends a version: Orchestration edits the body to
`AC-<issue>-v<n+1>`, records habit's decision under Contract changes, and posts the
contract-version comment and a new handoff; dependent work waits for Execution's renewed
claim. Evidence and records go in comments, never in the body.

### Records

The issue holds the contract and its lifecycle. The PR holds the records bound to a head,
and whoever posts one links it from the issue in one line.

| Record | By, when | Where | Fields |
| --- | --- | --- | --- |
| Handoff | Orchestration, at dispatch | issue | contract ID and round; digest; risk with reason; mode; base commit, branch, worktree; habit-started skills with OpenCode and Claude Code syntax; self-called skills; allocations; stop conditions; launch prompt |
| Switch | the switching session | issue | `Orchestration to Execution for <contract>`; the contract is no longer its to change |
| Claim | Execution, before editing | issue | contract ID and round; digests verified; actual base commit, branch, worktree; skills loaded; assigns the issue to itself |
| Contract version | Orchestration, at a version | issue | new contract ID; habit's decision; changed criteria; new digest |
| Handback | Execution, when done | PR | see Handback |
| Automated-review state | Execution, per head | PR | `review.md` |
| Pre-merge check | Orchestration, low tier | PR | format in `review.md` |
| Acceptance record, high-tier report | Acceptance, medium and high | PR | format in `review.md` |
| Completion | Orchestration, after merge | issue | see Completion |

In a handoff the skill lines read, for example, `habit invokes: implement (OpenCode
@implement, Claude Code /implement)` and `Self-called: tdd, code-review, pr`.

Stop conditions in every handoff: a digest mismatch, a scope or acceptance change, or a
product question the contract does not settle. Comment on the issue, pause the affected work
and end with a next-step block that names the open decision and carries the contract-version
launch prompt; routine in-contract choices and repair need no approval.

## Next steps

Every session that returns work to habit ends its terminal reply with a next-step block. The
block carries absolute paths; the tracker record that hands the work on carries the same
launch prompt without machine paths. habit sends the invocation and the launch prompt in one
message.

```text
Next step for habit
Do: [one action: start a session, merge, or decide]
Where: [harness, and the absolute path of the worktree or checkout to start in]
Invoke: [OpenCode @<skill>, Claude Code /<skill>; or none]
Paste: [the filled launch prompt]
Read first: [the records or files to read before acting; or none]
After: [what the next session returns, and where]
```

A launch prompt points at its handoff or record instead of repeating it. Fill the brackets:

```text
Orchestration start: Role: Orchestration. [Goal, or issue URL]. Read AGENTS.md and docs/agents/delivery.md, refresh the tracker, and end with a next-step block.
Execution: Role: Execution. Contract [AC ID], round [r], mode [mode], risk [tier]. Handoff: [handoff URL]. Work only in the worktree it names. Read AGENTS.md and docs/agents/delivery.md, then follow that handoff.
Repair round: Role: Execution. Contract [AC ID], round [r], repair. Record: [Acceptance record URL]. Work in the worktree the handoff names. Read AGENTS.md and docs/agents/delivery.md, fix each Fail, and hand back on the PR.
Acceptance: Role: Acceptance. Contract [AC ID], round [r], risk [tier]. Handback: [handback URL] at head [sha]. Read AGENTS.md, docs/agents/delivery.md and docs/agents/review.md, assess that head, and post the records on the PR.
Pre-merge check: Role: Orchestration. Pre-merge check of contract [AC ID], low tier. Handback: [handback URL] at head [sha]. Read AGENTS.md, docs/agents/delivery.md and docs/agents/review.md, then run the check and post it on the PR.
Completion: Role: Orchestration. Complete contract [AC ID]; PR [URL] is merged. Follow-ups: [findings marked yes that habit keeps; or none]. Read AGENTS.md and docs/agents/delivery.md, then follow Completion.
Contract version: Role: Orchestration. Version contract [AC ID]. Stop: [stop comment URL]; habit decides: [decision]. Read AGENTS.md and docs/agents/delivery.md, append the version and post the new handoff.
```

## Handback

Execution writes the PR body with `pr`, adding the `Closes`, `Risk` and `Revert` lines the PR
template requires, and ends with a handback comment on the PR, linked from the issue:

- the contract ID and the exact head;
- a `CRIT or BASE ID -> primary evidence -> Pass/Fail` row for every criterion;
- the commands run and their material output;
- the automated-review state on that head;
- deferred work, out-of-contract findings and decisions the contract left open;
- the next session's launch prompt: the pre-merge check for low, Acceptance otherwise.

Execution leaves the issue and PR open, releases write ownership and ends with the next-step
block.

## Repair

A round is one Execution pass plus one review; the initial delivery is round 1. A Fail
returns to Execution through the repair-round prompt, and review narrows from round 2
(`review.md`). After the third failed round the issue moves to `ready-for-human` with the
evidence and a recommended decision.

Classify each Fail:

- **fix in place**: a finite in-contract correction. The original Execution repairs it; habit
  may start a fresh session or a stronger model for it, and that still counts as a round.
- **needs decision**: a product, scope or contract decision is missing. Apply
  `ready-for-human`, pause the affected work and let habit decide.
- **environment blocker**: tools, credentials, platform or shared state prevent a fair
  attempt. Resolve it first; the round does not count.

## Completion

habit squash-merges once the tier's path has passed. Orchestration then:

1. verifies the merged result on the default branch of `origin`;
2. removes only the worktrees and branches it owns that hold no unpreserved work, checks
   `git worktree list` for leftover review worktrees, removes them and runs
   `git worktree prune`;
3. opens one `needs-triage` issue titled `follow-up: <AC ID>` for the findings marked
   `follow-up: yes` that habit kept, only when at least one remains;
4. posts the completion comment on the issue: the merge commit, the cleanup, and the
   follow-up issue link or `no follow-ups`.

A confirmed P0/P1, or a revert of a merged delivery, still opens an environment-improvement
issue (`review.md`).

Rendered from repository-governance at a9eb81d0c41e19c0a024eabb00fd7591d8a0ac1f; change it only through an initialize-repository upgrade (OpenCode `@initialize-repository`, Claude Code `/initialize-repository`).
