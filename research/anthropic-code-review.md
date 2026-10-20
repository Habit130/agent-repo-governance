# Anthropic's published code-review practice

**Question.** What does Anthropic's published code-review practice consist of, as its primary
sources state it?

**Ticket.** Habit130/agent-repo-governance#5 (wayfinder:research). **Compiled.** 2026-10-20.
All sources were accessed on 2026-10-20 (America/Los_Angeles).

## How to read this

- Every fact carries a source key such as `[BLOG]`; the key maps to a full URL and an access date
  in **Sources**.
- **Primary** means an Anthropic-published page: the claude.dev developer blog, the Claude Code
  documentation, claude.com articles, Anthropic Engineering, or the Claude Help Center. The only
  **secondary** item referenced is a post on X, and it is marked as secondary and is used only as
  already quoted by `[BLOG]`.
- The claude.dev page's title is "How the Claude Code team does code review"; the ticket's Cover
  calls it "Solving code review at Anthropic", and its URL slug is
  `solving-code-review-at-anthropic`. `[BLOG]`
- The sources describe three different scopes. They are kept separate here because the sources
  keep them separate:
  1. The Claude Code team's own flow, described in the first person by team members `[BLOG]`.
  2. The public Code Review product, `/code-review`, and the security-review features
     `[CR-DOCS] [LOCAL] [SEC-SUPPORT]`.
  3. Anthropic Security Engineering's software-development-lifecycle controls `[SEC-SDLC]`.
- Statements are grouped and quoted, not evaluated. Where two sources state different things,
  both statements are recorded.
- The eight numbered sections below are the findings, grouped by the Cover's items; **Open gaps**
  and **Sources** follow them.

## 1. Review layers and their order

`[BLOG]` describes a change as passing through multiple layers rather than one gate:

> "A typical change, from an engineer's laptop (or a Claude session in Slack), goes through
> multiple layers of code review." `[BLOG]`

It also states that most review now happens before a pull request exists:

> "Most review now happens before a PR exists." `[BLOG]`

and that review moved earlier in time:

> "Now, review runs continuously, more like spellcheck while you write." `[BLOG]`

### 1.1 The layers named in the post's prose

The post numbers seven sections. In its own order:

| # | Layer | What the source says happens | Who or what reviews | Source |
| - | ----- | ---------------------------- | ------------------- | ------ |
| 1 | Verification before the PR | Claude is given something it can run (tests, a build, a screenshot against the design) and asked to show the output; a subagent reviews the diff with fresh context; internal skills hunt bugs, simplify the diff, and check behavior end to end; UI changes are checked against design guidelines | The author-directed Claude, a fresh-context subagent, and internal skills | `[BLOG]` |
| 2 | AI review on every PR | Every PR gets a Claude review before a person looks; it reads the diff against the whole repo and the PR's stated intent and asks whether the change solves its problem, fits the system, or breaks something else; on bug fixes it looks for the root cause | Claude review agents | `[BLOG]` |
| 3 | Security review that can block | Security gets its own automated review; a PR cannot merge while any finding from the bug review or the security review is still open | Automated security review | `[BLOG]` |
| 4 | Automated checks that block | Lint, type checks, tests on every platform, and a build; "A typical CLI pull request may run dozens of checks before anyone looks at it" | CI | `[BLOG]` |
| 5 | Human approval, scaled by risk | A classifier assigns a risk tier; the tier sets how many human approvals are required | People, with classifiers setting the tier | `[BLOG]` |
| 6 | Merge queue, flags and a gradual release | The merge queue re-runs every check against main with the change applied; new behavior ships behind a flag to Anthropic employees first; public releases go to `latest` before `stable` | The merge queue and release process | `[BLOG]` |
| 7 | Fast detection, fast rollback | Flags turn off without a deploy; Claude Code has a weekly on-call rotation; incident reviews ask which layer should have caught the issue | The author, on-call, and the revert and incident dashboards | `[BLOG]` |

The public counterparts of the AI-review and security-review layers are the managed Code Review
service (or the local `/code-review` command) and `/security-review` or the security-review GitHub
Action. `[CR-DOCS]` `[LOCAL]` `[SEC-SUPPORT]`

### 1.2 The order stated in the post's figures

The post's markdown rendition includes the figure descriptions. The layer figure lists
six layers, in this order:

> "Six layers stacked from top to bottom: verification, required CI, AI review, security review,
> human approval, and merge queue plus flags." `[BLOG]`

The "life of a change" figure describes the sequence as:

> "Before the pull request, the work is verified. On every pull request: required CI, Claude code
> review and security review, all automated, then a risk-based approval where a person decides.
> Then the merge queue, and after the merge a feature flag used internally first, a gradual
> release, and a last step to watch, fix forward or roll back." `[BLOG]`

The post's prose puts AI review (2) before automated checks (4); the figures put required CI
before AI review. The post does not state whether those two layers run in that sequence or in
parallel.

### 1.3 Who or what reviews, by layer

- **Before the PR.** The post says Claude is asked "to show the output instead of saying it's
  done", and that "a subagent reviews the diff with fresh context". It also says many engineers
  run "a few internal skills: one hunts for bugs, one simplifies the diff, and one checks the
  behavior end to end." `[BLOG]`
- **On the PR, AI review.** The post: "Every pull request gets a Claude review before a person
  looks." `[BLOG]` The public service is described as a managed service on Anthropic
  infrastructure: "Several agents read each change alongside the surrounding code, looking for
  issues such as logic errors, security vulnerabilities, or broken edge cases. A verification
  step checks findings against the code before they're reported." `[CR-DOCS]`
- **On the PR, local review.** `/code-review` "runs as a background subagent with its
  own context window"; with no target it reviews the branch's commits ahead of upstream plus
  uncommitted changes; effort levels trade coverage for confidence; it reports findings as text,
  and host applications can receive a findings list. `[LOCAL]`
- **On the PR, security review.** The post says security "gets its own automated review too", and
  that a PR cannot merge while any finding from either review is open. `[BLOG]` The public
  `/security-review` command and the security-review GitHub Action are the productized options;
  the Action "Triggers automatically when new pull requests are opened", "Applies customizable
  filtering rules to reduce false positives", and "Posts inline comments on the PR with identified
  concerns and recommended fixes." `[SEC-SUPPORT]` The in-session security-guidance plugin runs
  three checks: a deterministic pattern match on each file edit, a background model review at the
  end of each turn, and a deeper agentic review on each commit or push Claude makes; it "does not
  ask the same Claude instance that wrote the code to grade itself", and "None of the layers block
  writes or commits." `[SEC-GUIDANCE]`
- **On the PR, CI.** The post lists "lint, type checks, tests on every platform, and a build."
  `[BLOG]`
- **On the PR, human approval.** The post says human responsibility remains for direction,
  risky code, architecture, reading evidence, and owning the outcome. `[BLOG]` Fiona Fung, Director
  of Engineering for Claude Code and Claude Cowork, states: "Claude handles all the style and
  linting, PR feedback requests, catching bugs and fixing them before a full commit, and adding
  tests. Where we still definitely want a human is expertise." `[ORG]`
- **Merge and after.** The merge queue re-runs checks; flags and staged releases provide the
  rollout; the author, on-call, and dashboards notice bad merges; flags and reverts undo them.
  `[BLOG]`

### 1.4 The public service's four stages

The public Code Review documentation describes four stages:

1. "**Find**: several agents examine the diff and the surrounding code in parallel."
2. "**Verify**: a verification step checks the candidate findings against the code and filters out
   false positives."
3. "**Rank**: the findings that remain are deduplicated and ranked by severity."
4. "**Post**: the review posts its results on the pull request." `[CR-DOCS]`

The same page states that "A review never approves or blocks the pull request, so the decision to
merge stays with your team", that access is read-only and "a review doesn't push commits", and
that a review "works from reading the diff and the surrounding code, without building or running
your code." `[CR-DOCS]`

## 2. Finding categories; how findings are generated, verified, filtered, posted and answered

### 2.1 Categories

The internal reviewer tags each finding with one of three labels:

> "Each is tagged Important, Nit, or Pre-existing, so a bug the PR didn't introduce doesn't look
> like the author's fault." `[BLOG]`

The public product uses the same three labels, with these definitions:

| Marker | Severity | Meaning |
| ------ | -------- | ------- |
| 🔴 | Important | "A bug that should be fixed before merging" |
| 🟡 | Nit | "A minor issue, worth fixing but not blocking" |
| 🟣 | Pre-existing | "A bug that exists in the codebase but wasn't introduced by this PR" |

Source: `[PR-DOCS]`.

The public service also has review levels, which are depth settings rather than finding
categories: "**Quick**: a lighter pass. The fastest level, at the lowest cost. **Standard**:
balanced depth, speed, and cost. The default level. **Deep**: the most thorough pass. Takes the
longest and costs the most." `[CR-DOCS]` The general-availability announcement states that
"Admins choose Quick, Standard (default), or Deep for each repository." `[GA]`

By default, the public service "focuses on correctness: bugs that would break production, not
formatting preferences or missing test coverage." `[CR-DOCS]` The post says findings "that are
only about style, diagnostics, or cleanup get dropped" before posting. `[BLOG]` The local
`/code-review` report can carry "a category tag such as `correctness`" in host applications.
`[LOCAL]`

### 2.2 Generation

The post: "Several agents look for bugs at the same time." `[BLOG]` Anthropic's Deputy CISO adds
that "multiple agents automatically review" a PR and that "Each review agent is designed and
scoped to a specific, narrow focus and leverages RAG for additional context and memory
surrounding past incidents." `[SEC-SDLC]` The public announcement describes the same parallel
structure: "When a PR is opened, Code Review dispatches a team of agents. The agents look for bugs
in parallel." `[ANNOUNCE]` The documentation's **Find** stage is "several agents examine the diff
and the surrounding code in parallel." `[CR-DOCS]`

### 2.3 Verification

The post says findings are verified before humans see them:

> "Findings get verified by other agents before humans review them. Several agents look for bugs
> at the same time. Then a separate group votes on each finding, and it only gets posted if
> enough of them agree it's real." `[BLOG]`

The security article states a proof requirement: "we've gained confidence in the findings by
requiring the agents to write a proof that their finding is valid." `[SEC-SDLC]` The public
documentation's **Verify** stage "checks the candidate findings against the code and filters out
false positives." `[CR-DOCS]`

### 2.4 Filtering

The post names the filter classes and says the filters were tested:

> "Findings that are only about style, diagnostics, or cleanup get dropped. We A/B tested those
> filters on our own PRs before keeping them." `[BLOG]`

`REVIEW.md` is the documented per-repository review-instruction mechanism. It can redefine
severity, "cap the nits", list paths or classes to skip, and require evidence before a class of
finding is posted.
The documentation's example sets "Report at most five Nits per review", does not report "Anything
CI already enforces: lint, formatting, type errors", generated files under `src/gen/`, or `*.lock`
files, and requires "a `file:line` citation in the source, not an inference from naming."
`[CUSTOMIZE]`

### 2.5 Posting

The internal reviewer posts inline comments sorted by severity. `[BLOG]` The public service posts
"inline comments on the lines concerned, ranked by severity, with a summary and a check run on the
pull request." `[CR-DOCS]` The check run is named **Claude Code Review**; its details list findings
in a table sorted by severity; findings that could not be posted inline appear as annotations;
and the check run "never concludes as a failure, so a finished review doesn't fail a required
check." `[PR-DOCS]` When a finding carries recorded reasoning, it has a collapsed **Why this was
flagged** section. `[PR-DOCS]` The check run's last line is machine-readable, and the docs show
parsing the severity counts from it to gate a merge in another CI job. `[PR-DOCS]`

When the public reviewer finds nothing, "the check run's title reads **Code review found no
issues**, and Claude posts the same short note on the pull request." `[CR-DOCS]`

### 2.6 Answering

The post states the internal rule as:

> "Every finding has to be answered. You either fix it or resolve the thread with a reason."
> `[BLOG]`

The post adds that "Often an agent picks up the fix overnight, so the author comes back to a PR
that's already been through another round." `[BLOG]`

The public product's default rule is:

> "You can merge without responding to a finding, unless your repository's own rules require it."
> `[PR-DOCS]`

To clear a finding, a person resolves the thread or pushes a fix; "Replying alone doesn't dismiss
a finding"; a later review reads replies on earlier findings and can resolve the thread or post
one follow-up reply. `[PR-DOCS]` A review triggered by a new push "resolves its earlier thread when
it judges the issue fixed." `[CR-DOCS]` Comment commands start a review: `@claude review` starts a
single review, `@claude review always` also subscribes the PR to reviews on later pushes, and
`@claude review once` is the same as the first. They must be top-level comments from a person with
write, maintain, or admin permission; "comments from bots don't start reviews." `[PR-DOCS]`
Automatic reviews skip draft PRs and PRs from forks. `[PR-DOCS]`

## 3. Risk tiers, classification and approvals

### 3.1 The tiers

The post gives this table:

| Risk | Examples | Human approvals |
| ---- | -------- | --------------- |
| Low | "Docs, copy, internal-only features, additive changes behind a flag" | "None required once automated review and security checks are green" |
| Medium | "Ordinary product changes, and changes to sensitive areas such as caching, the auto-updater, or system prompts" | "One person" |
| High | "The highest-risk code, plus a small set of paths that always need two people" | "Two people" |

Source: `[BLOG]`.

### 3.2 Who or what classifies a change

The post states the rule and the mechanism:

> "The change sets the tier, not the author. A classifier reads the change and picks its risk
> tier. A second classifier asks whether this particular change needs another person even when
> its tier says it doesn't. Some paths always need a person, anything owners have listed as
> sensitive and any CI workflow file." `[BLOG]`

The two path categories it names are owner-listed sensitive paths and CI workflow files. `[BLOG]`
It also states that the high tier includes "a small set of paths that
always need two people" without listing them. `[BLOG]` Its adoption guidance names paths to keep
under a person: "Use CODEOWNERS and branch protection so auth, billing, CI and release workflows,
and installers always need a person." `[BLOG]`

Anthropic Security Engineering describes a separate, organization-level control: "We tier our
codebase by risk, and make deliberate decisions on what parts to automate. Entire codebases have
strict human approval processes." `[SEC-SDLC]` That article does not define the tiers or list the
codebases. Its planning-stage project security review (PSR) also contains a risk judgment: "Once we
gained confidence that Claude was accurate in assessing risk, we allowed teams to approve their
own project, if Claude deemed the launch low enough risk." `[SEC-SDLC]`

Anthropic Engineering's source-control article describes approval constraints in the internal
review tool: "the code review tooling we built can express complex semantic constraints on
approvals, which lets us differentiate simple things like comment-only changes from sensitive
logical changes, so that human reviewers can focus on the most consequential changes." `[SCION]`

### 3.3 Trusted authors and who can fill a human slot

> "Only authors on the repo's trusted list get the lighter paths, mostly the team that owns it.
> Everyone else needs a second person to approve. An agent's approval never counts as a person's,
> either. Automated review can clear a low-risk change, but it can't fill a slot that calls for a
> human." `[BLOG]`

### 3.4 The person behind an agent-written change

> "Whoever prompted the change is on the hook for it. On an agent-written PR, the person directing
> the agent counts as one of the required reviewers, the same as if they'd typed the code
> themselves." `[BLOG]`

### 3.5 What an approval covers

> "An approval covers one specific commit. If new commits land that the system can't vouch for,
> like an agent's push or a merge someone resolved by hand, the approval has to be given again."
> `[BLOG]`

The post's adoption guidance repeats the practice as "dismiss approvals on new commits." `[BLOG]`

### 3.6 Low-risk changes that merge on automated checks

The post's closing section states:

> "Our own repos go further, letting owners decide which low-risk changes merge on automated
> checks alone, and that line keeps moving." `[BLOG]`

The public product does not approve or block:

> "A review never approves or blocks the pull request, so the decision to merge stays with your
> team." `[CR-DOCS]`

The research-preview announcement states: "It won't approve PRs — that's still a
human call". `[ANNOUNCE]` The post quotes that announcement's wording as "approving a pull request
is still a human call; the product posts findings, not approvals." `[BLOG]`

### 3.7 Where humans still review

The post lists the responsibilities it says remain with people:

- "**Deciding whether to build it.** Direction, taste and scope. One team that declared its review
  bottleneck solved still kept human review for changes from outside the team, so someone asks
  “should we even do this?”"
- "**Reviewing risky code** such as billing, the auto-updater and CI workflows."
- "**Reviewing architecture** that sets a pattern others will copy."
- "**Reading the evidence.** Test output, the command that ran and what it returned, a screenshot,
  the reviewer's findings. If you can't say what the checks would miss, ask for a real review
  rather than a quick approval."
- "**Owning the outcome.** A person is accountable for every change that ships, whoever typed it."
  `[BLOG]`

Fiona Fung describes human review as focused on domain expertise: "The new norm is human
review where it matters: for legal review, I always want my legal partner involved in risk
tolerance. For trust boundaries and security-sensitive code, I want the domain experts. Product
managers and designers also need to be involved with product sense and taste." `[ORG]`

### 3.8 Approval logging, sampling and shadow mode

Anthropic Security Engineering describes these controls:

- "Every approval is logged with the signals and reasoning behind it, and a risk-weighted sample
  is reviewed by humans." `[SEC-SDLC]`
- "Another round of testing focuses on invariants like “user A can never read user B’s data,” and
  triggers additional manual reviews." `[SEC-SDLC]`
- "**Shadow mode** for all new AI reviewers. New agents post comments for human approval until
  trust is earned. Our team also “red teams” them and tries to insert malicious changes."
  `[SEC-SDLC]`
- "**Sampling** a percentage of all automated approvals." `[SEC-SDLC]`
- "**Routing every agent action to the SIEM.** Every automated approval, tool call, and
  agent-to-agent message is logged with the signals it used and lands in our SIEM, so any decision
  is attributable and auditable after the fact." `[SEC-SDLC]`

## 4. Required checks, merge queue, flags, release channels, detection and rollback

### 4.1 Required checks

The post says the automated checks are "The usual: lint, type checks, tests on every platform, and
a build", and that a CLI PR may run "dozens of checks" before a person looks. `[BLOG]` The PR
template "asks how the change was tested and how to undo it. Claude can fill that in, but the
person who asked for the change signs off on it." `[BLOG]` The post's adoption list says to
"Require CI, and add “Testing”, “Risk” and “How to revert” to your PR template." `[BLOG]`

The public service can be set, per repository, to review "once when a pull request opens, after
every push, or only on request"; a person with write access can also comment `@claude review`.
`[CR-DOCS]`

### 4.2 Merge queue

> "The merge queue re-runs every check against main with the change applied, so two PRs that pass
> separately can't combine into a broken main." `[BLOG]`

Anthropic Engineering describes the monorepo's arrangement: "A proper merge queue,
for example, doesn't make much sense at agent scale. What does CI even mean when hundreds or even
thousands of changes can merge while tests are running? We haven't been able to effectively
replicate the industry standard of a global repository lock on the merge queue, so instead, we've
invested in post-merge and pre-deploy automated testing. This does mean that concurrent changes
can conflict, but Claude can typically fix these conflicts faster than humans can even identify
them." `[SCION]`

The post states: "Claude Code lives in its own repository, separate from the monorepo." `[BLOG]`
The source-control article describes the monorepo and Scion. Neither source reconciles the two
statements.

### 4.3 Flags and release channels

> "New behavior usually ships behind a flag to Anthropic employees first, and our heavy use often
> surfaces regressions before users do. Public releases go to the `latest` channel first. The
> `stable` channel trails it." `[BLOG]`

The post also lists "Use a merge queue, feature flags, internal use first, staged releases and
one-step rollback" in its adoption guidance. `[BLOG]`

### 4.4 Detection

> "Noticing a bad merge still depends on the author and on-call as well as the revert and incident
> dashboards. We don't yet have circuit breakers that tighten approval when those numbers move;
> engineers here want them before more code moves to zero-human merges." `[BLOG]`

> "Flags turn off without a deploy. Claude Code has a weekly on-call rotation, and incident
> reviews ask which layer should have caught the issue." `[BLOG]`

The source-control article describes "Slack channels where we tasked Claude with being obsessively
focused on the health of a single component", called "superfans", including "an Antique merge
queue superfan." `[SCION]`

### 4.5 Rollback and post-incident handling

The post's rollback statements are the flag switch, reverts, and staged releases: "Everything is
reversible. Flags, reverts and staged releases undo most mistakes in minutes." `[BLOG]` It also
states: "If you land a small or medium change and something still goes wrong, it's a team norm
that you usually fix it." `[BLOG]`

Anthropic Security Engineering describes a deploy-stage gate and a limit on automated response:

- Staging includes "external pentesting for major launches and periodic DAST scans", and the team
  is "implementing continuous AI-powered DAST scans in our staging environment." `[SEC-SDLC]`
- For production alerts, Claude reviews logs, root-causes, writes a post-mortem, and in some cases
  writes a fix. "What this agent can't do is deploy the fix automatically. It's a single-purpose
  system account agent with three permissions: it can write new docs, post in company channels,
  and access production logs. The fix either needs to come from a separate agent-human reviewer
  system." `[SEC-SDLC]`
- An incident-response agent once asked another Claude instance to push a fix; "This was caught at
  a human review gate as designed." `[SEC-SDLC]`

### 4.6 Speed

The general-availability announcement says "Most reviews now finish about 3x faster (~20 minutes
down to 6-10 minutes) compared to during preview." `[GA]` The research-preview announcement said
"Based on our testing, the average review takes around 20 minutes." `[ANNOUNCE]`

## 5. What `CLAUDE.md` and `REVIEW.md` hold, and the PR template fields

### 5.1 `CLAUDE.md`

The post defines the file and what it holds:

> "`CLAUDE.md` tells Claude what the project is: the stack, the conventions, the goals and the
> non-goals. Every review loads it, so in a large codebase we keep it short and point to other
> docs from there. The reviewer also flags code that breaks a convention in it, and changes that
> make a line in it out of date." `[BLOG]`

The documentation describes `CLAUDE.md` as project instructions that Claude Code reads for every
task, "reviews included"; Code Review "reads them as project context and flags changes that
violate them." `[CUSTOMIZE]` It reads the root `CLAUDE.md` and the `CLAUDE.md` files in the parent
directories of each changed file; a subdirectory's file is read when the PR changes a file under
that path. `[CUSTOMIZE]` The memory documentation adds that `CLAUDE.md` files "give Claude
persistent instructions" and that "Claude treats them as context, not enforced configuration."
`[MEMORY]`

Anthropic Security Engineering says secure-coding guidance is encoded in these files: "At
Anthropic, those guidelines are encoded in CLAUDE.md files and references to org-wide skills so
the code follows these best practices the minute it's generated." It also says its team "started
with a CLAUDE.md file that instructs the agent to run /security-review as a final step before
opening a PR." `[SEC-SDLC]`

### 5.2 `REVIEW.md`

The post's description:

> "`REVIEW.md`, written by code owners, tells the reviewer what matters in their part of the code.
> We check separately whether the reviewer actually follows it. The good ones are short. They say
> what failure looks like in that repo (for docs it's “it lies,” for config it's “it misroutes”),
> cap the nits, list paths to skip, and ask for a file and line as evidence instead of a guess
> from a name. They also ask for a summary that starts with a count and says plainly when there's
> nothing to fix." `[BLOG]`

The documentation adds:

- `REVIEW.md` is a file at the repository root; a subdirectory `REVIEW.md` adds checks for changes
  under that path, on top of the root file. `[CUSTOMIZE]`
- "The agents that find issues and the agents that verify them receive its contents as your
  repository's review instructions, alongside Code Review's default review guidance. The step that
  writes the final review consults it before settling severity and writing the summary."
  `[CUSTOMIZE]`
- It is read from the PR's base branch or the default branch, "never from the pull request's own
  changes." `[CUSTOMIZE]`
- The page says: "Keep `REVIEW.md` on your default branch and protect that branch. When a review
  reads the copy on a protected default branch, the first row of the table below, it honors these
  instructions from the root file: Lowering a finding's severity; Excluding paths, files, or
  classes of issue; Capping nit comments." It then defines what counts as protection: "A ruleset
  counts when it restricts updates or requires pull requests with at least one approval. If it
  requires pull requests, it must also dismiss that approval on a new push or require the approval
  to come after the last push." `[CUSTOMIZE]`
- The managed service reads both `CLAUDE.md` and `REVIEW.md`; the local `/code-review` command
  "reads your `CLAUDE.md` files and not `REVIEW.md`." `[CUSTOMIZE]` `[LOCAL]`

The documented example `REVIEW.md` includes a definition of what Important means ("Reserve
Important for findings that would break behavior, leak data, or block a rollback"), a nit cap
("Report at most five Nits per review"), a do-not-report list (CI-enforced checks, generated
files, lockfiles, test-only code), and always-check rules (integration tests for new API routes,
no email addresses or user IDs in logs, queries scoped to the caller's tenant). `[CUSTOMIZE]`

The post says the team fixes recurring review comments at the source: "in the skill, with a lint
rule, or with updates to instructional files such as" `CLAUDE.md` and `REVIEW.md`. `[BLOG]`

### 5.3 PR template fields

The post's description of its own PR template names two fields: "how the change was tested" and
"how to undo it." `[BLOG]` The adoption section names three fields to add: "Testing", "Risk" and
"How to revert." `[BLOG]` The post does not reproduce the internal template. It states that Claude
can fill the template in, but "the person who asked for the change signs off on it." `[BLOG]`

## 6. Round caps, re-review scope and other convergence controls

### 6.1 The internal convergence problem

The post states the failure mode, the measurement, and the changes made:

> "An agent author and an agent reviewer can keep each other busy indefinitely. One CLI PR went
> through more than fifty rounds of review and fixes overnight before its author stopped it."
> `[BLOG]`

> "When we ran git blame on what the reviewer kept flagging, about 59% of it was code that had
> been there since the reviewer's first pass. The reviewer was rarely finding new bugs, it was
> finding a few more old ones each round." `[BLOG]`

> "We made it worse ourselves. We'd gotten used to running several rounds by default, since each
> pass catches something new. This can be worthwhile on a risky change, but not on every PR. The
> team now tracks rounds-to-pass alongside recall, and changed re-review:" `[BLOG]`

The four changes it lists are:

> "**A round cap.** After three rounds, the reviewer asks the author to step back and reconsider
> the approach." `[BLOG]`
>
> "**Diff-only re-review** after the first few passes." `[BLOG]`
>
> "**Flag the class of bug,** so the author fixes every instance, not one line." `[BLOG]`
>
> "**No repeats** of findings already posted." `[BLOG]`

It adds that "Review agents also run nightly over existing code, helping us catch old bugs before
they show up somewhere else." `[BLOG]`

The post's convergence figure reports: "pull requests passing after one review and fix round rose
from 65% to 78%; pull requests needing five or more rounds fell from 8.9% to 1.5%; mean reviews to
pass fell from 2.08 to 1.32." `[BLOG]`

### 6.2 The public product's re-review scope

The public documentation states a re-review scope:

> "A later review that starts on its own, such as after a push, focuses on what changed since the
> last review and posts fewer nits and pre-existing findings. Its summary counts what it left out,
> in a line that ends “found and not posted” or “outside the scope of this re-review and not
> posted.”" `[PR-DOCS]`

A review requested with `@claude review` "covers the whole pull request again." `[PR-DOCS]` The
documentation does not state a numeric round cap, an escalation to the author, or a hard stop.

### 6.3 Other controls in the public product

- A review "resolves its own earlier comment threads" and a later review resolves a thread when it
  judges the issue fixed. `[CR-DOCS]` `[PR-DOCS]`
- Automatic reviews skip drafts and PRs from forks. `[PR-DOCS]`
- `REVIEW.md` can cap nits, exclude paths, and require evidence. `[CUSTOMIZE]`
- `--max-findings <n>` changes the local review's usual limit; where the review reports through
  the findings tool, "the limit is 32." `[LOCAL]`

## 7. Metrics, guardrails and how the reviewer is improved

### 7.1 Human-time metrics and the guardrail

The post defines the target and the measures:

> "So the goal is that most pull requests in the Claude Code repos (the CLI, the desktop and web
> apps, and the mobile apps) merge with at most one human in the loop, who can be the author, with
> no increase in reverts or incidents. To measure human time, we track human approvals per PR
> (median and 95th percentile), human comments, and how long a PR waits on a person. Revert and
> incident rates are the guardrail: if they rise, we haven't saved human time, we've only moved
> it." `[BLOG]`

### 7.2 Reported figures

The sources report these numbers:

| Figure | Value | Source |
| ------ | ----- | ------ |
| Share of internal PRs getting substantive review comments | 16% before, 54% after | `[BLOG]` `[ANNOUNCE]` `[SEC-SDLC]` |
| Large PRs (>1,000 lines) with findings | 84%, averaging 7.5 issues | `[ANNOUNCE]` |
| Small PRs (<50 lines) with findings | 31%, averaging 0.5 issues | `[ANNOUNCE]` |
| Findings marked incorrect | "less than 1%" | `[ANNOUNCE]` |
| Average review time at preview | "around 20 minutes" | `[ANNOUNCE]` |
| Average review time at GA | "about 3x faster (~20 minutes down to 6-10 minutes)" | `[GA]` |
| Review cost | "generally average $15–25" | `[ANNOUNCE]` |
| Code written by Claude in Claude Code | "about 90 percent" | `[BLOG]` |
| Merged PRs to Claude Code, June to September | "more than doubled" while the reverted share "fell by more than 40 percent" | `[BLOG]` |
| PRs passing after one review and fix round | 65% to 78% | `[BLOG]` (figure data) |
| PRs needing five or more rounds | 8.9% to 1.5% | `[BLOG]` (figure data) |
| Mean reviews to pass | 2.08 to 1.32 | `[BLOG]` (figure data) |
| Flagged lines that predated the reviewer's first pass | "about 59%" | `[BLOG]` |
| Bugs behind past claude.ai incidents that current automated processes would have caught | "approximately a third" | `[SEC-SDLC]` |

The post states the 90% figure as something it has "said before" and does not link a source for
it; the post's subject is Claude Code's own code. `[BLOG]` The security article separately states
that Claude authors "about 80% of the code merged into our codebase today." `[SEC-SDLC]`

### 7.3 Noise measurement

The post describes how comment noise is scored:

> "We sort every comment the reviewer leaves by how the person on the PR responded: they fixed it,
> said it was wrong, said the behavior was intentional, or decided it didn't matter. We also run
> the reviewer on PRs we know are clean and count how often it reports something that would have
> led someone to make a harmful change. Our priority, written down, is catching real bugs first
> and cutting review rounds second." `[BLOG]`

It adds that "Noise costs more when the author is an agent. A person can wave off a nit in
seconds. An agent fixes it, which means another commit and another round of review." `[BLOG]`

### 7.4 The improvement loop

- **Incidents become an eval.** "The team collected past PRs that caused incidents, with their
  fix-forwards and reverts, and had engineers who know that code confirm each bug and where it
  lived. The reviewer runs against that set daily." `[BLOG]`
- **Filters were A/B tested.** Findings about style, diagnostics, or cleanup were dropped after
  A/B testing the filters on the team's own PRs. `[BLOG]`
- **Reviewer changes are rescored.** The post's adoption guidance says to "Turn incidents and
  reverts into an eval set, and rescore the reviewer whenever its prompts, tools or model change."
  `[BLOG]`
- **Misses become instructions.** "When a review misses something, we ask what the model didn't
  have in front of it and put the fix into a `CLAUDE.md`, a skill or a new check." `[BLOG]`
- **Recurring comments move to `REVIEW.md`.** The post says to "Add a `REVIEW.md`, and move
  repeated review comments into it." `[BLOG]`
- **New AI reviewers run in shadow mode and are sampled.** `[SEC-SDLC]`
- **Approvals are logged and sampled.** `[SEC-SDLC]`
- **Agent actions go to the SIEM.** `[SEC-SDLC]`
- **Security monitors a metrics dashboard.** "We maintain and closely monitor a dashboard that
  rolls up key metrics across every security process and workstream." `[SEC-SDLC]`

### 7.5 Guardrails and stated limits

- The stated guardrail: "Revert and incident rates are the guardrail: if they rise, we haven't
  saved human time, we've only moved it." `[BLOG]`
- "We don't yet have circuit breakers that tighten approval when those numbers move; engineers
  here want them before more code moves to zero-human merges." `[BLOG]`
- Human accountability remains: "A person is accountable for every change that ships, whoever
  typed it." `[BLOG]`
- The ownership norm: "If you land a small or medium change and something still goes wrong, it's a
  team norm that you usually fix it." The reasons given are small changes, reversibility, blast
  radius, fast regression signals, and that "It isn't blame." `[BLOG]`
- The public product warns: "Code Review uses AI to review code and may miss bugs, security
  vulnerabilities, or other issues. A review with no findings doesn't mean your code is error-free
  or secure." `[CR-DOCS]`
- The public security features "should complement, not replace, your existing security practices
  and manual code reviews." `[SEC-SUPPORT]`
- The security-guidance plugin "does not block writes or commits" and is "one layer of defense in
  depth, not a complete security solution." `[SEC-GUIDANCE]`

## 8. Related ownership and context practices in the same account

The post also states these practices; they are recorded because they are part of the same
published account of the review process:

- "Code review does two jobs: 1. Find and fix issues before they ship 2. Build shared context and
  codebase understanding across the team." `[BLOG]`
- "We don't have a formal process for this." People ask Claude to write an explainer for the
  slice they need, and some build a small visualization. `[BLOG]`
- Ownership is shared through open channels: "Much of the team works in open channels where anyone
  can see what others are building, pick up a thread, or point a Claude at a gap." `[BLOG]`
- Direction changes: "The trick is to raise a different direction in the thread early, not as a
  blocking comment on a finished PR." `[BLOG]`
- The team's source-control article says its members "still review every change request for the
  system, but they now examine the intent of the change as opposed to reading every line of code."
  `[SCION]`

## Open gaps

These are things the sources read do **not** state. They are recorded as gaps, not as conclusions.

1. **Classifier mechanics.** The post says "A classifier reads the change" and a second classifier
   decides whether another person is needed, but does not say whether the classifiers are models,
   rules, or people, what inputs they use, or what thresholds they apply. `[BLOG]`
2. **Sensitive-path and two-person-path lists.** Only examples are published: owner-listed
   sensitive paths and CI workflow files always need a person; the high tier includes "a small set
   of paths that always need two people" that is not enumerated. `[BLOG]`
3. **Trusted-list criteria.** The post says lighter paths go to authors on "the repo's trusted
   list, mostly the team that owns it", but does not state how the list is created, reviewed, or
   removed from. `[BLOG]`
4. **Approval eligibility.** The post states "one person" and "two people", that an agent's
   approval never counts, and that the person directing an agent counts. It does not state whether
   any person with write access can approve, whether authors may approve their own medium-risk
   changes, or how an approval is recorded or audited in that system. `[BLOG]` The security
   article states that "Every approval is logged with the signals and reasoning behind it, and a
   risk-weighted sample is reviewed by humans." `[SEC-SDLC]`
5. **Scope of "owners decide which low-risk changes merge on automated checks alone."** The post
   states the practice but not which repos, which low-risk classes, or what evidence an owner uses.
   `[BLOG]`
6. **The internal PR template.** The post describes two fields in its own template (how the change
   was tested, how to undo it) and, separately, its adoption guidance lists adding "Testing",
   "Risk" and "How to revert" to a template. It does not reproduce the internal template or say
   whether "Risk" is a field there. `[BLOG]`
7. **The internal skills.** The post names three purposes (bug hunting, diff simplification,
   end-to-end behavior) but not the skills' names or contents. `[BLOG]`
8. **Round-cap semantics.** "After three rounds, the reviewer asks the author to step back and
   reconsider the approach" does not state whether the reviewer can still post findings after
   that, whether the cap blocks merging, or how a disagreement is resolved. `[BLOG]` The public
   product documents re-review scope but no numeric cap or escalation. `[PR-DOCS]`
9. **Eval methodology.** The post states that incidents and reverts become an eval, that experts
   confirm each case, and that the reviewer runs against the set daily. It does not publish the
   set's size, case-selection rules, scoring method, or agreement measurement. `[BLOG]`
10. **Metric methodology.** The figures in 7.2 are reported without published sample definitions,
    time windows, or measurement method. The 90% "Claude writes" figure is stated as previously
    said, with no link. `[BLOG]` `[ANNOUNCE]` `[GA]`
11. **The 50-round example.** The post gives no PR link, repository, date, or outcome beyond the
    author stopping it. `[BLOG]`
12. **Incident review and rollback targets.** The post states a weekly on-call rotation and that
    incident reviews ask which layer should have caught the issue; it does not state who attends,
    how often reviews occur, what the outcomes are, or any rollback time target. `[BLOG]`
13. **Merge-queue scope.** The post says the Claude Code repositories use a merge queue; the
    source-control article says a proper merge queue "doesn't make much sense at agent scale" for
    the monorepo and that the team invested in post-merge and pre-deploy testing instead. No
    source read reconciles which codebase uses which arrangement. `[BLOG]` `[SCION]`
14. **Risk tiers versus review levels.** The internal account has Low/Medium/High risk tiers; the
    public product has Quick/Standard/Deep review levels. No source states a mapping between them,
    and the public service "never approves or blocks." `[BLOG]` `[CR-DOCS]` `[GA]`
15. **The security organization's tiers.** "We tier our codebase by risk" is stated without tier
    definitions, path lists, or a list of codebases with strict human approval. `[SEC-SDLC]`
16. **The X post.** The Boris Cherny post linked by the blog was not independently fetched; only
    the blog's quotation of it is used, so it is secondary here. `[X]`

## Sources

All URLs were accessed on **2026-10-20** (America/Los_Angeles).

| Key | Source | Publisher / date | URL | Status |
| --- | ------ | ---------------- | --- | ------ |
| `[BLOG]` | "How the Claude Code team does code review" (URL slug: `solving-code-review-at-anthropic`), Addy Osmani, Morgan Westlee Lunt, Qing Wang | claude.dev developer blog (linked from claude.com as "Developer blog"), 2026-10-15 | https://claude.dev/blog/solving-code-review-at-anthropic/ | Primary |
| `[CR-DOCS]` | "Code Review" | Claude Code documentation, code.claude.com, undated | https://code.claude.com/docs/en/code-review | Primary |
| `[CUSTOMIZE]` | "Customize Code Review" | Claude Code documentation, undated | https://code.claude.com/docs/en/code-review-customize | Primary |
| `[PR-DOCS]` | "Read and request reviews on a pull request" | Claude Code documentation, undated | https://code.claude.com/docs/en/code-review-pull-requests | Primary |
| `[LOCAL]` | "Review locally with `/code-review`" | Claude Code documentation, undated | https://code.claude.com/docs/en/code-review-local | Primary |
| `[MEMORY]` | "How Claude remembers your project" | Claude Code documentation, undated | https://code.claude.com/docs/en/memory | Primary |
| `[SEC-GUIDANCE]` | "Catch security issues as Claude writes code" | Claude Code documentation, undated | https://code.claude.com/docs/en/security-guidance | Primary |
| `[ANNOUNCE]` | "Bringing Code Review to Claude Code" | claude.com, 2026-03-09 | https://claude.com/resources/articles/code-review | Primary |
| `[GA]` | "Code Review is now generally available" | claude.com, 2026-10-15 | https://claude.com/resources/articles/code-review-is-now-generally-available | Primary |
| `[SEC-SDLC]` | "How Anthropic secures its AI-native software development lifecycle", Jason Clinton | claude.com, 2026-07-21 | https://claude.com/resources/articles/how-anthropic-secures-its-ai-native-software-development-lifecycle | Primary |
| `[SEC-SUPPORT]` | "Automated Security Reviews in Claude Code" | Claude Help Center, 2026-03-16 | https://support.claude.com/en/articles/11932705-automated-security-reviews-in-claude-code | Primary |
| `[SCION]` | "Redesigning source control at Anthropic" | Anthropic Engineering, 2026-10-13 (updated 2026-10-15) | https://www.anthropic.com/engineering/redesigning-source-control | Primary |
| `[ORG]` | "Running an AI-native engineering org", Fiona Fung | claude.com, 2026-06-03 | https://claude.com/resources/articles/running-an-ai-native-engineering-org | Primary |
| `[X]` | Boris Cherny post on verification, linked from `[BLOG]` | x.com, undated in the link | https://x.com/bcherny/status/2007179861115511237 | Secondary; not independently fetched, quoted only via `[BLOG]` |
