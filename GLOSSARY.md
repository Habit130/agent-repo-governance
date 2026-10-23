# Repository governance

The language of the governance model that this repository builds: how habit and agents govern habit's GitHub repositories, and how the generator instantiates that model in each one. Every process term here describes governed repositories. This repository runs under its own operating contract, `AGENTS.md` and `docs/agents/`, until its first Initialize moves it onto the model, and until then that contract wins wherever the two differ.

## People and accounts

**Maintainer**:
habit, the one human in every governed repository. habit decides scope, starts every session, answers escalations and holds every merge.
_Avoid_: user

**Maintainer account**:
habit's own GitHub account, which owns every governed repository and is used only by habit.

**Agent account**:
The one GitHub machine account that every agent session acts under. It is a write collaborator on each governed repository.
_Avoid_: bot account

**Trusted author**:
habit or the agent account: an author whose PRs are reviewed in place rather than re-landed.

## Roles and sessions

**Session**:
One agent context in a harness. It holds exactly one role, and its subagents act in that role.

**Role**:
What a session is authorized to do: Planner, Builder or Reviewer. A session started without one is read-only.

**Planner**:
The role that turns ideas, incoming issues and maps into specs and tickets with habit. It writes the repository only for the glossary and ADRs.

**Builder**:
The role that takes one ticket, implements and self-verifies it, and carries its PR to the point where habit can merge.

**Reviewer**:
The role that reviews a medium or high PR from a context that didn't write it, and writes the Merge summary once the review is clear.

**Start instruction**:
The text that starts a session, the same in every harness, naming its role, its target and its skills.

**Role file**:
The committed file holding one role's detailed workflow, which that role reads at session start.

**Dispatch**:
habit naming a ticket in a start instruction and starting its Builder. At medium and high it also covers starting the Reviewer, and at high requesting the Codex review bot on each head the Builder names.

**Escalation**:
A session stopping for habit's decision. Examples: a blocked Builder, a scope change, an unforeseen high, the round cap, an unavailable review bot, a broken governance gate or a denied permission.

**Direct request**:
habit asking a session for a change with no ticket. It makes the session a Builder, which records the request verbatim as an issue.

**Delivery**:
One ticket built by one fresh Builder session on one branch into one PR. A whole-spec delivery builds a spec's tickets in one PR.

**Delivery shape**:
Ticket by ticket or whole spec, chosen by the Planner and approved by habit.

## Work items

**Ticket**:
An issue a Builder can be dispatched on, frozen once published: a `to-tickets` sub-issue, a triaged issue with an agent brief, or a Builder-written issue from a direct request.

**Decision ticket**:
A wayfinder map's child issue. It resolves a decision and is never built.

**Spec**:
The issue describing a build that takes more than one Builder session. `to-spec` makes it, and it is the parent of its tickets.

**Agent brief**:
Triage's comment that turns an incoming issue into a ticket and serves as its contract.

**Risk note**:
A ticket's statement of a risk that the diff won't show.

## Risk and review

**Risk tier**:
Low, medium or high. The change sets it, not its author, and it decides which reviews the change must pass before habit merges it.
_Avoid_: risk level

**Effective tier**:
The tier in force on a PR's current head, as its `Risk:` line declares it.

**One-way door**:
A change or step that a revert can't undo, such as a data migration that has run or a release that has been published.

**Sensitive path**:
A path whose change is at least its floor, medium by default or high where habit set it, whoever the author is.

**Sensitive-path list**:
The one committed list of sensitive paths and their floors, held in the governance record and read by the governance gate.

**Review bot**:
A PR-level AI reviewer that isn't a governed role session, such as Bugbot or the Codex review bot.

**Codex review bot**:
The PR reviewer that answers only habit's request comment and posts as `chatgpt-codex-connector[bot]`.
_Avoid_: Codex, alone

**Self-verification**:
The Builder's check before its PR opens. It runs the ticket's verification commands, then a context-free subagent reviews the committed diff and classifies the tier independently.

**Self-verification evidence**:
The Builder's head-bound PR comment recording the commands run, their results and the before-and-after evidence.

**Reviewer handoff**:
The Builder's two-part request that habit start a Reviewer: one part for habit, one to paste to the Reviewer.

**Finding**:
One issue that a review raises, rated Important, Nit or Pre-existing.

**Blocking finding**:
An Important finding that is still open. No PR merges with one on its current head.

**Review state**:
Clear, flagged or unavailable, for one review on one head.

**Round**:
Every required review has run on one head, and the Builder has responded.

**Merge summary**:
The plain-language summary of a PR that habit merges on, bound to one head. Its terminal copy ends in the pinned merge command.
_Avoid_: PR summary

**High-risk report**:
The Merge summary of a high PR. It adds why the PR is high, the one-way-door rehearsal and the steps awaiting habit's go-ahead.

**Pinned merge command**:
habit's merge command, bound to the head the Merge summary describes, so a later push makes it fail.

**Pure revert**:
A PR that exactly undoes one merged squash commit and nothing else, as the governance gate confirms.

**Re-land**:
A Builder redoing an outside PR's change on its own branch, crediting the original author.

## Enforcement

**Governance gate**:
The fixed required check in every governed repository. It enforces the `Risk:` line, sensitive-path floors and the author rule from the PR itself, and confirms pure reverts.

**Owner script**:
The committed script that habit runs as the maintainer account to apply a governed repository's rulesets and settings.

## Policy and harnesses

**Canonical policy**:
`AGENTS.md` and `docs/agents/`: the harness-neutral policy that every harness reads.

**Harness translation**:
A file that only one harness or review bot reads. It translates the canonical policy into that tool's mechanics and adds no rule.

**Codex harness**:
Local Codex sessions in the ChatGPT app or its bundled CLI.
_Avoid_: Codex, alone

## Repository governance and the generator

**Governance model**:
The one, versioned design of roles, rules and process that governed repositories follow.

**Repository governance**:
One repository's committed governance, instantiated from one governance model version for that repository.

**Governed repository**:
A repository of habit's personal account with a governance record on its default branch, other than the sandbox repository.

**Generator**:
The user-invoked skill, `govern-repository`, that turns the governance model plus a repository's current state into that repository's governance.

**Initialize**:
The generator mode for a repository with no governance record. Anything already there is current state to carry or replace.

**Upgrade**:
The generator mode for a repository whose record names an older governance model version than the installed generator.

**Repair**:
The generator mode for a repository whose record names the installed version. It finds drift and restores it.

**Governance record**:
The committed file naming the governance model version that a repository's governance came from. It holds the repository's confirmed values and its sensitive-path list.

**Fixed content**:
Governance content identical in every governed repository at one governance model version. Only the generator changes it.

**Confirmed value**:
A value derived from a repository and confirmed by habit, kept in the governance record: a repository-specific sensitive path, its floor, or a required CI check.

**Repository-owned content**:
Governance content written once at Initialize and maintained afterwards by the repository's own PRs.

## Versions

**Governance model version**:
An increasing integer naming one released state of what the governance model lands in a repository.

**Change note**:
A version's plain-Chinese note for habit: what changes, whether habit must act, and how urgent it is.
_Avoid_: release notes, changelog

**Urgent version**:
A version that fixes a way to break a hard rule, or without which a lagging repository goes wrong with the machine's skills. It upgrades before the repository's next delivery.

**Drift**:
Any difference between a repository's governance and what its record's version plus its confirmed values produce.

## The machine

**Machine skill set**:
The skills this repository installs and updates on a machine: the generator plus the skills governance relies on.

**Personal skill**:
Any other skill on the machine. The install never updates or removes it.

**Install**:
Bringing a machine to the latest state of this repository's default branch: the machine skill set, the machine rules and the links, then the machine check and the governed-repository list.

**Installed state**:
The machine's record of the commit it installed and the managed skills' content.

**Machine check**:
The read-only check of a machine's skills, rules, links and identity.

## Measurement

**Miss**:
Governance letting through something its rules should have stopped, found after the step that should have caught it: an escape or a process miss. An outside change, such as a harness update, that breaks a governance run is a miss too.

**Escape**:
A problem that got past governance. Examples: a reverted PR, a red default-branch CI run after a merge, a bug traced to a merged PR, or a credential exposed, merged or not.
_Avoid_: incident

**Process miss**:
A governance rule that wasn't followed, and that nothing caught before the merge.

**Miss record**:
The issue labelled `miss` that records one miss. Its `retro` handles it, not triage.

**Merge watch**:
The fixed workflow that runs after every merge and, without blocking anything, records misses: a red default-branch CI run, a merged pure revert, and a review missing from the merged head.

## Credentials

**Credential**:
A value that grants access, such as a token, a key or a password.
_Avoid_: secret, alone

**Actions secret**:
A credential stored in GitHub for workflows, including environment and Dependabot secrets.

**Exposed credential**:
A credential that reached GitHub in any form, merged or not.

**Rotate**:
To revoke a credential and issue a replacement.

## Verification

**Fixture**:
A prepared input state, such as a repository, recorded GitHub state or a machine home, together with its expected results.

**Scenario**:
A model's run of the generator over one fixture in one harness, checked against the fixture's expected results.

**Sandbox repository**:
A standing repository of habit's personal account used only for live checks. It is not a governed repository.

**Live check**:
Verification against real GitHub, in a sandbox repository.
