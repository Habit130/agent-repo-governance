# Governance model

The language of the governance model that this repository builds: how habit and agents govern habit's GitHub repositories, and how the generator instantiates that model in each one. Every process term here describes governed repositories. Terms follow the newest governance model version in this repository's template store, a draft version included, so a term may describe a rule that a repository on an older version doesn't hold yet. What binds a repository, this one included, is its own `AGENTS.md` and `docs/agents/`.

## People and accounts

**Maintainer**:
habit, the one human in every governed repository. habit decides scope, starts every session, answers escalations and holds every merge.
_Avoid_: the user

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
What a session is authorized to do: Planner, Builder or Reviewer.

**Planner**:
The role that turns ideas, incoming issues and maps into specs and tickets with habit.

**Builder**:
The role that takes one delivery, a ticket or a spec approved for whole-spec delivery, implements and self-verifies it, and carries its PR to the point where habit can merge.

**Reviewer**:
The role that reviews a medium or high PR from a context that didn't write it, and writes the Merge summary once the review is clear.

**Start instruction**:
The text that starts a session, the same in every harness, naming its role, its target and its skills.

**Start request**:
A session's two-part request that habit start another session: one part for habit, and one start instruction to paste. The Reviewer handoff is one.

**Role file**:
The committed file holding one role's detailed workflow, which that role reads at session start.

**Dispatch**:
habit naming a ticket, or a spec approved for whole-spec delivery, in a start instruction and starting its Builder. At medium and high it also covers starting the Reviewer and requesting each review bot the Builder names on a head.

**Escalation**:
A session stopping for habit's decision. Examples: a blocked Builder, a scope change, an unforeseen high, the round cap, an unavailable review bot, a broken governance gate or a denied permission.

**Direct request**:
habit asking a session for a change with no ticket. It makes the session a Builder, which records the request verbatim as an issue.

**Delivery**:
By default, one ticket built by one fresh Builder session on one branch into one PR. A whole-spec delivery builds a spec's tickets in one PR, and a results-comment ticket is delivered with no PR.

**Delivery shape**:
Ticket by ticket or whole spec, chosen by the Planner and approved by habit.

**Mid-session request**:
A session's short request for one thing from habit, after which the session carries on. An escalation is one.

**Final handoff**:
A session's closing message to habit once it has no next step of its own: the conclusion, what habit does next, and whether the session can be closed.

**Dispatch plan**:
The Planner's ordered list of an effort's approved tickets, each with its start instruction and the condition for dispatching it. habit dispatches from it, and only a Planner changes it.

## Work items

**Ticket**:
An issue a Builder can be dispatched on, frozen once published: a `to-tickets` sub-issue, a triaged issue with an agent brief, or a Builder-written issue from a direct request.

**Decision ticket**:
A wayfinder map's child issue. It resolves a decision and is never built.

**Spec**:
The issue describing a build that takes more than one Builder session. `to-spec` makes it, and it is the parent of its tickets.

**Agent brief**:
Triage's comment that turns an incoming issue into a ticket and serves as its contract.

**Results-comment ticket**:
A ticket that changes nothing in the repository and that habit approved to be delivered with no PR. Its results comment completes it.

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
A PR-level AI reviewer that isn't a governed role session, such as the Codex review bot or Copilot code review.

**Codex review bot**:
The PR reviewer that answers only habit's request comment and posts as `chatgpt-codex-connector[bot]`. It is distinct from the Codex harness.

**Copilot code review**:
GitHub Copilot's PR reviewer, which starts only on habit's own request in the browser and posts as `copilot-pull-request-reviewer[bot]`.

**Bot slot**:
One review bot that a tier requires, named by its position, `bot-1` or `bot-2`, never by a bot. Two slots are filled by two different review bots.

**Enabled review bots**:
The ordered list of review bots that habit confirmed for a repository. Its order is the order of preference, and a supported bot left off it is disabled: never requested, awaited or counted.

**Fallback**:
The next enabled review bot filling a bot slot whose first bot was unavailable.

**Waiver**:
habit's approval, in habit's own PR comment, that one named required review or verification goes unmet for one PR at one head. A new head voids it.
_Avoid_: reduction, substitution, skip

**Rerun-only pass**:
A required check that failed on a head and then passed on the same head with nothing repaired. It counts as unrepaired until an issue covers its cause.

**Self-verification**:
The Builder's check before its PR opens. It runs the ticket's verification commands, then a context-free subagent reviews the committed diff and classifies the tier independently.

**Evidence comment**:
The Builder's head-bound PR comment recording the commands run, their results and the before-and-after evidence.
_Avoid_: Self-verification evidence

**Reviewer handoff**:
The Builder's two-part request that habit start a Reviewer: one part for habit, one to paste to the Reviewer.

**Finding**:
One issue that a review raises, rated Important, Nit or Pre-existing.

**Blocking finding**:
An Important finding that is still open. No PR merges with one on its current head.

**Review state**:
Clear, flagged, waived or unavailable, for one review on one head.

**Round**:
Every required review has run on one head, and the Builder has responded.

**Merge summary**:
The plain-language summary of a PR that habit merges on, bound to one head. The Merge handoff follows its terminal copy.
_Avoid_: PR summary

**High-risk report**:
The Merge summary of a high PR. It adds why the PR is high, the one-way-door rehearsal and the steps awaiting habit's go-ahead.

**Merge handoff**:
The final handoff that follows the Merge summary, holding the pinned merge command. It names no next ticket: that comes from the dispatch plan.

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
Local Codex sessions in the ChatGPT app or its bundled CLI. It is distinct from the Codex review bot.

## Repository governance and the generator

**Governance model**:
The one, versioned design of roles, rules and process that governed repositories follow.

**Repository governance**:
One repository's committed governance, instantiated from one governance model version for that repository.

**Governed repository**:
A repository of habit's personal account with a governance record on its default branch, other than the public and private sandbox repositories.

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
A value derived from a repository and confirmed by habit, kept in the governance record: a repository-specific sensitive path, its floor, a required CI check, or the enabled review bots.

**Repository-owned content**:
Governance content written once at Initialize and maintained afterwards by the repository's own PRs.

**Template store**:
The generator's templates, version manifests and change notes, kept in one directory per governance model version.

**Stored form**:
The reversible encoding in which this repository keeps skill copies, templates and fixtures, so that no harness or review bot loads them.

## Versions

**Governance model version**:
An increasing integer naming one released state of what the governance model lands in a repository.

**Draft version**:
The one unreleased governance model version, the highest in the template store. Changes accumulate in it across PRs until its release.
_Avoid_: unpublished model, candidate

**Release**:
Adding a draft version's change note to the default branch. From then on the version is frozen, and the next install makes it the installed version.

**Installed version**:
The highest released governance model version in the template store that the install put on the machine.

**Change note**:
A version's plain-Chinese note for habit: what changes, whether habit must act, and how urgent it is.
_Avoid_: release notes, changelog

**Urgent version**:
A version that fixes a way to break a hard rule, or without which a lagging repository goes wrong with the machine's skills. It upgrades before the repository's next delivery.

**Retired file**:
A generated file that an earlier version wrote and a later version removes at Upgrade.

**Drift**:
Any difference between a repository's governance and what its record's version plus its confirmed values produce.

## The machine

**Machine skill set**:
The skills this repository installs and updates on a machine: the generator plus the skills governance relies on.

**Skill copy**:
A third-party skill that governance relies on, kept in this repository at one recorded upstream commit.

**Personal skill**:
Any other skill on the machine. The install never updates or removes it.

**Install**:
Bringing a machine to the latest state of this repository's default branch: the machine skill set, the machine rules and the links, then the machine check and the governed-repository list.

**Account wizard**:
The one-time setup of a new machine's accounts, which habit runs before its first install.

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
The issue labelled `miss` that records one miss.

**Merge watch**:
The fixed workflow that runs after every merge and, without blocking anything, records misses: a red default-branch CI run, a merged pure revert, and a review missing from the merged head.

## Credentials

**Credential**:
A value that grants access, such as a token, a key or a password.

**Actions secret**:
A credential stored in GitHub for workflows, including environment and Dependabot secrets.

**Exposed credential**:
A credential that reached GitHub in any form, merged or not.

**Rotate**:
To revoke a credential and issue a replacement.

## Verification

**Fixture**:
A prepared input state, such as a repository, recorded GitHub state or a machine home, together with its expected results.

**Stand-in GitHub**:
The recorded GitHub state that suites and scenarios run against in place of real GitHub.

**Scenario**:
A model's run of the generator over one fixture in one harness, checked against the fixture's expected results.

**Sandbox repository**:
A standing repository of habit's personal account used only for live checks. It is not a governed repository.

**Live check**:
Verification against real GitHub, in a sandbox repository.

**End-to-end run**:
A release's Initialize of the public sandbox repository by the releasing commit's generator, followed through to habit's merge and the owner script.

**Release check**:
The CI check in this repository that freezes released governance model versions.
