# Research: How mattpocock/skills sets up a repository and chains its skills

## Question

How does mattpocock/skills expect a repository to be set up, and how do its skills chain from an idea to a merged change?

## Source snapshot

- Repository: `https://github.com/mattpocock/skills`
- Default branch: `main`
- Commit: `5beb35b040e3de97e54fa9e386d7e42d15c295c2`
- Commit date: 2026-10-19 16:51:40 +0100
- Commit subject: `chief-of-staff: keep memory in a dated, commit-cited wiki (#1304)`
- Access date: 2026-10-20 (America/Los_Angeles)
- Method: `git ls-remote` resolved `HEAD` and `refs/heads/main` to the SHA above on 2026-10-20; `git clone --depth 1` produced the working tree used for every quote below.
- Citation convention: `[S#]` links resolve in **Sources** at the end. Every repository path is relative to the repository root at the commit above. Primary sources are the repository's own `SKILL.md` files, skill templates, manifests and agent-policy files at that commit. First-party pages under `docs/` are marked **secondary** where they describe behavior beyond the skill file. Files under `.changeset/` are marked **pending-release notes**: they describe changes present in the tree, not a published release.

## Findings

### 1. Skill inventory and invocation mode

The repository has 38 `SKILL.md` files at this commit: 20 under `skills/engineering/`, 7 under `skills/productivity/`, 4 under `skills/misc/`, 7 under `skills/in-progress/`, and 0 under `skills/deprecated/`. The bucket layout is defined in `CLAUDE.md`:

> `engineering/`: daily code work
> `productivity/`: daily non-code workflow tools
> `misc/`: kept around but rarely used, not promoted
> `in-progress/`: beta: public on purpose, feedback wanted, not shipped in the plugin
> `deprecated/`: no longer used

`CLAUDE.md` defines **promoted** as `engineering/` plus `productivity/`, and states that the Claude Code plugin ships exactly the promoted set:

> Every skill in `engineering/` or `productivity/` (the **promoted** buckets) must have a reference in the top-level `README.md` and an entry in `.claude-plugin/plugin.json`'s `skills` array (the Claude Code plugin ships exactly the promoted set). Skills in `misc/`, `in-progress/`, and `deprecated/` must not appear in either. [S2]

The plugin manifest lists 27 skill directories, matching the 20 engineering plus 7 productivity skills. [S8] ADR 0002 records why the set ships as a Claude Code plugin and how the manifests select the promoted subset. [S6] The `misc/` bucket is described as "frozen and unmaintained" and `in-progress/` is "not shipped in the plugin". [S31][S2]

The one invocation axis is defined in `CLAUDE.md`:

> Every `SKILL.md` is either user-invoked (`disable-model-invocation: true` plus `policy.allow_implicit_invocation: false` in `agents/openai.yaml`, reachable only by the human) or model-invoked (model- or user-reachable). [S2]

`.agents/invocation.md` gives the same rule and the reason for the two-file pairing:

> **User-invoked**: reachable **only by the human typing its name**. Set `disable-model-invocation: true` in the frontmatter (Claude Code) and `policy.allow_implicit_invocation: false` in `agents/openai.yaml` (Codex). [...] **Model-invoked**: reachable by **model or user**. The default: omit `disable-model-invocation` and the `policy` block from `agents/openai.yaml`. [S4]

Each `SKILL.md` also has an `agents/openai.yaml` beside it. `CLAUDE.md` states the split must agree across harnesses: "Keep the two in sync: a skill is user-invoked in both harnesses or neither." [S2]

The table below reads the split from each `SKILL.md` frontmatter and its sibling `agents/openai.yaml` at the snapshot commit. Every row's source is `https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/<path>/SKILL.md` and the adjacent `agents/openai.yaml` [S1]; for example, [`engineering/ask-matt`](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/ask-matt/SKILL.md).

| Skill | `disable-model-invocation` | `allow_implicit_invocation` | Mode |
| --- | --- | --- | --- |
| `engineering/ask-matt` | `true` | `false` | user-invoked |
| `engineering/code-review` | absent | absent | model-invoked |
| `engineering/codebase-design` | absent | absent | model-invoked |
| `engineering/diagnosing-bugs` | absent | absent | model-invoked |
| `engineering/domain-modeling` | absent | absent | model-invoked |
| `engineering/grill-with-docs` | `true` | `false` | user-invoked |
| `engineering/implement` | `true` | `false` | user-invoked |
| `engineering/implement-spec` | `true` | `false` | user-invoked |
| `engineering/improve-codebase-architecture` | `true` | `false` | user-invoked |
| `engineering/pr` | absent | absent | model-invoked |
| `engineering/prototype` | absent | absent | model-invoked |
| `engineering/research` | absent | absent | model-invoked |
| `engineering/retro` | `true` | `false` | user-invoked |
| `engineering/setup-matt-pocock-skills` | `true` | `false` | user-invoked |
| `engineering/tdd` | absent | absent | model-invoked |
| `engineering/to-spec` | `true` | `false` | user-invoked |
| `engineering/to-tickets` | `true` | `false` | user-invoked |
| `engineering/triage` | `true` | `false` | user-invoked |
| `engineering/wayfinder` | `true` | `false` | user-invoked |
| `engineering/wizard` | absent | absent | model-invoked |
| `productivity/grill-me` | `true` | `false` | user-invoked |
| `productivity/grilling` | absent | absent | model-invoked |
| `productivity/handoff` | `true` | `false` | user-invoked |
| `productivity/teach` | `true` | `false` | user-invoked |
| `productivity/to-questionnaire` | `true` | `false` | user-invoked |
| `productivity/wait-what` | `true` | `false` | user-invoked |
| `productivity/writing-for-agents` | absent | absent | model-invoked |
| `misc/git-guardrails-claude-code` | absent | absent | model-invoked |
| `misc/migrate-to-shoehorn` | absent | absent | model-invoked |
| `misc/scaffold-exercises` | absent | absent | model-invoked |
| `misc/setup-pre-commit` | absent | absent | model-invoked |
| `in-progress/chief-of-staff` | `true` | `false` | user-invoked |
| `in-progress/claude-handoff` | `true` | `false` | user-invoked |
| `in-progress/loop-me` | `true` | `false` | user-invoked |
| `in-progress/setup-ts-deep-modules` | `true` | `false` | user-invoked |
| `in-progress/writing-beats` | `true` | `false` | user-invoked |
| `in-progress/writing-fragments` | `true` | `false` | user-invoked |
| `in-progress/writing-shape` | `true` | `false` | user-invoked |

Totals from the table: 23 user-invoked and 15 model-invoked. Within the 27 promoted skills: 16 user-invoked and 11 model-invoked. No `SKILL.md` has `disable-model-invocation: true` without the `allow_implicit_invocation: false` policy, and none has the policy without the frontmatter flag. `skills/deprecated/` contains only a `README.md` at this commit. [S1]

The top-level `README.md` groups the promoted skills under the same two headings and states the boundary:

> **User-invoked** skills are reachable only when you type them (e.g. `/grill-me`); their job is to orchestrate. **Model-invoked** skills can be invoked by you _or_ reached for automatically by the agent when the task fits; they hold the reusable discipline. A user-invoked skill may invoke model-invoked skills, but never another user-invoked one. [S3]

The engineering bucket README repeats the same split, with each entry linked to its `SKILL.md`. [S7]

The repository's own `AGENTS.md` is a symlink to `CLAUDE.md`: `ls -l AGENTS.md` reports `AGENTS.md -> CLAUDE.md`. [S1]

### 2. What `setup-matt-pocock-skills` writes into a repository

`setup-matt-pocock-skills` is user-invoked. The top-level `README.md` tells the user to run it once per repo before the first engineering flow, and `ask-matt` lists it under **Precondition** rather than as a step in the main flow. [S9][S3][S26] Its own description says:

> Configure this repo for the engineering skills: set up its issue tracker, triage label vocabulary, and domain doc layout. Run once before first use of the other engineering skills. [S9]

The skill describes itself as "a prompt-driven skill, not a deterministic script. Explore, present what you found, confirm with the user, then write." [S9] It explores `git remote -v` and `.git/config`, `AGENTS.md`, `CLAUDE.md`, `GLOSSARY.md`, `GLOSSARY-MAP.md`, `docs/adr/`, `src/*/docs/adr/`, `docs/agents/`, `.scratch/`, whether `triage` is installed, and monorepo signals. [S9]

#### 2.1 Files and paths

| Path | Written when | Seed or form | What it contains |
| --- | --- | --- | --- |
| `CLAUDE.md` or `AGENTS.md` (`## Agent skills` block) | always | inline template in `SKILL.md` | one-line pointers to the three `docs/agents/` files |
| `docs/agents/issue-tracker.md` | always | `issue-tracker-github.md`, `issue-tracker-gitlab.md`, `issue-tracker-local.md`, or prose supplied by the user | tracker conventions, PR-as-request-surface flag, wayfinding operations |
| `docs/agents/triage-labels.md` | only when `triage` is installed and Section B ran | `triage-labels.md` | mapping from five canonical roles to tracker label strings |
| `docs/agents/domain.md` | always | `domain.md` | read order for glossary and ADRs, file layout, vocabulary rule, ADR-conflict rule |
| Tracker labels | when Section B ran on GitHub or GitLab | `gh label create` / `glab label create` | creates each configured label the tracker lacks |

The file and label rows are from `SKILL.md` step 4. [S9] The "written when" conditions are explicit in the same step:

> Include the `### Triage labels` sub-block, and write `docs/agents/triage-labels.md`, only when `triage` is installed and Section B ran. When it isn't, both are omitted. [S9]

> When Section B ran on GitHub or GitLab, create each configured label the tracker lacks (`gh label create` / `glab label create`). [S9]

The `## Agent skills` block is:

```markdown
## Agent skills

### Issue tracker

[one-line summary of where issues are tracked]. See `docs/agents/issue-tracker.md`.

### Triage labels

[one-line summary of the label vocabulary]. See `docs/agents/triage-labels.md`.

### Domain docs

[one-line summary of layout: "single-context" or "multi-context"]. See `docs/agents/domain.md`.
```

It goes into exactly one instruction file. The selection rule is:

> If `CLAUDE.md` exists, edit it.
> Else if `AGENTS.md` exists, edit it.
> If neither exists, ask the user which one to create; don't pick for them. [S9]

> Never create `AGENTS.md` when `CLAUDE.md` already exists (or vice versa); always edit the one that's already there. [S9]

If an `## Agent skills` block already exists, the skill updates it in place rather than appending a duplicate, and it does not overwrite user edits to surrounding sections. [S9]

The source repository's own setup is narrower than the full output: its `docs/agents/` contains only `triage-labels.md`, and its `CLAUDE.md` ends with only an `### Triage labels` sub-block pointing at that file. It has no `docs/agents/issue-tracker.md` or `docs/agents/domain.md` at this commit. [S2][S32]

#### 2.2 Issue-tracker conventions

The GitHub template says issues and specs "live as GitHub issues" and to "Use the `gh` CLI for all operations". [S10] Its conventions cover create, read, list, sub-issues, comment, label and close:

> - **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
> - **Read an issue**: `gh issue view <number> --json number,title,body,labels,comments`.
> - **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
> - **Make an issue a sub-issue of a parent**: `gh issue create --parent <parent> ...`, or `gh issue edit <parent> --add-sub-issue <child>` afterwards (`gh` 2.94+). [...]
> - **Comment on an issue**: `gh issue comment <number> --body "..."`
> - **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
> - **Close**: `gh issue close <number> --comment "..."` [S10]

The same file carries the PR-as-request-surface flag, defaulted off:

> **PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_ [S10]

When set to `yes`, it defines PR read/list/comment/label/close equivalents, and notes that GitHub shares one number space between issues and PRs, so a bare `#42` is resolved with `gh pr view 42` then `gh issue view 42`. [S10]

It also defines the wayfinding operations used by `wayfinder`: the map is "a single issue labelled `wayfinder:map`"; child tickets are sub-issues labelled `wayfinder:<type>`; blocking uses native issue dependencies via `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, falling back to a `Blocked by:` line; the frontier is the open, unblocked, unassigned children; claim is `gh issue edit <n> --add-assignee @me`; resolve is comment, close, then append a gist and link to the map's Decisions-so-far. [S10]

The GitLab template mirrors this with `glab`, with GitLab-specific names: comments are "notes", merge requests replace PRs, native blocking is the `/blocked_by #<n>` quick action (Premium/Ultimate), and the fallback is the same `Blocked by:` body line. [S11]

The local-markdown template defines a repository-internal convention rather than a tracker:

> - One feature per directory: `.scratch/<feature-slug>/`
> - The spec is `.scratch/<feature-slug>/spec.md`
> - Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
> - Triage state is recorded as a `Status:` line near the top of each issue file
> - Comments and conversation history append to the bottom of the file under a `## Comments` heading [S12]

Its wayfinding form is `.scratch/<effort>/map.md` plus `.scratch/<effort>/issues/NN-<slug>.md`, with a `Type:` line for `research`/`prototype`/`grilling`/`task` and a `Status:` line for `claimed`/`resolved`. [S12]

For any other tracker, setup writes `docs/agents/issue-tracker.md` from scratch using the user's one-paragraph description. [S9]

#### 2.3 Triage-label conventions

The seed file maps five canonical roles to tracker strings and tells the user to edit the right-hand column:

| Label in mattpocock/skills | Label in our tracker | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified, ready for an AFK agent |
| `ready-for-human` | `ready-for-human` | Requires human implementation |
| `wontfix` | `wontfix` | Will not be actioned |

> When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table. [S13]

> Edit the "Label in our tracker" column to match whatever vocabulary you actually use. [S13]

Section B asks one question, "Do you want to keep the default triage labels? (recommended: **yes**)", and writes the labels as-is on yes; if the user says no, it collects overrides "so `triage` applies existing labels instead of creating duplicates." [S9] Section B is skipped entirely when `triage` is not installed. [S9]

The two **category** roles used by `triage`, `bug` and `enhancement`, do not appear in this mapping file; see the gap list. [S19][S13]

#### 2.4 Domain-doc conventions

`docs/agents/domain.md` defines the consumer contract for the domain docs. Its first section is:

> ## Before exploring, read these
>
> - **`GLOSSARY.md`** at the repo root, or
> - **`GLOSSARY-MAP.md`** at the repo root if it exists: it points at one `GLOSSARY.md` per context. Read each one relevant to the topic.
> - **`docs/adr/`**: read ADRs that touch the area you're about to work in. In multi-context repos, also check `src/<context>/docs/adr/` for context-scoped decisions.
>
> If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. [S14]

It defines two layouts. Single-context is `GLOSSARY.md` plus `docs/adr/` at the root; multi-context is `GLOSSARY-MAP.md` at the root pointing at per-context `GLOSSARY.md` and `src/<context>/docs/adr/`. [S14] It also states the vocabulary rule ("use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids") and the ADR-conflict rule:

> If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:
>
> > _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_ [S14]

Setup defaults to single-context and writes it without asking; it offers multi-context only when exploration found monorepo signals. [S9]

#### 2.5 What setup does not write

- It does not create `GLOSSARY.md`, `GLOSSARY-MAP.md` or ADRs. `domain.md` says the `domain-modeling` skill "creates them lazily when terms or decisions actually get resolved". [S14] The setup docs page states "a repo with no domain docs after setup is normal." [S33]
- The setup `SKILL.md` names no `.out-of-scope/` write; that directory is written by `triage`. [S9][S21]
- It does not edit any skill's `SKILL.md`. [S33]
- It has no user-level or global mode; the config is committed per repository. [S33]
- It does not create `wayfinder:map` or `wayfinder:<type>` labels. [S33] See the gap list for the resulting missing-label case.

The setup docs page also records a discrepancy with the skill file on label creation: it says setup "does not run `gh label create`" and that `docs/agents/triage-labels.md` is only a mapping. [S33] The skill file says to create the missing labels at step 4. [S9] The changeset in the same tree says "`setup-matt-pocock-skills` now creates missing triage labels on GitHub/GitLab (#616)". [S43] This is recorded as an open gap below.

### 3. The nine requested skills: inputs, outputs and operations

Every subsection reads the operative steps from the `SKILL.md` at the snapshot commit. First-party docs pages are cited only for statements that go beyond the skill file, and are marked secondary.

#### 3.1 `to-spec`

**Inputs.** The current conversation context and the codebase understanding, with no new interview:

> This skill takes the current conversation context and codebase understanding and produces a spec. Do NOT interview the user; just synthesize what you already know. [S15]

It expects the issue tracker and triage-label vocabulary to have been provided, and otherwise tells the user to run `/setup-matt-pocock-skills`. [S15] It uses the project's domain glossary vocabulary and respects ADRs in the area. [S15]

**Process.** It explores the repo, sketches the seams where the feature will be tested, prefers existing and highest seams, aims for one seam if possible, and checks the seams with the user before writing. [S15]

**Output.** One spec issue in the configured tracker, using the seven-section template: Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope, Further Notes. [S15] It then applies the `ready-for-agent` triage label:

> Write the spec using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label - no need for additional triage. [S15]

**Tracker, branch, commit and PR operations.** Creates one issue in the configured tracker; applies `ready-for-agent`. No branch, commit or PR operation is named. The tracker template supplies `gh issue create` and `gh issue edit --add-label` for GitHub. [S15][S10] The skill does not instruct a search of the tracker for duplicate or overlapping issues before publishing. [S15] The first-party docs page states that it does not search the tracker and does not cite the ADRs it respects. [S34]

**Skills called.** None. [S15]

#### 3.2 `to-tickets`

**Inputs.** A plan, a spec, or the current conversation. If the user passes a reference (a spec path, issue number or URL), it fetches that and reads the full body and comments. [S16] It expects the tracker and triage-label vocabulary to have been provided, and otherwise points at `/setup-matt-pocock-skills`. [S16] It uses the project's glossary vocabulary and respects ADRs in the area. [S16]

**Process.** It optionally explores the codebase, looks for prefactoring ("Make the change easy, then make the easy change"), and breaks the work into tracer-bullet vertical slices. Each slice must cut through every layer, be demoable or verifiable alone, and fit one fresh context window. [S16] It then gives each ticket its blocking edges, quizzes the user on granularity and edges, and iterates until the user approves. [S16] Wide refactors are the exception: they are sequenced as expand, migrate in batches, contract, rather than forced into vertical slices. [S16]

**Output.** One ticket per approved slice, published "in dependency order (blockers first)". On a real tracker, each ticket becomes an issue; if the source was an existing issue, each ticket is made its sub-issue. It applies `ready-for-agent` "unless instructed otherwise; the tickets are agent-grabbable by construction". [S16] On local markdown, it writes one file per ticket under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in dependency order, with the per-ticket template containing What to build, Blocked by, Status and acceptance criteria. [S16]

**Tracker, branch, commit and PR operations.** Creates one issue per ticket; makes each a sub-issue of the source issue when there is one; writes blocking edges using the platform's native relationship where it has one, otherwise a `Blocked by` section; applies `ready-for-agent`; explicitly "Do NOT close or modify any parent issue." [S16] The GitHub tracker template supplies the sub-issue commands and the native blocking command. [S10] The changeset records the sub-issue behavior and the omission of `## Blocked by` when the edges are native. [S45] No branch, commit or PR operation is named. [S16]

**Skills called.** None. [S16]

**First-party docs note (secondary).** The docs page repeats the vertical-slice rule, the quiz, and the native-edge preference, and adds that the skill stops at the artifact and has no auto-dispatch mode. [S35]

#### 3.3 `implement`

**Inputs.** A spec or a set of tickets, or work described by the user. If the user passes a ticket reference, the skill fetches it from the issue tracker and states its title before starting; if the reference is ambiguous, it asks. [S17] It expects pre-agreed seams and drives `tdd` at them. [S17]

**Output.** Code changes on the current branch, plus a `code-review` pass. The `SKILL.md` names no branch creation and no PR; the first-party docs page states that the skill does not create a branch and does not ask. [S17][S36]

> Call the Skill tool with "tdd" where possible, at pre-agreed seams.
>
> Run typechecking regularly, single test files regularly, and the full test suite once at the end.
>
> Once done, call the Skill tool with "code-review" to review the work.
>
> Commit your work to the current branch. [S17]

**Tracker, branch, commit and PR operations.** Reads the ticket when a reference is passed. Commits to the current branch. It names no branch creation, no push, no PR, and no ticket close or acceptance-criteria update. [S17] The first-party docs page states the same limit explicitly: "`implement` has no completion step. It ends at the commit and never touches the work item." [S36]

**Skills called.** `tdd`, then `code-review`. [S17]

**First-party docs note (secondary).** The docs page says one run covers one ticket, and that the review-before-commit order means `code-review` cannot see uncommitted work. [S36]

#### 3.4 `implement-spec`

**Inputs.** A spec with associated tickets, read from the configured tracker. The skill expects the tracker to have been provided, and otherwise points at `/setup-matt-pocock-skills`. [S18] It reads the tickets as a task graph, not a list:

> The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed. [S18]

**Output.** The whole spec implemented on one integration branch, with every ticket resolved the way the tracker closes work; optionally, a draft PR later marked ready. [S18]

**Process.** The steps are:

1. Read the spec and tickets.
2. Optionally use an exploration subagent that saves markdown notes "in a directory outside the repo, accessible by all future subagents". [S18]
3. Create the integration branch. If the tracker closes work through PRs, or the user asks, open a draft PR "after the first merge in step 5 (a branch with no commits ahead of main can't open one), marked as closing the spec and tickets." [S18]
4. Run implementer subagents, each in its own worktree and branch. Each confirms its worktree is based on the integration branch and resets onto it if not, calls `tdd`, and merges the integration branch tip into its own branch before reporting done. [S18]
5. Merge each completed implementer's work to the integration branch "with a **merger subagent**". [S18]
6. Kick off more implementers when the frontier changes. [S18]
7. Once all tickets are complete, call `code-review` on the integration branch and fix all findings "in a single **implementer subagent**". [S18]
8. If a draft PR exists, mark it ready for review; otherwise "resolve each ticket the way the issue tracker closes work, and report the integration branch." [S18]
9. Clean up all implementer subagent worktrees. [S18]

**Tracker, branch, commit and PR operations.** Reads the spec and tickets. Creates an integration branch. Creates one worktree and branch per implementer. Merges implementer branches into the integration branch through a merger subagent. Opens a draft PR after the first merge when the tracker closes work through PRs or the user asks, and marks it ready at the end. Resolves tickets when there is no PR. Cleans up worktrees. [S18] The skill states no base commit for the integration branch, no push command, and no explicit commit command for the implementer subagents. [S18] It does not instruct a merge into the default branch. [S18]

**Skills called.** `tdd` from each implementer, and `code-review` once over the integration branch. [S18]

**First-party docs note (secondary).** The docs page says implementers communicate with the orchestrator through context pointers, that the run ends on the integration branch when no PR is wanted, and that the tracker decides whether a PR exists at all. [S37]

#### 3.5 `triage`

**Inputs.** Issues on the project tracker, plus external PRs when the tracker config sets the request-surface flag to `yes`. The maintainer invokes `/triage` with a natural-language request. It reads the full issue or PR, prior triage notes, the codebase through the domain glossary and ADRs, and `.out-of-scope/*.md`. [S19]

**Output.** A recommendation first, then, on direction, an applied category role and state role, and one of: an agent brief comment, triage notes, a closing comment, or an `.out-of-scope/` record. [S19] Every comment or issue it posts must start with:

```text
> *This was generated by AI during triage.*
```

The requirement is stated in the `triage` SKILL.md. [S19]

**Process.** It shows three discovery buckets (unlabeled, `needs-triage`, and `needs-info` with reporter activity), then for a chosen item: gather context; recommend with reasoning and a codebase summary; verify the claim (reproduce a bug, or check out a PR and run its tests); grill if needed by calling `grilling` and `domain-modeling`; apply the outcome. [S19] The apply step depends on the state:

- `ready-for-agent`: post an agent brief comment.
- `ready-for-human`: same structure as an agent brief, with the reason it cannot be delegated.
- `needs-info`: post triage notes using the template.
- `wontfix`: close, with one of three comment paths: already implemented (point to where it lives, no `.out-of-scope/` write), rejected bug (polite explanation, close), rejected enhancement (write `.out-of-scope/`, link it from the comment, close). [S19]
- `needs-triage`: apply the role, optionally comment. [S19]

**Tracker, branch, commit and PR operations.** Reads and lists issues and, when in scope, PRs; applies and removes labels; posts comments; closes issues; writes `.out-of-scope/` files in the repo; checks out a PR and runs commands for verification. [S19] It creates no branch, commit or PR. It does not merge. [S19]

**Skills called.** `grilling` and `domain-modeling`, both in one "call twice" step, when the request needs fleshing out. [S19]

**Agent brief.** The brief is "the authoritative specification that an AFK agent will work from", is posted on an issue or PR when it moves to `ready-for-agent`, and is durable rather than precise: name interfaces, types and behavioral contracts, do not name file paths or line numbers, include testable acceptance criteria and explicit scope boundaries. [S20] The original body and discussion are "context: the agent brief is the contract." [S20]

**First-party docs note (secondary).** The docs page says triage is "only for issues **you didn't create**", recommends rather than relabels, and treats `ready-for-human` on a PR as "ready for a human to merge". [S38]

#### 3.6 `code-review`

**Inputs.** A fixed point named by the user (commit SHA, branch, tag, `main`, `HEAD~5`, etc.) and optionally a spec. If the user does not name a fixed point, the skill asks. [S22] It expects the issue tracker to have been provided, and otherwise points at `/setup-matt-pocock-skills`. [S22]

**Process.** It captures one diff command, `git diff <fixed-point>...HEAD` (three-dot, against the merge-base), plus `git log <fixed-point>..HEAD --oneline`, and fails before spawning anything if the ref does not resolve or the diff is empty. [S22] It then finds the spec in this order:

1. Issue references in commit messages (`#123`, `Closes #45`, GitLab `!67`), fetched via the tracker doc.
2. A path passed as an argument.
3. A spec file under `docs/`, `specs/`, or `.scratch/` matching the branch or feature name.
4. Asking the user. If there is no spec, the Spec axis is skipped and reports "no spec available". [S22]

It finds standards sources by searching the repo for every file that documents how code should be written; `CODING_STANDARDS.md` and `CONTRIBUTING.md` "must be on the list" when present. [S22] On top of the repo's standards it always applies a twelve-smell baseline from Fowler's _Refactoring_ chapter 3: Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest. Two rules bind the baseline: "The repo overrides" any documented standard, and every smell is a judgement call. [S22]

**Output.** Two separate reports, under `## Standards` and `## Spec`, returned by two parallel sub-agents. The aggregation is explicitly non-merged:

> Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings, because the two axes are deliberately separate (see _Why two axes_). [S22]

It ends with total findings per axis and the worst issue within each axis, and does not pick a single winner across axes. [S22]

**Tracker, branch, commit and PR operations.** Reads the originating issue through the tracker when a commit message references one. Runs read-only git commands (`rev-parse`, `diff`, `log`). [S22] It creates no branch, commit or PR and writes no tracker state. [S22]

**Skills called.** None. It spawns two sub-agents with pasted prompts; those sub-agents are not named skills. [S22]

**First-party docs note (secondary).** The docs page says the skill never merges or re-ranks the axes, that findings are "a hypothesis, not evidence", that a fresh session is preferred over the authoring session, and that there is no convergence guarantee. [S39]

#### 3.7 `pr`

**Inputs.** A pull request body being written. The description is simply "Use when writing a PR body." [S23]

**Output.** A PR body in three sections:

> ## Summary
>
> <diagram, diff-sketch, or tree>
>
> ## Evidence
>
> - **Before:** <screenshot/output/failing test run>
>   **After:** <screenshot/output/passing test run>
>
> ## Merge Danger
>
> **Door:** <one-way or two-way>
>
> <optional: description>
>
> **Blast Radius:** <one-word description>
>
> <optional: potential ramifications of merge> [S23]

The Summary is "the smallest view that makes the key point clear", chosen from pseudocode, call tree, component tree, file tree, Mermaid, or a shaped diff. Evidence is a before and after; a screenshot is the strongest evidence when the change is visual, otherwise the exact test or console output. Merge Danger asks for a one-way or two-way door and a blast radius. [S23] The skill says "Skip all preambles and keep prose brief" and "Use the user's domain language from `GLOSSARY.md`." [S23]

**Tracker, branch, commit and PR operations.** None named. It does not push a branch, open a PR or decide its contents. [S23] The first-party docs page states this directly: "It does not push a branch, open the PR, or decide what goes into it." [S40]

**Skills called.** None. [S23]

#### 3.8 `wayfinder`

**Inputs.** A loose idea (chart mode), or an existing map identified by URL or number and optionally a ticket (work mode). It expects the issue tracker to have been provided, and otherwise points at `/setup-matt-pocock-skills`; if no tracker has been provided, it defaults to the local-markdown tracker. [S24]

**Output.** A map issue labelled `wayfinder:map` with the body sections Destination, Notes, Decisions so far, Not yet specified, Out of scope; child issues labelled `wayfinder:<type>` whose body is `## Question`; blocking edges; claims; resolution comments; closed tickets; updated map lines; and, for research tickets, a pushed `research/<name>` branch. [S24]

**Process: chart the map.**

1. Name the destination by calling `grilling` and `domain-modeling`.
2. Grill breadth-first to map the frontier and the fog. If no fog appears, stop: the effort is small enough to skip the map, and the skill asks the user how to proceed.
3. Create the map with the destination and notes, empty Decisions so far, and the fog in Not yet specified.
4. Create the tickets that can be specified now as child issues, then wire blocking edges "in a **second pass**" because issues need ids first. Write cross-references only with real ids.
5. Fire a research subagent for each `research` ticket; it calls `research` and captures findings on a throwaway `research/<name>` branch with a context pointer.
6. Stop. [S24]

The research-branch rule is:

> capturing its findings on a throwaway `research/<name>` branch with a context pointer from the ticket. Push the branch but open no PR: it is never merged. [S24]

The changeset records the same behavior: "`wayfinder` no longer labels maps or tickets `ready-for-agent` (#518), writes cross-references only with real issue ids (#507), opens no PR from research branches (#576), and resolves each ticket as the type its label names (#625)." [S44]

**Process: work through the map.**

1. Load the map at low resolution.
2. Choose the ticket: the named one, or the first frontier ticket in order. Claim it by assigning it to yourself before any work.
3. Resolve it as the type in its `wayfinder:<type>` label. Read the label, not the body. Fetch related or closed ticket bodies on demand, call the skills named in Notes, and in doubt call `grilling` and `domain-modeling`.
4. Record the resolution: post the answer as a resolution comment, close the issue, append a context pointer to the map's Decisions-so-far.
5. Add newly surfaced tickets (create then wire), graduate fog into new tickets, rule out-of-scope work by closing it and adding one line to Out of scope, and update or delete tickets invalidated by the decision. [S24]

The session limit is explicit:

> Either way, **never resolve more than one ticket per session**, with the exception of research tickets. [S24]

**Ticket types.** `wayfinder:<type>` is one of `research` (AFK), `prototype` (HITL), `grilling` (HITL), or `task` (HITL or AFK). Research is resolved by a subagent that calls the `research` skill; prototype calls `prototype` and links the artifact; grilling always calls `grilling` and `domain-modeling`; task is manual work that unblocks a decision and is resolved when done. [S24] A map and its tickets carry the `wayfinder:` labels only, "never a triage label like `ready-for-agent`: they are decisions, not implementation work." [S24]

**Planning stance.** The skill is "planning by default": each ticket resolves a decision, and the map is done when nothing is left to decide. An effort may override this in the map's Notes by carrying execution into the map, but absent that override it produces "decisions, not deliverables". [S24]

**Tracker, branch, commit and PR operations.** Creates the map issue and child issues; applies `wayfinder:` labels; writes native blocking edges or the body-line fallback; assigns the ticket to claim it; comments the resolution; closes resolved and out-of-scope tickets; edits the map's Decisions-so-far and Not yet specified. Pushes a `research/<name>` branch and opens no PR from it. [S24] It does not merge, and the branch is "never merged". [S24]

**Skills called.** `grilling`, `domain-modeling`, `research`, `prototype`, as the ticket type and charting step require. [S24][S27][S28]

**First-party docs note (secondary).** The docs page states that wayfinder is "situational on-ramp, not the default starting point", that a cleared map rejoins the chain at `to-spec`, and that the map is finished when the session "points you toward a spec, not a pull request." [S41]

#### 3.9 `retro`

**Inputs.** A coding session, defaulting to the current one, or a session the user identifies in session logs. It first calls `writing-for-agents` for the writing style. [S25]

**Process.** It reads the primary sources for that session and looks for candidates in seven categories: navigation, automated checks, coding standards, global `AGENTS.md`, tool economy, no-ops, and information access. [S25] It then presents the candidates "in order of severity". [S25]

Its reference section states the division of labor between implementation and review:

> Remember that all work goes through two stages: implementation and review. The implementation agent has the most **context pressure**. They are responsible for exploration, writing code, and debugging failures.
>
> The review agent has the least context pressure - it receives a diff, so no exploration needed. It often does not need to write code or debug.
>
> This means that the review agent should be responsible for imposing coding standards, not the implementation agent. [S25]

It also states the file roles: `CLAUDE.md`/`AGENTS.md` "are pushed to the context window of any agent working in this repo. They should be used incredibly sparingly, usually only for **navigation pointers** to other files"; `CODING_STANDARDS.md` "is read during review, not implementation"; docs are reference files pointed to by other files; skills are for docs or user-invoked commands. [S25]

**Output.** A prioritized list of candidate improvements to the agent's environment. The `SKILL.md` presents candidates and names no edit step; the docs page states "`retro` only proposes. Nothing changes until you pick a candidate." [S25][S42]

**Tracker, branch, commit and PR operations.** None named. It reads session logs, `package.json`/build-tool check scripts, CI workflows, `AGENTS.md`/`CLAUDE.md`, and `CODING_STANDARDS.md`; it writes no tracker state, branch, commit or PR. [S25]

**Skills called.** `writing-for-agents`. [S25]

**First-party docs note (secondary).** The docs page says mechanical violations should become deterministic checks and that only genuine judgement calls belong in `CODING_STANDARDS.md`; it also states that the skill edits nothing and installs no hook automatically. [S42]

#### 3.10 The chain at a glance

`ask-matt` is the repository's router. It describes one main flow, an On-ramps section, a codebase-health skill, a vocabulary layer, phase boundaries, and standalone skills. [S26] The main flow it documents is:

> 1. **`/grill-with-docs`** sharpens the idea by interview. [...]
> 2. **Branch: can you settle every question in conversation?** If a question needs a runnable answer [...], detour through a prototype, bridged by **`/handoff`** in both directions [...]
> 3. **Branch: is this a multi-session build?**
>    - **Yes** → **`/to-spec`** ... then **`/to-tickets`** ... Then work the tickets one of two ways:
>      - **`/implement`** per ticket, **`/clear`ing context between each one**. [...]
>      - **`/implement-spec`** for the whole spec in one run. [...]
>    - **No** → **`/implement`** right here, in the same context window.
>
>    Either way, the code gets built by driving **`/tdd`** ... and closes out with **`/code-review`** ...
>
> 4. **`/retro`** closes the loop. [S26]

The docs pages render the same chain as text:

- `grill-with-docs → to-spec → to-tickets → implement → code-review → retro` [S34][S35][S36][S39][S42]
- `grill-with-docs → to-spec → to-tickets → implement-spec → retro` [S37]
- `to-spec → to-tickets → implement → code-review → pr → retro` when the work ships as a PR [S40]

`ask-matt`'s introduction says "Most paths run along one **main flow**, and two **on-ramps** merge onto it", but its `## On-ramps` section lists three: `triage` ("Bugs and requests piling up"), `diagnosing-bugs` ("Something's broken"), and `wayfinder` ("A huge, foggy effort"). [S26] `wayfinder` "hands off, it doesn't build" and rejoins the main flow at `to-spec`; `triage` is a parallel lane for work that arrived from someone else. [S26][S41][S38]

The invocation rule and the chain text sit at different layers. All of `to-spec`, `to-tickets`, `implement`, `implement-spec`, `wayfinder`, `triage` and `setup-matt-pocock-skills` are user-invoked, and `.agents/invocation.md` says a skill can never reach another user-invoked skill. [S4] Separately, the docs page for `implement` states that when `ask-matt` or `to-tickets` says "then `/implement` per ticket", "that is an instruction to you, not something the agent will do unprompted." [S36] The sources do not state that the arrows are Skill tool calls.

Among the requested skills and their docs pages, the sources contain no instruction for an agent to merge a PR into the default branch. The only literal branch-merge instruction is `implement-spec` merging implementer branches into its integration branch. [S18][S24][S38]

### 4. The triage state machine and label meanings

`triage` defines two **category** roles and five **state** roles. [S19]

Category roles:

| Role | Meaning |
| --- | --- |
| `bug` | Something is broken |
| `enhancement` | New feature or improvement |

State roles:

| Role | Meaning |
| --- | --- |
| `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | Fully specified, ready for an AFK agent |
| `ready-for-human` | Requires human implementation |
| `wontfix` | Will not be actioned |

The meanings above are from `triage` and its mapping template. [S19][S13] The invariant is:

> Every triaged issue should carry exactly one category role and one state role. If state roles conflict, flag it and ask the maintainer before doing anything else. [S19]

The transitions are:

> State transitions: an unlabeled issue normally goes to `needs-triage` first; from there it moves to `needs-info`, `ready-for-agent`, `ready-for-human`, or `wontfix`. `needs-info` returns to `needs-triage` once the reporter replies. The maintainer can override at any time; flag transitions that look unusual and ask before proceeding. [S19]

The discovery surface is three buckets, oldest first: unlabeled, `needs-triage`, and `needs-info` with reporter activity since the last triage notes. When PRs are in scope, each line is tagged `[PR]` or `[issue]`, and discovery shows only external PRs; naming a PR explicitly always triages it regardless of author. [S19]

For a PR, the same states read against the attached code: `ready-for-agent` means a brief is attached and an agent should take the next step on the diff; `ready-for-human` "means it's ready for a human to merge." [S19]

`wontfix` has three distinct paths, and only one writes the knowledge base:

| Why it is closed | What the skill does |
| --- | --- |
| Already implemented | Points to where the feature lives; does **not** write `.out-of-scope/`, because "that KB is for *rejected* requests, not built ones." |
| Rejected bug | Polite explanation, then close. |
| Rejected enhancement | Writes `.out-of-scope/`, links it from a comment, then closes. |

The `.out-of-scope/` rules: one file per concept, not per issue; multiple requests for the same thing are grouped under one file; a rejected enhancement (including an enhancement PR) is recorded; an already-implemented feature is not; the file is a short design document with a decision, a reason, and a Prior requests list. [S21]

The maintainer can override the machine directly ("move #42 to ready-for-agent"): the skill confirms the role changes, comment and close, then acts, and skips grilling. If moving to `ready-for-agent` without a grilling session, it asks whether the user wants an agent brief. [S19]

The label strings are not necessarily the canonical names. The mapping file translates each role to the tracker's string, and `triage` says "The actual label strings used in the issue tracker may differ. The mapping should have been provided to you. If not, tell the user to run `/setup-matt-pocock-skills`." [S19][S13]

### 5. How skills read `AGENTS.md`, `CLAUDE.md`, `docs/agents/`, `GLOSSARY.md` and ADRs

#### 5.1 The instruction file and the `## Agent skills` pointer

The mechanism is a pointer from the always-loaded instruction file to three small files in the repository. Setup writes the `## Agent skills` block into whichever of `CLAUDE.md` or `AGENTS.md` exists, preferring `CLAUDE.md` and refusing to create one when the other exists. [S9] The block's three entries each end with `See docs/agents/<file>.md`. [S9]

The block carries a one-line summary and a path for each file; the conventions themselves live in `docs/agents/`. The setup docs page describes the mechanism: "Those files are the only thing that varies between repos. The skills themselves are identical everywhere. They read `docs/agents/issue-tracker.md` at run time and do what it says." [S33]

The source repository itself follows this only partially: `AGENTS.md` is a symlink to `CLAUDE.md`, and `CLAUDE.md` has an `### Triage labels` sub-block pointing at `docs/agents/triage-labels.md`, but no issue-tracker or domain-doc block and no corresponding files. [S1][S2][S32]

`retro` treats the instruction file as a context-cost surface rather than a rules dump:

> `CLAUDE.md`/`AGENTS.md`: these files are pushed to the context window of any agent working in this repo. They should be used incredibly sparingly, usually only for **navigation pointers** to other files. [S25]

`setup` is the only requested skill that reads and edits `AGENTS.md`/`CLAUDE.md` directly; `retro` reads them to look for steering lines that should move to standards or checks. [S9][S25] The other requested skills do not name `AGENTS.md` or `CLAUDE.md` in their `SKILL.md`; they rely on the harness loading the file and on the `docs/agents/` pointer inside it. [S15][S16][S17][S18][S19][S22][S23][S24]

#### 5.2 `docs/agents/`

The three files have distinct conditions and readers:

| File | Written by setup | Read by | How it is reached | When it is absent |
| --- | --- | --- | --- | --- |
| `docs/agents/issue-tracker.md` | always | `to-spec`, `to-tickets`, `triage`, `code-review`, `wayfinder`, `implement-spec`, `implement` | "The issue tracker ... should have been provided to you" [S15][S16][S19][S22][S24][S18][S17], plus the `## Agent skills` pointer | The skills that carry the pointer tell the user to run `/setup-matt-pocock-skills`; `wayfinder` says it defaults to local markdown if no tracker has been provided [S24]; `implement` names no fallback. [S17] |
| `docs/agents/triage-labels.md` | only when `triage` is installed and Section B ran | `triage` reads the mapping; `to-spec` and `to-tickets` apply the label string without naming the file | "The issue tracker and triage label vocabulary should have been provided to you." [S15][S16] | Setup omits the file and the `### Triage labels` block. [S9] |
| `docs/agents/domain.md` | always | the skills that read the glossary and ADRs, through the block | The file states its own read order; setup's block points at it. [S14][S9] | The consumer rule is "proceed silently"; absence is not flagged. [S14] |

`wayfinder` uses a named section rather than a fixed path: it says "Consult the tracker doc's 'Wayfinding operations' section for how _this_ repo expresses them", and the first-party docs page adds that wayfinder "finds that doc through the pointer in your `CLAUDE.md` / `AGENTS.md`, not at a fixed path." [S24][S41]

`code-review` resolves issue references "via the workflow in the tracker doc", and its changeset says it "resolves the issue tracker through the provided tracker doc instead of a hard-coded path." [S22][S46]

#### 5.3 `GLOSSARY.md` and ADRs

The domain-doc contract is `docs/agents/domain.md`: before exploring, read `GLOSSARY.md` or `GLOSSARY-MAP.md`, and read the ADRs that touch the area; if they are missing, proceed silently and do not suggest creating them. Vocabulary output must use the glossary's terms, and an output that contradicts an ADR must surface the conflict rather than silently overriding. [S14]

The files themselves are created lazily by `domain-modeling` when the first term or decision is resolved. [S14][S30] `GLOSSARY.md` is "totally devoid of implementation details"; it is a glossary, not a spec or scratch pad. [S30] ADRs live in `docs/adr/` with sequential numbering (`0001-slug.md`), and are only offered when a decision is hard to reverse, surprising without context, and the result of a real trade-off. [S30]

Which requested skills name the glossary or ADRs:

| Skill | Glossary | ADRs | Quote or note |
| --- | --- | --- | --- |
| `to-spec` | yes | yes | "Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching." [S15] |
| `to-tickets` | yes | yes | "Ticket titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching." [S16] |
| `implement` | no | no | The SKILL.md does not name them. [S17] |
| `implement-spec` | no | no | The SKILL.md does not name them. [S18] |
| `triage` | yes | yes | "Explore the codebase using the project's domain glossary, respecting ADRs in the area." [S19] |
| `code-review` | no | no | It reads the repo's coding-standards documents; `CODING_STANDARDS.md` and `CONTRIBUTING.md` must be on the list when present. [S22] |
| `pr` | yes | no | "Use the user's domain language from `GLOSSARY.md`." [S23] |
| `wayfinder` | no | no | The SKILL.md does not name them; it calls `domain-modeling` for the decision work. [S24] |
| `retro` | no | no | It names `CLAUDE.md`/`AGENTS.md`, `CODING_STANDARDS.md` and docs as reference files. [S25] |
| `setup-matt-pocock-skills` | reads existing | reads existing | Explores `GLOSSARY.md`, `GLOSSARY-MAP.md`, `docs/adr/` and `src/*/docs/adr/` before proposing the layout. [S9] |

`.agents/invocation.md` draws a line between reading the glossary and invoking `domain-modeling`:

> Merely _reading_ `GLOSSARY.md` for vocabulary is a one-line prose pointer, not the `domain-modeling` skill. Only the active build/sharpen discipline (challenge terms, edge-case scenarios, write ADRs, update `GLOSSARY.md` inline) is `domain-modeling`. [S4]

The ADR for the setup pointer splits skills into hard and soft dependencies:

> - **Hard dependency** (`to-tickets`, `to-spec`, `triage`): include an explicit one-liner: _"… should have been provided to you; run `/setup-matt-pocock-skills` if not."_ Without the mapping, output is wrong, not just fuzzy.
> - **Soft dependency** (`diagnose`, `tdd`, `improve-codebase-architecture`): reference "the project's domain glossary" and "ADRs in the area you're touching" in vague prose only. [S5]

At this commit, the explicit setup pointer also appears in `code-review`, `wayfinder` and `implement-spec`, which the ADR does not list; the soft-dependency list also names `diagnose`, while the current skill is `diagnosing-bugs`. [S22][S24][S18][S5] This is recorded as a gap.

### 6. Invocation and chaining rules, and the stated stance on review, PR shape, branching and merging

#### 6.1 Which skills may invoke which

The hard rule is in `.agents/invocation.md`:

> A user-invoked skill may invoke model-invoked skills, but it can never reach another user-invoked skill. [S4]

Dependencies between skills are expressed as an explicit call to the Skill tool, not as cross-folder file links or a bare slash-name in prose:

> Dependencies are expressed as an explicit instruction to **call the Skill tool** with the named skill (`Call the Skill tool with "grilling"`), not deep `../other-skill/FILE.md` cross-references, and not a bare `/skill`-style mention left for the model to interpret. [S4]

Two calls are required when two skills are needed:

> The Skill tool takes one skill per call. A step that needs two skills is two calls, not one call with two names: say so (`Call the Skill tool twice, for "grilling" and "domain-modeling"`), not "call it with X and Y," which reads as a single call taking both. [S4]

When the precondition is user-invoked, the skill must hand the action to the human:

> When a step's precondition is a user-invoked skill (e.g. `setup-matt-pocock-skills`), phrase it as an instruction for the human to act on: "tell the user to run `/setup-matt-pocock-skills`", never as a Skill tool call. [S4]

Router prose that names skills for a human to choose from is not invoking anything, so it keeps `/skill`-style names as plain labels. [S4] `ask-matt` is the main router; `CLAUDE.md` says it "maps every user-reachable skill and how they relate", and changes to a skill's place in the flow require updating it. [S2][S26]

The explicit Skill tool calls among the requested skills are:

| Skill | Calls |
| --- | --- |
| `to-spec` | none |
| `to-tickets` | none |
| `implement` | `tdd`, `code-review` |
| `implement-spec` | `tdd` per implementer, `code-review` once |
| `triage` | `grilling` and `domain-modeling`, twice in one step |
| `code-review` | none; two review sub-agents |
| `pr` | none |
| `wayfinder` | `grilling`, `domain-modeling`, `research`, `prototype` |
| `retro` | `writing-for-agents` |

Sources: [S15][S16][S17][S18][S19][S22][S23][S24][S25]

#### 6.2 Chain rules the sources state

- `triage` is for incoming work, not for tickets the planning flow produced. `ask-matt` says: "Triage is only for issues **you didn't create**: bug reports, incoming feature requests, anything that arrives raw. Tickets that `/to-tickets` produced are already agent-ready, so **don't triage them**." [S26]
- `to-tickets` does not close or modify the parent issue. [S16]
- `wayfinder` is planning, not execution, unless the map's Notes override it; a map and its tickets carry only `wayfinder:` labels, never `ready-for-agent`; and a session resolves one ticket, except research tickets. [S24]
- A finished wayfinder map does not build: `ask-matt` says it merges onto the main flow at `to-spec`, and going straight to `implement` "skips that collapse and throws the linked detail away", except when the effort turned out small. [S26]
- `implement-spec` reads tickets as a task graph with a frontier, not as a sequential list. [S18]
- Setup is a precondition for the tracker-reading skills, not a chain step: `ask-matt` lists `/setup-matt-pocock-skills` under **Precondition**. [S26]

#### 6.3 Review stance

`code-review` is the review skill. Its defining choices are:

- Two axes, Standards and Spec, each in a parallel sub-agent "so they don't pollute each other's context". [S22]
- A fixed point is mandatory; the skill asks for one if the user did not supply it. [S22]
- The diff is `<fixed-point>...HEAD`, three-dot, so it is measured from the merge-base and excludes staged and working-tree changes. [S22]
- Findings are presented per axis and never merged or reranked; the summary picks a worst issue per axis and no overall winner. [S22]
- The repo's documented standards override the Fowler smell baseline; every smell is a judgement call, and anything tooling already enforces is skipped. [S22]
- Every finding cites a standard, a named smell plus hunk, or a spec line. [S22]

The first-party docs page adds three statements beyond the skill file, marked secondary: findings are "a hypothesis, not evidence"; a fresh review session is preferred over the authoring session; and there is no convergence guarantee, so the skill should not be run in a loop until clean. [S39]

`implement` and `implement-spec` both close with `code-review`; `implement` runs it before committing, and `implement-spec` runs it once over the integration branch and sends all findings to one fix subagent. [S17][S18]

#### 6.4 PR shape

`pr` defines the body as Summary, Evidence, and Merge Danger. The Summary is a visual chosen as "the smallest view that makes the key point clear", not a prose restatement of the diff. Evidence is a before and after, with a screenshot described as "S-tier" when the change is visual and execution-based evidence as "A-tier". Merge Danger asks whether the change is a one-way or two-way door and names its blast radius. [S23]

The skill writes only the body and names no push, open, update or merge operation. The first-party docs page states that it "does not push a branch, open the PR, or decide what goes into it." [S23][S40] It also does not read a repository's existing PR template; the docs page says "Neither, by default" when a repo template and the `pr` template both exist. [S38]

`implement-spec` is the one requested skill that opens a PR: a draft after the first merge when the tracker closes work through PRs or the user asks, marked ready at the end. [S18] The `pr` skill is model-invoked, so it can be reached when a PR body is being written, but no requested skill contains an explicit "call `pr`" step. [S23][S4]

#### 6.5 Branching and merging

- `implement` commits "to the current branch". The first-party docs page states that it "does not create one, and it does not ask." [S17][S36]
- `implement-spec` creates an integration branch, gives each implementer its own worktree and branch based on the integration branch, has each implementer merge the integration tip into its branch, and has a merger subagent merge each completed branch into the integration branch. It opens a draft PR only when the tracker closes work through PRs or the user asks, and otherwise resolves tickets and stops on the integration branch. [S18]
- `wayfinder` research tickets push a throwaway `research/<name>` branch and "open no PR: it is never merged." [S24]
- `prototype` commits the prototype to "a throwaway branch, out of main" and leaves a context pointer on the implementation issue; "The main branch keeps only the validated decision." [S29]
- No requested skill instructs a merge into the default branch. The only merge instruction is `implement-spec` merging implementer branches into its integration branch. [S18] On a PR, `triage` reads `ready-for-human` as "ready for a human to merge". [S19]

## Open gaps

These are points the snapshot leaves unresolved, contradictory or silent. They are recorded as facts about the sources, not as recommendations.

1. **Setup's label-creation behavior is contradictory across three first-party files.** `SKILL.md` step 4 says "create each configured label the tracker lacks (`gh label create` / `glab label create`)." [S9] The docs page says the opposite: "It doesn't. [...] It does not run `gh label create`", and calls the label file a mapping only. [S33] The changeset says "`setup-matt-pocock-skills` now creates missing triage labels on GitHub/GitLab (#616)." [S43] The sources do not state which text is authoritative.

2. **The label vocabulary is conditional on `triage` being installed, but `to-spec` and `to-tickets` still instruct applying a triage label.** Setup skips Section B and omits `docs/agents/triage-labels.md` when `triage` is not installed, "since an uninstalled skill needs no labels." [S9] `to-spec` says "Apply the `ready-for-agent` triage label" [S15] and `to-tickets` says "Apply the `ready-for-agent` triage label unless instructed otherwise." [S16] The sources do not state how a repo without the `triage` skill maps a custom label vocabulary for these two skills.

3. **The two category roles have no mapping file.** `triage` defines `bug` and `enhancement` as category roles and requires exactly one category and one state role per issue. [S19] The seed `triage-labels.md` maps five state roles only. [S13] Setup's Section B asks only about the five default labels. [S9] The triage docs page tells the user to create "the five state labels and two category labels yourself", but no template maps the two. [S38]

4. **`wayfinder`'s own labels are not created by setup.** `wayfinder` requires a `wayfinder:map` label and `wayfinder:<type>` labels. [S24] Setup creates the triage labels only when Section B ran, and names no wayfinder labels. [S9] The setup docs page says setup does not create them and that `gh issue create --label <missing>` "fails instead of creating the label"; it advises creating them by hand before the first wayfinder run on GitHub. [S33]

5. **The native-blocking command is documented two ways.** The GitHub tracker template adds an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, using the blocker's database id. [S10] The to-tickets docs page says GitHub supports native blocking and gives `gh issue create --blocked-by 12,15`. [S35] The `to-tickets` skill itself says to use "the platform's native blocking relationship where it has one", without naming a command. [S16] The sources do not say which command is canonical at this commit.

6. **`implement` runs `code-review` before committing, and `code-review` reviews committed work only.** `implement` orders "call the Skill tool with `code-review`" before "Commit your work to the current branch." [S17] `code-review` reviews `git diff <fixed-point>...HEAD`, three-dot, and notes the commit list; it does not include staged or working-tree changes. [S22] The implement docs page calls this unfixed on both sides: "Commit first, then review against the point you branched from." [S36]

7. **`implement` does not close the ticket, while the frontier depends on closures.** The `implement` steps end at "Commit your work to the current branch" and name no ticket state change. [S17] The implement docs page states it "never touches the work item", does not tick acceptance criteria, and tells the user: "Close the ticket and reconcile the criteria yourself." [S36] `to-tickets` defines the frontier as "any ticket whose blockers are all done", and the local template records `Status: ready-for-agent`. [S16] The docs page places ticket closure on the human; the `SKILL.md` has no closure step.

8. **`implement-spec`'s resolution step is under-specified.** The skill says "resolve each ticket the way the issue tracker closes work" when no draft PR exists. [S18] The GitHub tracker template gives `gh issue close` among its general conventions and defines a separate "Resolve" operation only under "Wayfinding operations": comment, close, then append a gist and link to the map's Decisions-so-far. [S10] The sources do not state whether `implement-spec`'s "resolve" means the general Close or the Wayfinding Resolve. When a draft PR does exist, step 8 marks it ready and does not say who resolves the tickets; [S18] the docs page says the tracker closes work through PRs, but does not name a merger. [S37] The skill also names no base commit for the integration branch, no push command and no explicit commit command for implementer subagents. [S18]

9. **`code-review`'s sub-agent prompts do not forbid re-invoking the skill.** The Standards and Spec prompts are pasted briefs under 400 words, and neither contains a no-delegation instruction. [S22] The code-review docs page calls the resulting recursion a "known open bug" reproduced in more than one harness, with a one-line guard "not in the shipped skill yet." [S39] This is a secondary claim about observed behavior; the primary text simply omits the guard.

10. **Setup's instruction-file choice is based on file existence, not the running harness.** The rule is "If `CLAUDE.md` exists, edit it. Else if `AGENTS.md` exists, edit it." [S9] The setup docs page calls this a known gap: in a repo with a `CLAUDE.md` left over from Claude Code, the block can go to a file Codex never reads, and it lists two manual workarounds. [S33] The sources do not state a harness-aware selection rule.

11. **`pr` and a repository's existing PR template have no precedence rule.** The `pr` skill uses its own three-section template; the docs page says it does not look for `.github/pull_request_template.md` "or anything like it." [S23][S40] The docs page says neither wins by default and that, doing nothing, "the agent has two competing instructions for the same document." [S40] The sources do not define which template applies when both exist.

12. **`to-spec` labels the spec `ready-for-agent`; the docs page says the label "marks an input, not a work order."** The skill applies the label directly. [S15] The docs page calls the resulting AFK pickup "the most-reported problem with the skill" and notes that AFK agents "will try to build the whole spec in one run instead of picking up the ticket slices"; it offers two workarounds, excluding the parent spec in the agent prompt or removing the label after `/to-tickets` runs. [S34] The skill text at this commit still applies the label.

13. **ADR 0001's hard/soft setup-pointer taxonomy no longer matches the skill files.** The ADR lists `to-tickets`, `to-spec` and `triage` as hard dependencies, and `diagnose`, `tdd` and `improve-codebase-architecture` as soft dependencies. [S5] The explicit "should have been provided to you; run `/setup-matt-pocock-skills` if not" pointer also appears in `code-review`, `wayfinder` and `implement-spec` at this commit. [S22][S24][S18] The soft list names `diagnose`, while the current skill is `diagnosing-bugs`. [S5] No source updates the ADR.

14. **`wayfinder`'s "plan, don't do" default has a documented override with no enforcement.** The skill says an effort "can override this in its **Notes**, carrying execution into the map itself." [S24] The first-party docs page calls this "a real gap in the skill" and reports that the agent writes the Notes, so the constraint and its exemption live in a file the constrained agent owns. [S41] The sources state no hard stop for the default.

15. **`ask-matt`'s on-ramp count does not match its list.** The introduction says "Most paths run along one **main flow**, and two **on-ramps** merge onto it", while the `## On-ramps` section lists three: `triage`, `diagnosing-bugs` and `wayfinder`. [S26] The sources do not say which count is intended.

## Sources

All sources were accessed on 2026-10-20 (America/Los_Angeles). `[S#]` labels are the citation keys used above; each label links to the exact file at the snapshot commit. "Primary" means the repository's own operative file at that commit. "Secondary" means first-party docs prose that describes behavior beyond the skill file. "Pending-release note" means a `.changeset/` entry present in the tree, not proof of a published release.

- [S1] Repository tree at `5beb35b040e3de97e54fa9e386d7e42d15c295c2` (primary; commit date 2026-10-19). `[S1]` also covers the `git ls-remote` and `git clone --depth 1` checks made on 2026-10-20.
- [S2] `CLAUDE.md` (primary; `AGENTS.md` is a symlink to it).
- [S3] `README.md` (primary for the published inventory and the user/model split; it also contains product prose).
- [S4] `.agents/invocation.md` (primary policy for invocation and skill-to-skill dependencies).
- [S5] `.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md` (primary design record).
- [S6] `.agents/adr/0002-ship-as-a-claude-code-plugin.md` (primary design record).
- [S7] `skills/engineering/README.md` (primary bucket listing).
- [S8] `.claude-plugin/plugin.json` (primary manifest; 27 entries).
- [S9] `skills/engineering/setup-matt-pocock-skills/SKILL.md` (primary).
- [S10] `skills/engineering/setup-matt-pocock-skills/issue-tracker-github.md` (primary seed template).
- [S11] `skills/engineering/setup-matt-pocock-skills/issue-tracker-gitlab.md` (primary seed template).
- [S12] `skills/engineering/setup-matt-pocock-skills/issue-tracker-local.md` (primary seed template).
- [S13] `skills/engineering/setup-matt-pocock-skills/triage-labels.md` (primary seed template).
- [S14] `skills/engineering/setup-matt-pocock-skills/domain.md` (primary seed template).
- [S15] `skills/engineering/to-spec/SKILL.md` (primary).
- [S16] `skills/engineering/to-tickets/SKILL.md` (primary).
- [S17] `skills/engineering/implement/SKILL.md` (primary).
- [S18] `skills/engineering/implement-spec/SKILL.md` (primary).
- [S19] `skills/engineering/triage/SKILL.md` (primary).
- [S20] `skills/engineering/triage/AGENT-BRIEF.md` (primary).
- [S21] `skills/engineering/triage/OUT-OF-SCOPE.md` (primary).
- [S22] `skills/engineering/code-review/SKILL.md` (primary).
- [S23] `skills/engineering/pr/SKILL.md` (primary).
- [S24] `skills/engineering/wayfinder/SKILL.md` (primary).
- [S25] `skills/engineering/retro/SKILL.md` (primary).
- [S26] `skills/engineering/ask-matt/SKILL.md` (primary router).
- [S27] `skills/productivity/grilling/SKILL.md` (primary; the primitive called by `triage`, `wayfinder` and `grill-with-docs`).
- [S28] `skills/engineering/research/SKILL.md` (primary; the research primitive).
- [S29] `skills/engineering/prototype/SKILL.md` (primary; prototype branch rule).
- [S30] `skills/engineering/domain-modeling/SKILL.md` (primary; glossary and ADR creation).
- [S31] `SCOPE.md` (primary repository scope; `misc/` is frozen and unmaintained).
- [S32] `docs/agents/triage-labels.md` (primary repository-local config; partial setup example).
- [S33] `docs/engineering/setup-matt-pocock-skills.md` (secondary first-party docs).
- [S34] `docs/engineering/to-spec.md` (secondary first-party docs).
- [S35] `docs/engineering/to-tickets.md` (secondary first-party docs).
- [S36] `docs/engineering/implement.md` (secondary first-party docs).
- [S37] `docs/engineering/implement-spec.md` (secondary first-party docs).
- [S38] `docs/engineering/triage.md` (secondary first-party docs).
- [S39] `docs/engineering/code-review.md` (secondary first-party docs).
- [S40] `docs/engineering/pr.md` (secondary first-party docs).
- [S41] `docs/engineering/wayfinder.md` (secondary first-party docs).
- [S42] `docs/engineering/retro.md` (secondary first-party docs).
- [S43] `.changeset/setup-tracker-fixes.md` (pending-release note; label creation and template fixes).
- [S44] `.changeset/wayfinder-labels-refs-research-prs.md` (pending-release note; wayfinder labels, real ids, no PR from research branches).
- [S45] `.changeset/to-tickets-sub-issues.md` (pending-release note; sub-issues and native blocking).
- [S46] `.changeset/code-review-standards-and-subagents.md` (pending-release note; standards-file search and sub-agent handling).

[S1]: https://github.com/mattpocock/skills/tree/5beb35b040e3de97e54fa9e386d7e42d15c295c2
[S2]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/CLAUDE.md
[S3]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/README.md
[S4]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/.agents/invocation.md
[S5]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md
[S6]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/.agents/adr/0002-ship-as-a-claude-code-plugin.md
[S7]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/README.md
[S8]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/.claude-plugin/plugin.json
[S9]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/setup-matt-pocock-skills/SKILL.md
[S10]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/setup-matt-pocock-skills/issue-tracker-github.md
[S11]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/setup-matt-pocock-skills/issue-tracker-gitlab.md
[S12]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/setup-matt-pocock-skills/issue-tracker-local.md
[S13]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/setup-matt-pocock-skills/triage-labels.md
[S14]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/setup-matt-pocock-skills/domain.md
[S15]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/to-spec/SKILL.md
[S16]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/to-tickets/SKILL.md
[S17]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/implement/SKILL.md
[S18]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/implement-spec/SKILL.md
[S19]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/triage/SKILL.md
[S20]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/triage/AGENT-BRIEF.md
[S21]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/triage/OUT-OF-SCOPE.md
[S22]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/code-review/SKILL.md
[S23]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/pr/SKILL.md
[S24]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/wayfinder/SKILL.md
[S25]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/retro/SKILL.md
[S26]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/ask-matt/SKILL.md
[S27]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/productivity/grilling/SKILL.md
[S28]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/research/SKILL.md
[S29]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/prototype/SKILL.md
[S30]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/domain-modeling/SKILL.md
[S31]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/SCOPE.md
[S32]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/agents/triage-labels.md
[S33]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/setup-matt-pocock-skills.md
[S34]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/to-spec.md
[S35]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/to-tickets.md
[S36]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/implement.md
[S37]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/implement-spec.md
[S38]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/triage.md
[S39]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/code-review.md
[S40]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/pr.md
[S41]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/wayfinder.md
[S42]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/docs/engineering/retro.md
[S43]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/.changeset/setup-tracker-fixes.md
[S44]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/.changeset/wayfinder-labels-refs-research-prs.md
[S45]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/.changeset/to-tickets-sub-issues.md
[S46]: https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/.changeset/code-review-standards-and-subagents.md
