# PROTOTYPE: the repository governance version 1 writes

Throwaway. Never merged. Asset for
[Prototype the repository governance that version 1 writes into a sample repository](https://github.com/Habit130/agent-repo-governance/issues/35),
on the map [Map: governance model and generator v1](https://github.com/Habit130/agent-repo-governance/issues/4).

**Question.** What does the repository governance that governance model version 1 writes
look like, file by file? Does it read as light, complete and free of duplication when one
delivery walks through it?

**Shape.** The ticket fixes the asset's shape: every file at outline level, plus a
plain-Chinese tour and walkthrough for habit (`TOUR.zh.md`). Neither of the `prototype`
skill's two branches, a clickable logic demo or UI variants, fits that question, so this
follows the ticket.

**Not reopened.** Everything here comes from the closed tickets the issue names. Where the
prototype needed something those tickets don't settle, the gap is listed at the end with the
ticket it would amend.

## The sample repository

`Habit130/tally`, made up: a small public TypeScript command-line time tracker with optional
sync to a hosted API.

Before Initialize it has:

- `package.json` scripts `lint`, `build`, `test`;
- one CI workflow, `.github/workflows/ci.yml`, job `test`, on every PR and every push to
  `main`, no path filters;
- `src/sync/auth.ts`, which stores and refreshes the sync API token;
- `scripts/release.sh`, which publishes to npm;
- `CONTRIBUTING.md` with three rules, sorted at Initialize:
  - "tests never call the real sync API": compatible, carried into `AGENTS.md`;
  - "user-visible CLI changes add a CHANGELOG line": compatible, carried;
  - "squash-merge only": covered by the model, dropped and listed;
  - "maintainers may push small fixes straight to main": conflicts, dropped and listed for
    habit.
- no governance record, so the generator's run is an Initialize.

habit's confirmed values for it: `src/sync/auth.ts` sensitive (authentication, medium
floor), `scripts/release.sh` sensitive with a high floor, required check `test`.

## How files are named here

No harness or review bot may load a prototype file as live instructions. So:

- leading-dot directories become `dot-…` (`dot-github/` is the sample's `.github/`);
- files a harness or bot loads by name get `.outline` appended: `AGENTS.md`, `CLAUDE.md`,
  `BUGBOT.md`, the workflow and the script.

## File index

Class: **F** fixed (generated notice, replaced whole on Upgrade, checked by exact
comparison), **C** confirmed value (kept in the record), **R** repository-owned (written once
at Initialize, never touched by Upgrade). Sizes: the outline here, and an estimate of the
final wording.

| Sample path | Prototype file | Class | Read by, when | Outline | Final, est. |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | `sample-repo/AGENTS.md.outline` | F inside markers, R below | Every session, first; the Codex review bot | 5.8 KB | 8–10 KB |
| `.claude/CLAUDE.md` | `sample-repo/dot-claude/CLAUDE.md.outline` | F inside markers, R below | Claude Code sessions, at start | 0.9 KB | 0.6 KB |
| `docs/agents/planner.md` | `sample-repo/docs/agents/planner.md` | F | Planner, at start | 2.1 KB | 3–4 KB |
| `docs/agents/builder.md` | `sample-repo/docs/agents/builder.md` | F | Builder, at start; Planner for docs PRs | 4.5 KB | 6–8 KB |
| `docs/agents/reviewer.md` | `sample-repo/docs/agents/reviewer.md` | F | Reviewer, at start | 1.6 KB | 2–3 KB |
| `docs/agents/review.md` | `sample-repo/docs/agents/review.md` | F | Builder and Reviewer, at start | 5.0 KB | 7–9 KB |
| `docs/agents/issue-tracker.md` | `sample-repo/docs/agents/issue-tracker.md` | F, repository name substituted | Any session using the tracker | 1.3 KB | 3 KB |
| `docs/agents/triage-labels.md` | `sample-repo/docs/agents/triage-labels.md` | F | `triage`, and labelling | 0.6 KB | 1 KB |
| `docs/agents/domain.md` | `sample-repo/docs/agents/domain.md` | F | Before exploring domain code | 0.5 KB | 1.3 KB |
| `docs/agents/build.md` | `sample-repo/docs/agents/build.md` | R | Builder at start; Planner writing Verification | 0.7 KB | 0.7 KB |
| `.github/PULL_REQUEST_TEMPLATE.md` | `sample-repo/dot-github/PULL_REQUEST_TEMPLATE.md` | F | Builder opening a PR | 0.8 KB | 0.6 KB |
| `.cursor/BUGBOT.md` | `sample-repo/dot-cursor/BUGBOT.md.outline` | F, the one sanctioned copy | Bugbot, each review | 0.8 KB | ≈ AGENTS.md's Code Review Rules, 3 KB |
| `.github/governance/record.yml` | `sample-repo/dot-github/governance/record.yml` | F version and default paths; C `confirmed` | The gate, every PR; the owner script; the generator | 1.2 KB | 1 KB |
| `.github/workflows/governance-gate.yml` | `sample-repo/dot-github/workflows/governance-gate.yml.outline` | F | GitHub, every PR event | 1.5 KB | 4–6 KB of code |
| `.github/governance/owner.sh` | `sample-repo/dot-github/governance/owner.sh.outline` | F | habit, after Initialize and after check changes | 1.4 KB | 4–6 KB of code |

Also written, not as files: the three rulesets and four settings (by `owner.sh`), the triage
and wayfinder labels (by the generator).

Not written: a root `CLAUDE.md`, `AGENTS.override.md`, `.codex/`, harness permission files,
agent definitions, `.dsh/` overlays, hooks, issue templates, skill copies, a delivery
protocol, `GLOSSARY.md`, ADRs.

**What each session reads at start**, estimated final: Builder `AGENTS.md` + `builder.md` +
`review.md` + `build.md` ≈ 25 KB; Reviewer ≈ 19 KB; Planner ≈ 13 KB.

## Checks before showing habit

**Generated notice.** Every F file carries the one-line notice on line 1, or line 2 under
the owner script's shebang. Mixed files say which part it covers: the markers in `AGENTS.md`
and `.claude/CLAUDE.md`, "except `confirmed`" in the record. The PR template's notice is an
HTML comment; the gate reads only lines starting `Risk:` or `Reverts:`, so a body built from
the template still parses. `build.md` carries no notice (R).

**Codex's 32 KiB cap.** The cap counts every project `AGENTS.md` on the path combined; the
global file has its own budget. The sample has one, estimated 8–10 KB final, about 30% of the
cap. Basis: the outline's bullets are already near final length except the tier table, which
grows by about 1.5 KB, and connecting prose. A repository with nested `AGENTS.md` files adds
theirs.

**One home per rule.** Rule, its one home, and the files that only point to it:

| Rule | Home | Pointers only |
| --- | --- | --- |
| Start instruction; one role per session; no role is read-only; direct request makes a Builder | `AGENTS.md` How to start | `builder.md` (direct-request procedure), `planner.md` |
| Hard limits of every agent and each role | `AGENTS.md` Hard limits | role files open with "not repeated here" |
| Talking to habit: Chinese, no code, sender label, two-part start requests, "Waiting on habit" line | `AGENTS.md` Talking to habit | `builder.md` handoff, `planner.md`, `review.md` merge summary |
| Fixed files; confirmed values only on habit's quoted request; governance beats skill text; missing skill stops | `AGENTS.md` Governance files | record header |
| Tier criteria, trusted authors, floors, finding categories, mapping, tier challenge, fixed-content edit is Important, round-2 rules | `AGENTS.md` Code Review Rules | `review.md`, `builder.md` step 6; `BUGBOT.md` restates it (sanctioned copy) |
| Sensitive-path list | `record.yml` | `AGENTS.md`, `BUGBOT.md`, the gate |
| Setting, raising and lowering the tier | `review.md` Setting the tier | `reviewer.md` step 3 |
| Minimum reviews per tier; high extras | `review.md` | `builder.md` step 9 |
| Bot requests, review states, unavailable bots | `review.md` Review bots | `builder.md` step 8, Escalations |
| Answering findings; rounds; cap; re-review; waiting | `review.md` | `builder.md`, `reviewer.md` step 5 |
| Subagent with no conversation context | `review.md` Subagents | `builder.md` step 6, `.claude/CLAUDE.md` (how, in Claude Code) |
| Security review | `review.md` | `reviewer.md` step 7 |
| Merge summary, high-risk report, rules-in-effect check, pinned command, next start instruction | `review.md` Merge summary | `builder.md` step 9, `reviewer.md` Outputs |
| Builder steps, evidence comment, Reviewer handoff, Codex request, syncing, escalations, gate recovery, after merge, pure reverts, re-landing | `builder.md` | `review.md`, `planner.md` (docs PR) |
| Reviewer inputs, steps, outputs | `reviewer.md` | — |
| Entry points, delivery shape, spec and ticket contents, spec label removal, docs PR | `planner.md` | — |
| Claim, dispatch, frozen ticket bodies, tracker commands | `issue-tracker.md` | `builder.md` step 2, `triage-labels.md` |
| PR body shape, `Reverts:` slot | PR template | `builder.md` |
| Build and test commands | `build.md` | ticket Verification |
| What the gate enforces | gate workflow | — |
| GitHub target state | `owner.sh` | — |

Duplicates found and removed while drafting: ticket freezing (was in three files), claiming
and dispatch (two each), the self-verification description (two), the confirmed-values rule
(record header and `AGENTS.md`).

The one remaining copy is `BUGBOT.md`, by decision: Bugbot doesn't read `AGENTS.md`. It is
generated from the same template, and the exact-comparison check holds it identical.

## Small choices made here

Not decided by any ticket; mechanical, open to habit's objection:

- The record, the owner script and the gate: `.github/governance/record.yml`,
  `.github/governance/owner.sh`, `.github/workflows/governance-gate.yml`; check name
  `governance-gate`.
- Markers `<!-- governance:begin v1 -->` and `<!-- governance:end -->`.
- The pure-revert body line `Reverts: <sha>`, as a slot in the PR template.
- `.cursor/**` as a default sensitive path, covering Bugbot's rule file wherever it sits and
  its config.
- "Run as habit" written out as habit's account alias: the pinned merge command and the
  Codex request are `ghm …` commands, since `gh` on habit's machine is the agent account.

## Gaps surfaced, each an amendment to the ticket that decided it

1. **Where the review rules the bots read live.** "How work flows from idea to merged PR"
   puts the tiers, finding categories, mapping and tier challenge in `review.md`; "How one
   canonical policy reaches every harness" puts them in `AGENTS.md`'s Code Review Rules,
   which the Codex review bot reads. One home is needed. Proposed: `AGENTS.md`'s Code
   Review Rules; `review.md` keeps how they're applied.
2. **What `AGENTS.md` holds.** "How work flows from idea to merged PR" lists a flow overview,
   hard limits, the start-instruction rule and routing. Rules that bind every role but
   belong to no role file have no other home: talking to habit, governance files and lag.
   Proposed: two short sections in `AGENTS.md`.
3. **High floors in the gate.** "Which rules are enforced deterministically" has the gate
   check "at least medium" on sensitive paths, while the record holds per-path high floors
   ("How risk tiers gate a change"). Proposed: the gate enforces each matching path's floor;
   a confirmed pure revert stays exempt.
4. **Repository-specific review rules.** The bots read only fixed text: `AGENTS.md`'s Code
   Review Rules and `BUGBOT.md`. A repository rule such as the sample's CHANGELOG line
   reaches Builders and Reviewers through `AGENTS.md`'s repository section, never the bots.
   Proposed: accept for v1. Amends "How the generator turns a repository's state into its
   governance" only by stating it.
5. **The Builder after a medium or high merge.** "How work flows from idea to merged PR" has
   the Builder remove its worktree after merge, and at high run the smoke check and ask the
   go-ahead. At medium and high the Reviewer hands habit the merge command, so nothing tells
   the Builder the PR merged. Proposed: the Builder keeps waiting on the PR until it merges,
   like any other wait. A Builder that can't wait leaves its worktree, which is harmless. At
   high, the Reviewer's message tells habit to say "merged" in the Builder's terminal.
