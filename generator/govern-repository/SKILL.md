---
name: govern-repository
description: Initialize, upgrade or repair a repository's governance from the installed governance model. habit invokes it, with no arguments, from the repository's directory.
disable-model-invocation: true
metadata:
  opencode/autoinvoke: false
---

# Govern a repository

This run is a Builder delivery. Initialize and Repair are high. An Upgrade takes the tier
the default branch's adopted policy gives it, not the rendered target version; the Upgrade to
version 4 is still high. It takes no arguments and starts from the repository's directory.
`<entry>` below is `/usr/bin/python3 <this skill's directory>/scripts/govern.py`.
Each subcommand prints JSON; save each report in the run's report directory below.

**Temporary paths.** Allocate a fresh, unique directory with `mktemp -d` outside the checkout
for this run's reports. For each temporary worktree, allocate another fresh directory the
same way and give Git an unused child path inside it. Stop and preserve any pre-existing
work at an intended destination; never reuse or clear another run's directory or worktree.
Cleanup removes only paths this run allocated and worktrees it created.

**The harness.** The run happens only in Claude Code or OpenCode. In the Codex harness,
deepseekharness, Antigravity (app or CLI) or anything else, stop before any other step and
tell habit in Chinese where to run it, whatever a script says.

**Talking to habit.** Every message is plain Chinese, with governance terms and product names
in English and no code, diffs or paths. It names its sender and target.

**Before habit's answer** the checkout and GitHub stay as they are. The one write is
`<entry> accept-invitation`, for an invitation habit sent from the checklist.

## 1. Facts

1. Run `<entry> preconditions`. On a failed item, or a step only habit can take, give habit
   the one checklist. Items that block the run wait until habit says they are done. A step
   that can wait, such as the review bots, goes into the confirmation instead. On a private
   repository whose `private` item fails, give habit `rules_in_effect.habit_lines` verbatim,
   with its `command` beside them when there is one, and end: the run never waits on it.
2. Run `<entry> mode`, saving its report. On mode `stop`, or when any subcommand exits 2, tell
   habit the reason and end.
3. Follow the report's `outcome` by the words it begins with:
   - `no drift`: run `<entry> inspect` (read-only), send one Chinese message saying so and
     naming each Antigravity file it lists, left as it is, and end. No issue, no PR.
   - `not proven: the inactive rulesets`: run `<entry> inspect` (read-only), name each one
     under `drift.github.unplaced`, say it enforces nothing and needs no action, name each
     Antigravity file it lists, left as it is, and end. Write nothing and hand no command.
   - `not proven: the unread items` or `a ready owner-script command`, drift in GitHub state
     only: run `<entry> inspect` (read-only), go to section 6, step 2, naming any inactive
     ruleset under `unplaced` there too and each Antigravity file it lists, left as it is.
     No issue, no PR.
   - `Initialize`, `rebuild as at Initialize`, `Upgrade` or `Repair through the Upgrade
     flow`: carry on. Inactive rulesets under `unplaced` are named in the
     confirmation, and unread items under `drift.github.unreadable` are named there as
     unverified. "No drift" is said only for the no-drift outcome.

   `drift.github.owner_script_checks` is the accepted blind spot: settings the agent account
   can never read, which the owner script checks. They are never unverified, unread or drift,
   and never decide whether habit gets the owner-script command.
4. Run `<entry> inspect`.
5. **Product smoke, every PR-producing mode.** Before creating the ticket, identify actual
   default-branch product verification for the exact merged commit. A product build/test
   job triggered by a push to the default branch qualifies, including one in the same
   workflow as PR CI; identify its merged-commit run separately from the PR run. A failing
   qualifying run is failed smoke, not absent product verification. When verification is
   absent, select an executable local smoke from the repository's authoritative runbook and
   command inventory, with its prerequisites and success criterion. Preserve existing
   command prohibitions. At Upgrade and Repair, select it by reading; do not run exploratory
   build/test commands or change confirmed values or repository-owned content. Record the
   selected verification in the ticket before it is frozen. Governance audits, pre-merge
   PR runs and Release dispatch do not substitute. If no executable smoke can be determined,
   stop before creating the ticket and ask habit to resolve that blocker.

## 2. Judgment

At Initialize, or a rebuilt record, make every entry below; each ends up in the issue, and
in the confirmation as its items allow. At Upgrade, sort only the rules in
repository-owned content, to find what conflicts with the new fixed rules, and run no
commands: confirmed values and repository-owned content stay as they are, apart from a
conflict habit confirms. At Repair, make none of them; Antigravity's files are only listed.

- **Rules.** Sort every rule found in instructions, process documents, contributing guides
  and files at version paths into one class:
  - `covered`: the model already holds it, so it is dropped and listed;
  - `carried`: repository-specific and compatible, so "This repository" points to its
    authoritative runbook, naming when to read it; only a rule without an authoritative
    home is carried inline;
  - `conflicting`: it conflicts with the model or loosens it, so it is dropped and listed
    separately. Keeping it would be a model change, never a per-repository exception;
  - `removed`: an earlier decision removes it: a root `CLAUDE.md` once carried, any
    `AGENTS.override.md`, any `GEMINI.md`, `.codex/`, committed harness permission settings and agent
    definitions, issue templates of a replaced process, an older Bugbot rule file.

  Antigravity's own files follow the `removed` rule too, so its sessions read `AGENTS.md`'s
  policy. Sort the rules of every `GEMINI.md`, every `.agents/` `AGENTS.md`, `GEMINI.md` and
  `rules/` file, and every `.agent/` rule as a root `CLAUDE.md`'s, then class the file
  `removed`. List `.agents/` hooks (`hooks.json`), MCP servers (`mcp_config.json`),
  `plugins/`, custom subagents (`agents/`) and `workflows/` for habit and propose removing
  them, as `.codex/`. For a `rules.json`, list each of its entries for habit. Read a rule an
  entry selects only from the Git blob of a tracked regular file (`git ls-files -s` mode
  `100644` or `100755`), never through a link or a path outside the checkout, sort its
  rules, and keep such a file when it lies outside `.agents/` and `.agent/`. Read the
  manifest itself the same way; an untracked or linked manifest is listed unread. Class the
  manifest `removed` once every entry is accounted for. When an entry selects a directory,
  uses a filter, inherits another manifest, or resolves to a link or to no tracked regular
  file, name it for habit with the rules it leaves unaccounted for, and keep the manifest
  until habit decides on that entry. List workspace skills under `.agents/skills/` for habit
  and keep them, since other harnesses may read them. The legacy `.agent/` directory follows
  the same groups: the same files, hooks, MCP servers, plugins, subagents, workflows and
  skills, handled the same way. At Upgrade to version 6 or later, each file of the first two
  groups conflicts with the new fixed rule: sort its rules and propose its removal, a
  `rules.json` only once every entry is accounted for. At Repair, list each for habit and
  change nothing.

  Each rule's text is quoted with its file, except a credential in a rule, which is never
  quoted: its text names the credential's type and location instead (`AGENTS.md`, Secrets). Sort other files the model never writes, such as
  hooks, CODEOWNERS or a Bugbot config, the same way, and propose keeping or removing each.
  Preserve mandatory prohibitions and their force in the authoritative source. An
  explanatory consequence never replaces a prohibition. Carrying by reference removes
  duplicated policy, not command inventories, environment facts or verification evidence.
- **Sensitive paths.** Propose paths by category: authentication, billing and payments,
  release and publish workflows and scripts, installers, deployment configuration,
  secret-handling code, data migrations. Each gets a medium or high floor.
- **Required checks.** Propose a job only when `inspect` reads it as `every_pr: true` and not
  uncertain, under its reported `name`. Name every other job and why it can't be required.
- **Review bots**, when the version's manifest lists `review_bots`: propose those bots,
  enabled in the manifest's order, and name what each needs from habit (the `preconditions`
  checklist). habit's answer sets the record's enabled list and its order; a shorter list is
  allowed. Under version 4 the list is the order to try for one slot; when exhausted,
  medium takes a substituting Reviewer or habit's slot waiver, and high takes habit's wait
  or slot waiver. Older adopted policies still set the run's review requirements.
- **Commands.** Run the manifests' and documents' build and test commands in a temporary
  worktree allocated as **Temporary paths** above, so the checkout stays untouched. A manifest
  whose `extraction` is `unsupported` has its commands read from the file by you. Record each command you ran and
  whether it worked, with the cause of a failure. A failing command is a fact for `build.md`
  and the issue, never a question or an option for habit: the run never changes the
  repository's code, build or CI configuration to make one pass, which is separate work.
- **Actions secrets.** For each name under `ci.secrets`, propose its purpose and issuing
  service from the step that uses it. A name you can't place is asked about, never guessed.
- **Credentials.** A credential the inspection names is reported by type and location. Its
  removal is a separate ticket.

## 3. The confirmation

Send one plain message, never a question tool, then end the turn and wait for habit's answer.

- **Initialize, or a rebuilt record**, holds only: (1) sensitive paths as plain categories
  with paths as labels, plus any high floors; (2) the checks to make required, any that can't
   be and why, plus the product smoke or its local fallback; (3) the carrying lists: rules
  dropped as covered, rules dropped as conflicting, files removed by earlier decisions,
  repository skills sharing a machine skill's name, and nested `AGENTS.md` files; (4) the
  rulesets and branch protection the owner script will replace; (5) open PRs, for
  information; (6) any precondition step still open for habit; (7) the Actions secrets with
  proposed purposes and issuing services; (8) the labels to create; (9) on a private
  repository, that GitHub detects and blocks no credential there and that Actions minutes are
   limited, for habit's acknowledgment; (10) when the version's manifest lists
  `review_bots`, the enabled review bots in preference order. Files to keep or remove join
  item 3.
- **Upgrade** holds only: every change note after the record's version, combined, and what
  they mean here; confirmed values the new version newly needs, such as the enabled review
  bots when its manifest lists `review_bots` and the record holds none; each generated file
  the new version's manifest `retired`, which rendering removes, with any step that leaves
  to habit, such as disconnecting the Cursor GitHub App once its rule file is gone;
  repository-owned content that conflicts with the new fixed rules, Antigravity's files
  included; any ruleset or
  required-check change, applied after merge; the selected product smoke; and anything
  unverified. The Upgrade's own PR is reviewed under the policy on the default branch, the
  old version's; the new version's rules bind from the first PR after it merges. The new
  version's Merge watch may leave that PR's old review bots unjudged, so its Reviewer checks
  them before the merge. For the version 4 transition on a version 3 base only, an existing
  owner/exact-head `reviewer` waiver leaves that check to the Builder. Versions 1 and 2 still
  require the Reviewer status.
- **Repair with drift** holds only the drift found, how it is restored, the selected product
  smoke, any Antigravity file found (listed, left as it is), and anything unverified.

Each list is closed. Not asked: the wording of fixed content, the build and test commands
and their results, and the substitutions. Nothing outside a list's items becomes a question
or an option for habit; a fact the run found that fits no item goes into the issue.

An item habit's answer leaves open gets one follow-up about that item only, and stays open until habit answers it.

## 4. The issue

After habit's answer, run `<entry> identity`, then open one issue as the agent account with
`docs/agents/issue-tracker.md`'s create command form, and assign it to yourself with
`gh issue edit <n> --add-assignee "@me"`. It holds, in this order:

- habit's invocation, the findings, the proposals and habit's answers, each verbatim;
- one fenced block with the info string `govern-facts`, holding JSON with exactly these keys:
  Each rule's `text` quotes the original rule verbatim, including inline backticks, except
  that a credential in a rule is never quoted: its text names the credential's type and
  location instead (`AGENTS.md`, Secrets);
  `class` holds its classification, and rewritten carried text belongs outside this block.

  ```text
  rules: [{"text", "file", "class"}]        sensitive_paths: [{"pattern", "floor"}]
  required_checks: [name]                   actions_secrets: [{"name", "purpose", "service"}]
  labels_to_create: [name]                  nested_agents_md: [path]
  generator_identity: the identity subcommand's "identity"
  ```

- acceptance criteria and verification commands: exact comparison and the repository's
  commands that worked. A command that failed is listed as failing, outside Verification.
- after-merge product smoke: the qualifying default-branch job, or the predetermined local
  command, prerequisites and success criterion from Facts, tied to the exact merged commit.
  Record any known failure or unavailable prerequisite; selecting a smoke is not passing it.

## 5. Writing

1. Create only the labels missing from GitHub, from the version manifest's `labels`, with
   `gh label create <name> --color <color> --description <description>`. Every run that
   reaches Writing does this, Upgrade included, even when its confirmation names no labels.
   Preserve existing same-name, same-purpose labels with different descriptions. Their
   manifest descriptions are creation defaults. Escalate a purpose conflict before writing.
2. Allocate a worktree as **Temporary paths** above, on a new branch from the latest
   `origin` default branch.
3. Render: `<entry> render --dest <worktree> --repository <owner/name> --default-branch
   <branch> --confirmed <file>`, the file holding JSON with `sensitive_paths` and
   `required_checks`, plus `review_bots`, habit's list, when the version's manifest lists
   `review_bots`. Render refuses without it and writes nothing; no session invents the
   list. Upgrade keeps the confirmed values habit didn't change. Render removes each retired
   file an earlier version generated and lists it under `removed`; a file there the
   generator didn't write stays. When `mode`
   listed `drift.markers`, first run `<entry> mend-markers --worktree <worktree>`: it gives each
   mixed file one well-formed marker block at the record's version, restoring the markers or
   rebuilding the governance part as `repair` says, and keeps the file's repository-owned
   content. Quote each `dropped` line in a comment on the issue. A refusal ends the run like
   any exit 2.
   Remove a target first only where a version path holds another file, never a mixed file
   with governance markers: render replaces fixed files, and writes a removed mixed file whole.
4. Write the repository-owned content: `AGENTS.md`'s "This repository" section, with the
   authoritative runbook references and any inline carried rules and repository-specific
   review expectation; the Claude Code notes in
   `.claude/CLAUDE.md`; `docs/agents/build.md`, with the commands it ran, each marked as working
   or failing with the cause, the CI and the Actions secrets. On Upgrade, change this content only where habit confirmed a conflict.
5. Make the removals habit's answer leaves standing. Move the repository's own skills to
   `.agents/skills/`, with a `.claude/skills/` link, except skills under `.agent/skills/`,
   which stay where they are.
6. From here follow `docs/agents/builder.md`, Steps, from step 5: Initialize uses the rendered
   policy; Upgrade and Repair use the default branch's adopted policy. Use the issue as the
   ticket and declare the run's tier as above. Exact comparison, `<entry> compare --worktree <worktree>`,
   is part of its Verification and passes with `differences` empty before the PR opens.
   An Upgrade that changes the owner script, the target state or the required checks says in
   its Merge summary's "how to revert" (at high, the high-risk report) that habit reruns the
   owner script after a revert.
   At Initialize, the PR's Revert field and the high-risk report's revert note name each
   ruleset and setting the owner script will change, and whether it existed before. They say
   how habit returns each one in the browser after a revert without the owner script:
   disabling the Gate ruleset first, since it would otherwise require a gate the revert removes.

## 6. After merge

A run with no issue and no PR starts at step 2 and reports only to habit.

1. Wait on the PR as the role file says. Complete its product smoke on the exact merged
   commit: the actual default-branch product run, or the ticket's predetermined local smoke.
   Failure or unavailability leaves delivery incomplete and is escalated to habit.
   At every adopted policy version, reread each required review's result and the Merge
   summary from GitHub for the PR's exact head at merge before reporting; report only what
   that reading shows. Apply the adopted policy's Reviewer reread rule:

   - **Adopted policy below version 4:**
     Before any after-merge report, reread from GitHub, for the PR's exact head at merge:
     each required review's result, at medium and high the Comment review and the `Reviewer`
     status, and the Merge summary. The report states only what that reading shows.
   - **Adopted policy version 4:** reread the Comment review and `Reviewer` status only when
     a Reviewer ran.
2. Run `<entry> handover --mode-facts <saved mode report>`, adding
   `--required-checks-changed` when habit's answer changed them. When `owner_command` is true,
   give habit `<entry> owner-command --repository <owner/name>`'s command, with each of the
   report's `lines` verbatim beside it and each unverified item named. Hand it once per run.
   When it is false, the run ends here with the Chinese report.
3. After habit's run, fetch `origin` and allocate a temporary worktree as **Temporary paths**
   above at the default branch's head, then run `<entry> mode` once there. It reads the rulesets
   and readable settings as the agent account, and `<entry> preconditions` reads your own permission and, on a private repository, whether
   the rules are in effect: its `private` item and `rules_in_effect`. Report on the issue in
   English, where there is one, and to habit in Chinese, with whatever stays unread beside
   habit's owner-script report. When the `private` item fails, the issue records
   `rules_in_effect.issue_line` and habit hears its `habit_lines` verbatim. Its `command`, when
   there is one, is a second hand-over of the owner-script command, since the first run left a
   Gate or Merge rule out of effect.
