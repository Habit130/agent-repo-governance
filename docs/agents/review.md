# Review Rules

The detail behind the short Code Review Rules in `AGENTS.md`. Readers: the automated
reviewer, the Orchestration pre-merge check and Acceptance. `delivery.md` owns who reviews
at which tier.

## Findings

Rate every finding P0, P1, P2 or P3, or Pre-existing when the change did not introduce it.
P0 and P1 block the merge; P2, P3 and Pre-existing never block. A review record marks each
non-blocking finding `follow-up: yes` or `follow-up: no` with a reason; the default is `no`
for a style nit and for a finding that is rejected, already covered or fixed. Completion
turns the findings marked `yes` into one follow-up issue (`delivery.md`).

- **P0**: a catastrophic defect introduced by the change with system-wide or broadly
  irreversible impact, such as widespread unrecoverable data loss, a credential exposure
  that enables unauthorized access, or loss of the primary product for nearly all supported
  use, with no reasonable containment before merge.
- **P1**: a concrete defect introduced by the change on a supported path that breaks a core
  operation, corrupts canonical or persisted data, or violates an established security or
  privacy boundary, with substantial impact and no acceptable workaround for the affected
  path.
- **P2**: a defect with limited impact or an acceptable workaround, or a maintainability
  concern that will cost later.
- **P3**: a nit: naming, style the tooling does not enforce, an optional refactor, a
  stronger-test suggestion.
- **Pre-existing**: any defect the change did not introduce, whatever its severity.

An automated P0/P1 blocks once a review session confirms its trigger, impact and evidence,
and falls away when it cannot. An override comment cannot waive a confirmed P0/P1; changing
the boundary takes a new issue, an ADR and a contract version. A review never fails a
delivery against a newly preferred implementation, a stronger test or an unlisted scenario
unless that is a confirmed P0/P1.

## Evidence

- Cite `path:line` for the defect, not a guess from a name.
- State the failure shape: the trigger, the wrong behavior, the impact and the safe path.
  In this repository failure looks like:
  - Documentation: it lies about authority, supported behavior or verification, causing
    a session to take the wrong action.
  - Routing or configuration: it misroutes context or permissions, causing contradictory
    rules, unauthorized writes or a broken delivery path.
- Open every summary with the finding counts, and say plainly when nothing needs fixing.
- Report at most three P3 nits, after everything else; drop what tooling already enforces.

## Risk tiers

A change takes the highest tier any part of it reaches. The tier follows the change, not its
author.

| Tier | The change |
| --- | --- |
| low | a two-way door with a contained blast radius, no sensitive path, and deterministic verification that covers it, such as docs, tests, internal refactors and small fixes |
| medium | reversible user-visible behavior, an interface, a dependency, build or CI configuration, or a shared module |
| high | a one-way door (data migration, destructive operation, release or publish), authorization, privacy or secret handling, production resources, a broad blast radius, or first initialization and upgrades of governance |

### Sensitive paths

A change that touches one is never low. habit confirmed this list at initialization:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/agents/`
- `.github/`

## Rounds

`delivery.md` caps the rounds. From round 2, review only the repair diff and the criteria
whose evidence it changed, raise no finding twice, and flag a recurring bug class so
Execution fixes every instance.

## Acceptance checkout

Acceptance verifies in its own temporary worktree, detached at the exact head, never in the
primary checkout or Execution's worktree:
`git worktree add --detach <temporary path> <head sha>`. After verification it removes that
worktree (`git worktree remove <temporary path>`) and records the removal; Completion clears
any review worktree left behind (`delivery.md`).

## Automated reviewer

Record one state per exact head: **clear** (completed with no P0/P1), **flagged** (completed
with at least one P0/P1, each awaiting a disposition) or **unavailable** (not run, failed or
incomplete).

Codex and Cursor review every PR; request both explicitly on each delivery head.
Request Codex with a PR comment that contains exactly `@codex review`;
a trigger comment is not a review. Only that request writes the trigger literally, because
any comment containing it starts the reviewer, on issues as well as PRs: handoffs, claims,
handbacks, review records, contract and PR bodies and every other issue or PR comment name
the trigger without writing it. The state for a head comes from the `codex-review-state:v1`
marker in Codex's summary comment: the review is complete when its `code_review.commit_sha`
equals the head and its `code_review.status` is `completed`. Severity comes from Codex's
inline comments. A reply asking to create an environment is not terminal. Without the
marker, read the PR's reviews and inline comments for that head. When the review is
unavailable, the low-tier pre-merge check uses a `code-review` subagent and Acceptance
reviews without it. To change the reviewer, edit this section.

Request Cursor with a separate PR comment containing exactly `@cursor review`. The same
request-only trigger rule applies to Cursor: other issue and PR prose names the reviewer
without spelling its trigger. Record both reviewers separately, with the exact head,
request URL, result URL and clear, flagged or unavailable state.

For Cursor, inspect the `Cursor Bugbot` check on the exact head and its linked output,
reviews and inline comments. A completed successful review is clear only after checking
its findings. A neutral result can mean findings, cancellation or an internal error;
inspect the output instead of treating neutral as success. A failed check can represent
findings rather than an execution failure. Completed reviews with P0/P1 are flagged;
completed reviews without P0/P1 are clear. Missing, cancelled, errored or unproven
completion is unavailable. When no check exists, use a review explicitly tied to that
head and showing completion; otherwise record unavailable. Never infer completion from
the request comment or from a review of an older head.

The aggregate state is flagged if either reviewer is flagged, otherwise unavailable if
either is unavailable, otherwise clear. Apply the fallback above to an unavailable
aggregate, and disposition every finding from both reviewers. Reviewer availability
does not replace independent Acceptance for medium or high risk.

Cursor status semantics: https://cursor.com/docs/bugbot#ci-check-statuses.

## Records

Records go on the PR (`delivery.md`). An Acceptance Pass, and a pre-merge check that
recommends merge, end with two next-step blocks: the merge block (Do: squash-merge with the
title `<type>: <subject> (#PR)`, then delete the branch; Read first: the high-tier report when
there is one, the record and the PR) and the completion block (Paste: the completion prompt
listing the findings marked `follow-up: yes`, which habit may trim).

### Pre-merge check

```text
## Pre-merge check: [AC ID] at [head sha]
Checks: [pass | fail | none]. Evidence matrix: [all Pass | gaps]. Automated review: [clear | flagged | unavailable (code-review subagent used)].
Sensitive paths: [none | list]. Scope: [inside | exceeds].
Follow-ups: [each non-blocking finding with follow-up: yes | no and the reason; or none]
Recommendation: [merge | do not merge: blocker]
```

### Acceptance record

```text
## Acceptance: [AC ID] at [head sha], round [r]
Verdict: [Pass | Fail]. Findings: P0 [n], P1 [n], P2 [n], P3 [n], Pre-existing [n].
Checkout: detached worktree at [head sha], removed after verification.
| Criterion | Evidence | Result |
| --- | --- | --- |
| BASE-EVIDENCE | [primary evidence] | [Pass | Fail] |
| CRIT-1 | [primary evidence] | [Pass | Fail] |
Dispositions: [every automated-review finding, confirmed or rejected, with evidence]
Follow-ups: [each non-blocking finding with follow-up: yes | no and the reason; or none]
On Fail: [fix in place | needs decision | environment blocker], then the next-step block with the repair-round prompt.
```

### High-tier report

Acceptance posts it first among its comments, and habit reads it before reviewing. One
screen:

```text
## High-tier report: [AC ID] at [head sha]
Verdict: [Pass | Fail]. Findings: P0 [n], P1 [n], P2 [n], P3 [n], Pre-existing [n].
Why high: [tier reason]
Change:
- [three to five bullets]
Key evidence: [the strongest primary evidence]
Revert path: [how to undo, or why it cannot be undone]
Look here: [at most three path:line spots, each with why]
```

### Environment improvement

A confirmed P0/P1, or a revert of a merged delivery, opens one `needs-triage` issue titled
`env: <cause>`. Orchestration opens it. It links the finding or revert, names the check or
rule that would have caught it, and proposes only: prefer a deterministic check (CI, lint or
test), then a review rule here, then an instruction change. Normal triage and delivery apply
it.
