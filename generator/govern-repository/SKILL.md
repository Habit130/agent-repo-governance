---
name: govern-repository
description: Initialize, upgrade or repair a repository's governance from the installed governance model. habit invokes it, with no arguments, from the repository's directory.
disable-model-invocation: true
metadata:
  opencode/autoinvoke: false
---

# Govern a repository

This run is a high Builder delivery. It takes no arguments and starts from the repository's
directory. `<entry>` below is `/usr/bin/python3 <this skill's directory>/scripts/govern.py`.
Each subcommand prints JSON; save each report in a temporary directory outside the checkout.

**The harness.** The run happens only in Claude Code or OpenCode. In the Codex harness,
deepseekharness or anything else, stop before any other step and tell habit in Chinese where
to run it, whatever a script says.

**Talking to habit.** Every message is plain Chinese, with governance terms and product names
in English and no code, diffs or paths. It names its sender and target.

**Before habit's answer** the checkout and GitHub stay as they are. The one write is
`<entry> accept-invitation`, for an invitation habit sent from the checklist.

## 1. Facts

1. Run `<entry> preconditions`. On a failed item, or a step only habit can take, give habit
   the one checklist. Items that block the run wait until habit says they are done. A step
   that can wait, such as the review bots, goes into the confirmation instead.
2. Run `<entry> mode`, saving its report. On mode `stop`, tell habit the reason and end.
3. Follow the report's `outcome`:
   - **no drift**: send one Chinese message saying so, and end. No issue, no PR.
   - **not proven, the inactive rulesets**: name each one under `drift.github.unplaced`, say
     it enforces nothing and needs no action, and end. Write nothing and hand no command.
   - **not proven, the unread items**, or **drift in GitHub state only**: go to section 6,
     step 2. No issue, no PR.
   - **anything else**: carry on. Inactive rulesets under `unplaced` are named in the
     confirmation, and unread items under `drift.github.unreadable` are named there as
     unverified. "No drift" is said only for the no-drift outcome.
4. Run `<entry> inspect`.

## 2. Judgment

Every entry below ends up in the confirmation and the issue.

- **Rules.** Sort every rule found in instructions, process documents, contributing guides
  and files at version paths into one class:
  - `covered`: the model already holds it, so it is dropped and listed;
  - `carried`: repository-specific and compatible, so it goes into "This repository";
  - `conflicting`: it conflicts with the model or loosens it, so it is dropped and listed
    separately. Keeping it would be a model change, never a per-repository exception;
  - `removed`: an earlier decision removes it: a root `CLAUDE.md` once carried, any
    `AGENTS.override.md`, `.codex/`, committed harness permission settings and agent
    definitions, issue templates of a replaced process, an older Bugbot rule file.

  Each rule's text is quoted with its file. Sort other files the model never writes, such as
  hooks, CODEOWNERS or a Bugbot config, the same way, and propose keeping or removing each.
- **Sensitive paths.** Propose paths by category: authentication, billing and payments,
  release and publish workflows and scripts, installers, deployment configuration,
  secret-handling code, data migrations. Each gets a medium or high floor.
- **Required checks.** Propose a job only when `inspect` reads it as `every_pr: true` and not
  uncertain, under its reported `name`. Name every other job and why it can't be required.
- **Commands.** Run the manifests' and documents' build and test commands in a temporary
  worktree of your own, so the checkout stays untouched. A manifest whose `extraction` is
  `unsupported` has its commands read from the file by you. Record which worked.
- **Actions secrets.** For each name under `ci.secrets`, propose its purpose and issuing
  service from the step that uses it. A name you can't place is asked about, never guessed.
- **Credentials.** A credential the inspection names is reported by type and location. Its
  removal is a separate ticket.

## 3. The confirmation

Send one plain message, never a question tool, then end the turn and wait for habit's answer.

- **Initialize, or a rebuilt record**, holds only: (1) sensitive paths as plain categories
  with paths as labels, plus any high floors; (2) the checks to make required, any that can't
  be and why, or that there is no CI and so no smoke check; (3) the carrying lists: rules
  dropped as covered, rules dropped as conflicting, files removed by earlier decisions,
  repository skills sharing a machine skill's name, and nested `AGENTS.md` files; (4) the
  rulesets and branch protection the owner script will replace; (5) open PRs, for
  information; (6) any precondition step still open for habit; (7) the Actions secrets with
  proposed purposes and issuing services; (8) the labels to create; (9) on a private
  repository, that GitHub detects and blocks no credential there and that Actions minutes are
  limited, for habit's acknowledgment. Files to keep or remove join item 3.
- **Upgrade** holds only: every change note after the record's version, combined, and what
  they mean here; confirmed values the new version newly needs; repository-owned content that
  conflicts with the new fixed rules; any ruleset or required-check change, applied after
  merge; and anything unverified.
- **Repair with drift** holds only the drift found, how it is restored, and anything unverified.

An item habit's answer leaves open gets one follow-up about that item only. Assume no answer.

## 4. The issue

After habit's answer, run `<entry> identity`, then open one issue as the agent account with
`docs/agents/issue-tracker.md`'s create command form, and assign it to yourself with
`gh issue edit <n> --add-assignee "@me"`. It holds, in this order:

- habit's invocation, the findings, the proposals and habit's answers, each verbatim;
- one fenced block with the info string `govern-facts`, holding JSON with exactly these keys:

  ```text
  rules: [{"text", "file", "class"}]        sensitive_paths: [{"pattern", "floor"}]
  required_checks: [name]                   actions_secrets: [{"name", "purpose", "service"}]
  labels_to_create: [name]                  nested_agents_md: [path]
  generator_identity: the identity subcommand's "identity"
  ```

- acceptance criteria and verification commands, exact comparison included.

## 5. Writing

1. Create only the labels missing from GitHub, from the version manifest's `labels`, with
   `gh label create <name> --color <color> --description <description>`.
2. Make your own worktree on a new branch from the latest `origin` default branch.
3. Render: `<entry> render --dest <worktree> --repository <owner/name> --default-branch
   <branch> --confirmed <file>`, the file holding JSON with `sensitive_paths` and
   `required_checks`. Upgrade keeps the confirmed values habit didn't change. Remove a target
   first where `mode` says to rebuild it or a version path holds another file: render replaces
   fixed files, and a mixed file with no well-formed markers is taken back to the version's.
4. Write the repository-owned content: `AGENTS.md`'s "This repository" section, with the
   carried rules and any repository-specific review expectation; the Claude Code notes in
   `.claude/CLAUDE.md`; `docs/agents/build.md`, with the commands that worked, the CI and the
   Actions secrets. On Upgrade, change this content only where habit confirmed a conflict.
5. Make the removals habit's answer leaves standing. Move the repository's own skills to
   `.agents/skills/`, with a `.claude/skills/` link.
6. From here follow the version's `docs/agents/builder.md`, Steps, from step 5, with the issue
   as the ticket and `Risk: high`. Exact comparison, `<entry> compare --worktree <worktree>`,
   is part of its Verification and passes with `differences` empty before the PR opens.
   An Upgrade that changes the owner script, the target state or the required checks says in
   its high-risk report's "how to revert" that habit reruns the owner script after a revert.

## 6. After merge

1. Wait on the PR as the role file says. Confirm the default-branch CI run is green, or note
   that the repository has no CI.
2. Run `<entry> handover --mode-facts <saved mode report>`, adding
   `--required-checks-changed` when habit's answer changed them. When `owner_command` is true,
   give habit `<entry> owner-command --repository <owner/name>`'s command, with each of the
   report's `lines` verbatim beside it and each unverified item named. Hand it once per run.
3. After habit's run, rerun `<entry> mode` once and read back as the agent account what it can.
   Report in English on the issue and in Chinese to habit, with whatever stays unread beside
   habit's owner-script report. The run then ends.
