# Gate, Merge watch and owner live checks

Start with [Build and verification](../agents/build.md) for the ordered checks and
habit-only commands. This reference describes the current state.

## Merge watch

The rendered `.github/workflows/merge-watch.yml` and `.github/governance/merge_watch.py`
come from version 3's fixed templates under `generator/govern-repository/store/3/templates/`
(#41 §9). The script's docstring gives what it
records, from which facts, and how an unreadable fact yields a false miss record; it never
blocks anything and is never a required check.

**Version 3** judges reviews by responsibility, not provider, where versions 1 and 2
read Bugbot and the Codex review bot by name. Version 3's docstring is the full statement;
in short:

- The tier requires `self-verification` and `merge-summary` at every tier, `bot-1` and
  `reviewer` from medium, and `bot-2` at high. No bot is looked for at low.
- A bot slot is filled by a completed review on the head from a bot enabled in the record's
  confirmed `review_bots` at the merge's base: the pushed commit's parent, read through the
  contents API at that commit, not the merged tree. The one exception (#158) is a base with
  no record at all, as at an Initialize, where the record at the squash commit names the bots
  and the run prints a `NOTE` line. "No record" is GitHub's own answer, HTTP 404 with the
  message `Not Found`, raised as `NotFound` and never listed as unreadable; any other
  failure, a missing ref's 404 among them, stays a read that failed. `PROVIDERS` holds one reader per bot,
  `codex` and `copilot`; a disabled bot is never read. One provider fills one slot.
- The Merge summary's `Required reviews:` line is `review.md`'s version 3 grammar, read by
  `parse_reviews`: a line leaving out a required kind, or a bot slot's provider, doesn't
  read, so `merge-summary` is recorded (#89 F1). `reduced` and `substituted` are gone.
- A review waived by the repository owner's own PR comment, `Waiver: <item> at <40-hex head>
  — <reason>` as its first line, counts as present; any other author, another head or an
  item outside the review kinds counts for nothing.
- A merge whose base record is below version 3, such as an Upgrade's own PR, is judged only
  for what every version requires: the `Reviewer` status from medium and a Merge summary for
  the tier and head with a `Required reviews:` line of any kinds. Its review bots follow
  rules version 3 doesn't hold, so they aren't judged, and the run prints a `NOTE` line.
  habit accepted this transition exception on
  [PR #157](https://github.com/Habit130/agent-repo-governance/pull/157#issuecomment-6812806697),
  verbatim: "同意推荐并继续推进吧"; that PR's Reviewer checks the old bots before the merge. A
  base record that can't be read or doesn't parse enables no bot, a false miss.
- At low no bot's endpoint is read, so an unreadable one can't fail the run.
- `decide` takes an optional `notes` list for those lines, and `read` answers a
  `contents` path with the file's text.

**Version 4** keeps the same event and record boundary, with its script under
`generator/govern-repository/store/4/templates/`. For a base at version 4 or later, every
tier requires `self-verification` and `merge-summary`; medium and high require `bot-1`,
and only high requires `reviewer`. At medium, Merge watch accepts substitution after it
successfully reads and parses the bot policy. A readable summary with `reviewer=clear`
and the agent account's successful `Reviewer` status on the head fills an unfilled bot slot
only when `bot-1` declares `no-provider(none)` or `unavailable(<last enabled bot>)`, the last
enabled bot in the base record's ordered list. An earlier unavailable provider or any other
unfilled slot state remains missing. `no-provider(none)` declares exhaustion of an initially
empty list or of all enabled bots; it does not prove actual requests occurred. Sessions still
verify the requests and unavailability evidence. A valid owner/exact-head bot-slot waiver
remains a separate exception; high has no Reviewer substitution.
The bot order remains the confirmed list; when a bot is unavailable, the next enabled bot
fills the slot at medium and high. The
summary grammar and waiver kinds contain the one bot slot only. A merge onto a base below
version 4 takes the transition exception: a `Reviewer` status from medium and a summary
for the tier and head with any `Required reviews:` kinds. On a version 3 base only, a valid
owner/exact-head `reviewer` waiver also satisfies the Reviewer requirement; the Builder
checks the bots before merge when the Reviewer is waived. Otherwise the Reviewer checks
them. Versions 1 and 2 still require the Reviewer status. Bots are not judged by Merge
watch, and a `NOTE` line records the transition. Version 4's recorded cases live under
`tests/fixtures/merge-watch/v4/`; earlier cases and expectations remain unchanged.

- **Seam 2** is `merge_watch.decide(event_name, event, agent_account, read)`, where `read`
  answers a REST path with GitHub's list, every page joined, or raises `ReadError`
  (version 3: `NotFound`, its subclass, for a file GitHub says isn't there). Its
  output is the records to open. A new case joins `tests/fixtures/merge-watch/cases/` and is
  never renamed; the suite's docstring gives a case's shape. Version 3 cases live separately
  under `tests/fixtures/merge-watch/v3/`, preserving version 1's expected wording; the
  review cases there are named `review-*`, and the suite loads version 3's script beside
  version 3's gate. A version 3 case's optional `not_found` lists the paths GitHub answers
  with its own `Not Found`; the `review-base-without-record-*` cases (#158) use it.
- **GitHub's facts it relies on**, from github/docs at `6cbe641`, read 2026-10-30:
  - `on.workflow_run.workflows` takes the patterns of the workflow syntax's Filter pattern
    cheat sheet ("You can use special characters in path, branch, tag, and workflow name
    filters"): `**` matches any characters, `/` included, and `!` at a pattern's start
    negates the positive patterns before it. `["**", "!merge-watch"]` matches every
    workflow but Merge watch, whose `name:` is `merge-watch`; a workflow without one is
    named by its file path.
  - `workflow_run` fires only for a workflow file on the default branch, its `branches`
    filter names the branch the triggering run ran on, and chaining stops at three levels.
  - The Codex review bot keeps one summary comment per PR by
    `chatgpt-codex-connector[bot]`, edited in place, holding
    `<!-- codex-review-state:v1 {...} -->` (PRs #66 to #85).
  - History, read by versions 1 and 2 only, which version 3 retired: Bugbot's check run came
    from the app `cursor` (PR #85's head `bfec87b`), and Cursor concluded a finished review
    `success`, `neutral` (findings, a newer commit's cancellation, or an internal error) or
    `failure` (findings, when set to fail on them), and never `skipped` (Cursor's Bugbot
    docs, CI check statuses, read 2026-10-30).
  - The list endpoint `commits/{ref}/statuses` gives each status's `creator`, newest first;
    the combined `commits/{ref}/status` doesn't, so the script reads the list (GitHub's REST
    reference for commit statuses, read 2026-10-30).
  - Copilot code review, observed on the two sandboxes in #131 (2026-11-10 and 11-11), not
    documented: a review by `copilot-pull-request-reviewer[bot]` with
    `is_copilot_code_review` true and `commit_id` the head, and a `copilot-pull-request-reviewer`
    check run from the `github-actions` app, completed `success`, on the head. After a push
    the old review keeps its old `commit_id` and the new head has no check run until a new
    request. The workflow token with `pull-requests`, `checks` and `actions` read reads all
    of it. A request from the agent account is silently dropped, and Copilot's own review
    event starts a workflow only after approval, so Merge watch reads Copilot on its push
    run. A change in these fields yields false miss records, never a blocked merge.
- **The live check** is below, under Merge watch's live check.

## The owner script and live checks

The rendered `.github/governance/owner.sh` comes from version 3's fixed template
`generator/govern-repository/store/3/templates/dot-github/governance/owner.sh` (#44 §7). Its
docstring gives the preconditions, the order of writes and the exit codes (0 in place, 1 an
item failed or missing, 2 stopped before any write).

- **Version 4's event-policy line.** On a public repository, every `缺失` line for
  `pull_request_target 事件策略`, whether GitHub can't read the policies, can't write one or
  answers with something else, says before the manual steps that from 2026-12-02 GitHub
  blocks `pull_request_target` there without the policy, so `governance-gate` reports
  nothing and no PR can merge until it is set. The item's name, its statuses, the exit codes,
  the order of writes and the private skip line are version 3's, so the live probes read the
  report as before.

- **Its shape.** Line 1 is `#!/bin/bash`, so step 5's `/bin/bash -n` finds it; line 2 is the
  notice; its mode is `100755` in the manifest and the index. The bash entry feeds the Python
  program to `/usr/bin/python3 -I` through a quoted heredoc, so step 5 never parses that
  program: the `owner` suite parses it as 3.9. `@@version@@` in the notice is its only token.
- **The owner-script command**: see [habit-only commands](../agents/build.md#commands-only-habit-runs).
- **GitHub's facts it relies on**, read 2026-10-28: the GitHub Actions app's id 15368 from
  `GET /apps/github-actions`; the admin role's bypass actor id 5 from GitHub's own exported
  rulesets in `github/docs` at `57f571f`, since no prose states it; the repository-level
  Actions policy endpoints `/repos/{owner}/{repo}/actions/policies` and their allowlist-only
  `restrict_action_events` rule, from the same commit. GitHub returns rulesets and policies
  with fields the script never sent and leaves `update` bare, so it compares only what the
  target declares. Ruleset ref patterns are Ruby's `File.fnmatch` with `FNM_PATHNAME`
  (`github/docs` at `57f571f`, "Using `fnmatch` syntax", read 2026-10-29). The script
  decides which rulesets apply to the default branch with a step-by-step port of Ruby's
  `fnmatch`, `fnmatch_helper` and `bracket`. `tests/fixtures/owner/ref-patterns.json` records
  Ruby's own answers, which Seam D checks row by row. GitHub refuses a backslash and doesn't
  support complementing a set with `^` (same source), so a ruleset whose pattern has either is
  never removed: the report fails it and names the reason. The live probe `owner-state` asks
  `/usr/bin/ruby` itself instead of sharing the port.
- **Seam D** (`tests/suites/test_owner.py`) runs each case as `owner_support.py`'s docstring
  defines it. `tests/target_state.py` is #41 §7 written independently of the script; Seam D's
  recorded bodies and the live probes both compare against it. A new case joins
  `tests/fixtures/owner/cases/` and is never renamed.
- **Live checks** run through `tests/live/live.py` as the agent account, in the two
  sandboxes only. Its docstring lists the subcommands; `tests/live/probes/__init__.py` gives
  the one probe shape. Probes normally add only a module; the cancelled-run probe also
  stages its workflow in the render PR and selects version 3 during prepare. One check,
  for a sandbox:
  1. habit runs `live.py sandbox-command`'s line once, then connects the review bots the
     check's version uses for both sandboxes: the Codex review bot (its connector's
     repository list) and Copilot code review for version 3, plus, for version 2's probes
     only, the Cursor GitHub App's repository access. `live.py seed --sandbox <s>` then accepts the invitation and
     seeds the empty default branch from `tests/fixtures/repositories/sandbox/`, whose
     `fixture.json` holds the sandboxes' fixed confirmed values.
   2. `live.py prepare --pr <n> --sandbox <s> --probe <name>...`, at this checkout's pushed
     PR head, opens the sandbox PR, with a record under `live-checks/` so one exists even
     when the render is unchanged, and prints habit's commands: the pinned merge command,
     the owner-script command, then each probe's commands, each saving its output in the
     check directory. It renders the probes' own version: 2, 3 for version 3's probes, or 4 for version 4's;
     `--version <n>` renders a later one instead, the unpublished draft included, with the
     per-call opt-in, and refuses one below the probes' own. `prepared.json` keeps the
     version, so the probes judge with its confirmed values. Version 4 (#169) runs the
     gate's four probes with `owner-state` and `owner-rerun` as `--version 4`.
  3. After habit's steps, `live.py probe --state <dir>/prepared.json --probe <name>... --post`
     posts the result comment, naming the commit. The owner probes need one run without
     `--post` between habit's two owner-script runs (`probes/owner.py`).

## Owner permission verification

After adoption smoke, habit runs the owner command in the core build document. Capture the non-sensitive
`default_workflow_permissions` and `can_approve_pull_request_reviews` fields before and
after execution as maintainer evidence, alongside the full owner report. The agent's
readable rulesets/settings do not prove the workflow-permission postcondition. A report
that approval was already disabled also needs those fields to establish the preserved
default. The later generator `preconditions` run remains habit-run: it invokes the machine
check against habit's home (`AGENTS.md`, Verification by change).

Version 2 accepts only a valid `read` or `write` default and Boolean approval state. It
preserves that default when disabling approval, writes once, then reads back at most
three times (two-second intervals, five-second read timeouts). A changed default or invalid
state stops verification; an unconfirmed result is a failure, not a successful application.
Already-disabled approval needs no write. These are compatibility and observation repairs,
not evidence that an optional-field API failure or propagation delay was reproduced.

Reverting files does not restore GitHub settings: habit must rerun the corresponding
version's owner command after a revert.
The current gate still uses shared GitHub Actions App 15368, not a unique workflow issuer;
same-SHA stale-success limitations remain.

## Owner recovery checks

Run `owner-report`, `owner-state`, `owner-rerun` and `owner-recovery` in both sandboxes:

| Probe | Setup and evidence |
| --- | --- |
| `owner-recovery` | After initial owner application, habit captures the disabled-approval baseline, enables approval in sandbox settings without changing the default workflow permission, captures that state, runs the printed owner command, reads back both fields and repeats the owner command. The probe requires preserved `read`/`write`, disabled approval after repair and a zero-write repeat. Agents run none of these owner commands. |

Run setup probes without `--post` first, then the printed habit-only commands, then post
only when every assertion passes. A missing input is an incomplete check, never a skip.

Offline probe tests exercise the evidence judge, not GitHub's implementation. Record the
model head, sandbox PR, baseline, commands and full assertions with results. The live check
proves the retained owner repair, not reproduction of an optional-field API failure.

## The gate's live check

`tests/live/probes/gate.py` holds the gate's probes (#41 §8): `gate-trigger`, `gate-reruns`,
`gate-source` and `gate-rulesets`, run together, with the input `owner_report` that every check
takes. Its docstring gives the setup, the probe PRs and what each assertion reads.

- **Three steps after habit's merge and owner-script run:** `live.py probe` without `--post`
  sets the check up as the agent account; habit runs `gate-rulesets`' one command; then
  `live.py probe --post` judges. The setup writes the targets of habit's command to
  `gate_targets.txt` in the check directory.
- **The entry is `tests/live/gate_attempts.py`.** `gate-rulesets` prints a thin shell
  invocation of `/usr/bin/python3` with `--repository`, `--branch` and `--targets` pointing
  at the existing targets file. The entry owns preparation, dispatch, stop classification
  and the final ref read; subprocess argument vectors are separate from shell quoting.
  Absolute entry paths and quoted values let the command run from an unrelated directory.
  Importing, setting up or judging a probe never invokes the entry.
- **The attempts stay with habit.** The agent's direct push to the default branch, its
  force-push and its merges are habit's command, run as the agent account with `gh`. Claude
  Code's auto mode refused them to the agent on 2026-10-30. The probes never push to the
   default branch, force-push or merge.
- **Stop on the first success.** If an attempted push or merge exits 0, the command runs no
  later attempt and exits 3. Its output keeps that attempt's `exit=0`, prints
  `stop-after: <attempt>` with Chinese advice, and retains `== account` and `== after`;
  the latter reads refs after the stop. habit then stops as for a product question, rather
  than rerunning the command. `gate-rulesets` fails the success and each skipped attempt
  explicitly, and still reads both refs and every probe PR from GitHub. A clone, checkout
  or amend failure prints `never-reached:`: the push never reached GitHub, so it is neither
  a success nor a rejection; later attempts still run. When every attempt is rejected,
  the command keeps its section headers and `exit=` lines, prints no stop and exits 0.
- **Offline coverage** in `live-runner` executes the same generated invocation under bash
  with test-local `git` and `gh`, verifies every call's executable and complete arguments,
  and judges the captured protocol. It covers all six success positions, preparation
  failures, missing targets (exit 2 before tool calls), healthy rejections and quoted paths.
  It also appends the runner's unchanged `2>&1 | tee` capture decoration: the output's
  stop marker, not the outer pipeline status, tells the judge which attempts were skipped.
  These stand-in runs make no claim about live protection behavior; real attempts remain
  habit-only.
- **Version 3's review probes (#148)**, public sandbox only: prepare with
  `--probe merge-watch-v3-clean --probe merge-watch-v3-waived --probe merge-watch-v3-miss`.
  Any of them renders version 3 with the per-call opt-in and the confirmed `review_bots`
  `codex`, `copilot` (`live.py`, `V3_REVIEW_BOTS`); the seed's fixture stays as it is. Gate
  probes refuse to share the check, since these merge. Each probe opens its own PR at high
  and posts the agent's `Reviewer` status:
  - `merge-watch-v3-clean`: habit requests the Codex review bot and Copilot; the summary
    names `bot-1=clear(codex)` and `bot-2=clear(copilot)`. Merge watch records no miss.
  - `merge-watch-v3-waived`: habit requests Copilot only and posts the waiver of `bot-1` on
    the head from the printed command. Merge watch records no miss.
  - `merge-watch-v3-miss`: habit requests the Codex review bot only; the probe posts an
    agent-account waiver of `bot-2` as planted data, and the summary leaves the Reviewer
    out. Merge watch records one `missing-review` record lacking `bot-2, merge-summary`.

  The steps are the clean probe's: a first `live.py probe` opens the PRs and writes the
  targets; habit runs the printed steps (two Codex review bot requests, two Copilot
  requests in the browser at Lite, about 6 AI credits each by #63's measurement, and one
  waiver comment); a second run waits for each bot within its wait (30 minutes for the
  Codex review bot, 15 for Copilot), posts each summary and reports `READY`; habit runs
  each printed pinned merge; a last run judges Merge watch's own push runs and posts with
  `--post`. A bot that doesn't answer stops its probe as an environment blocker, never a
  pass. A run whose log holds a `NOTE` line fails the clean and waived probes.
- **Version 4's review probes (#183, #187)**, public sandbox only: from the committed,
  pushed delivery head, run
  `python3 tests/live/live.py prepare --pr <n> --sandbox public --probe merge-watch-v4-high --probe merge-watch-v4-medium --probe merge-watch-v4-miss --directory <dir>`.
  These render version 4 from the delivery checkout using the runner's fixed test
  configuration. Each probe uses Codex in the single `bot-1` slot. Run the gate probes
  in a separate check.

  habit merges the render PR using its printed pinned command and runs its printed owner
  command. Then run
  `python3 tests/live/live.py probe --state <dir>/prepared.json --probe merge-watch-v4-high --probe merge-watch-v4-medium --probe merge-watch-v4-miss`
  once to open the three probe PRs and write habit's command targets. The initial results
  say that habit's steps and merges are pending. All probe writes use the agent account:
  - `merge-watch-v4-high`: a successful `Reviewer` status and a summary listing
    `self-verification`, `bot-1=clear(codex)` and `reviewer=clear`; no miss.
  - `merge-watch-v4-medium`: no `Reviewer` status and a Builder summary listing only
    `self-verification` and `bot-1=clear(codex)`, stating that no independent session looked
    at the change; no miss.
  - `merge-watch-v4-miss`: high, no `Reviewer` status, and a summary omitting `reviewer`;
    exactly one `missing-review` record lacking `reviewer, merge-summary`.

  If automatic Codex review completed on a probe head, it counts without a request
  comment. Otherwise habit makes that probe's printed Codex request; agents never send a
  bot trigger. Rerun the same probe command to collect reviews, post the summaries and
  report `READY`. A requested bot has its 30-minute wait; no answer is an environment
  blocker. habit alone runs each printed pinned merge after `READY`. After all three
  merges, run the same probe command with `--post`: every assertion must pass, and its
  PR comment names the delivery commit and sandbox heads. Clean probes reject transition
  `NOTE` lines; the miss probe checks the exact run result and record's six field lines.
  These statuses and summaries are sandbox probe data, not a real Reviewer session.
- **`merge-watch-miss` under version 3** reads `bot-2` as the missing second bot where
  earlier versions write `codex`; the cancelled-run and planted-miss probes can therefore
  share version 3's render.
- **The private sandbox (#53)** takes the same probes, unchanged: `prepare --sandbox private`
  and the same `--probe` names. They read the repository, default branch and confirmed checks
  from the context, and `gate-trigger` expects the event policy skipped (`已跳过`) there.
- **GitHub's facts they rely on**, read on 2026-10-30 from `Habit130/governance-sandbox`,
  and from github/docs at `6cbe641`:
  - A `pull_request_target` run's `head_sha` is the PR head. Its job checks out the default
    branch, whose commit the gate's log line names. The job's own check run and the
    script's posted one are both `governance-gate` from GitHub Actions (app 15368), in
    different check suites.
  - A body edit (`edited`) runs the gate again on the same head. The first run's failing
    check run stays on the head, but a merge rejection then names no required check.
  - Skip instructions in a commit message don't stop `pull_request_target`
    (`skip-workflow-runs.md`). With no app pinned, a same-name check and status must both
    pass (`troubleshooting-required-status-checks.md`).
  - GraphQL's `isRequired` reads `true` for the agent's same-name status, so it is no
    evidence of what satisfies a pinned check. The agent's own merge state always reads
    `BLOCKED`, because the Merge ruleset restricts updates.
  - The rejections, quoted:
    - A direct push gets `GH013` with one `- ` line per rule: `Changes must be made
      through a pull request.`, `Required status check "governance-gate" was not set by
      the expected GitHub app.` and `Cannot update this protected ref.`
    - A force-push to another branch gets `Cannot force-push to this branch`.
    - A merge gets HTTP 405, `Repository rule violations found`, with
      `Required status check "governance-gate" is failing.` while the gate fails, and
      `Cannot update this protected ref.`

## Merge watch's live check

`tests/live/probes/merge_watch.py` holds version 2's Merge watch probes (#41 §9, seam 4),
kept for sandbox checks of version 2's render:
`merge-watch-clean` for a head with every review, and `merge-watch-miss` for a planted miss.
Its docstring gives each step and what each assertion reads. `merge_watch_v3.py` holds
version 3's (#148), described above under Version 3's review probes.

- **The planted miss is the render PR.** It is declared high and nothing reviews it, so its
  merge always leaves a `missing-review` record, and `merge-watch-miss` judges that record.
  Miss records in a sandbox count nowhere (#44 §12).
- **Two sandbox merges, in this order after `prepare --probe merge-watch-clean --probe
  merge-watch-miss`:**
  1. habit merges the render PR and runs the owner-script command.
  2. `live.py probe` without `--post` opens the probe PR, requests Bugbot, posts the agent's
     `Reviewer` status and writes `merge_watch_codex.txt`.
  3. habit runs the printed Codex review bot request.
  4. `live.py probe` waits for both bots, posts the Merge summary and reports `READY`. Give
     it 40 minutes in the background: two 15-minute waits for Bugbot and 10 for the Codex
     review bot. It
     writes `merge_watch_merge.txt` only on `READY`.
  5. habit runs the printed pinned merge, which refuses until that file exists.
  6. `live.py probe --post` judges. Each sandbox PR's head is fixed by then; a new head would
     reset all four facts.
- **Merge watch's run decides CRIT-1, not the agent's reading.** A failed read counts as
  absent, so a push run that says `No miss in this push event.`, with no `UNREADABLE` line,
  has read all four facts with its own token.
- **A bot that doesn't answer stops the check.** After one Bugbot request and one retry, or
  a Codex wait that runs out, the run fails naming what came back. That is an environment
  blocker and never a reduction. The Merge summary lists every kind as `clear`, so no kind
  counts without being read.
- **Reading a run's log.** GitHub redirects it to Azure Blob Storage. On 2026-10-31 `gh` 2.98
  timed out in the TLS handshake with that host from habit's machine, while `curl` reached
  it, and `GODEBUG=tlsmlkem=0` cleared it. When the probes report that a log couldn't be
  read with `TLS handshake timeout`, run `live.py probe` with that variable set.
- **Cancelled default-branch run (#135):** prepare the public sandbox with
  `--probe merge-watch-cancelled --probe merge-watch-miss`. This combination renders
  version 3 with the per-call opt-in; other probes retain version 2.
  Prepare refuses an existing open `red-default-branch` record. Resolve that record before
  preparing; the probe never closes an unrelated record.
  The render PR includes a unique workflow and marker. Only a default-branch push changing
  that marker triggers the workflow; its sole job sleeps for two minutes with a one-minute
  timeout. habit merges the render PR and runs the printed owner command, as usual.
  Run `live.py probe` after GitHub completes the timeout and Merge watch's `workflow_run`
  run; if still pending, retry. The probe reads the cancelled run, GitHub's timeout
  annotation, Merge watch's own successful run and log, and the exact six-field miss record
  from GitHub. A manual cancellation is insufficient evidence.
  Once every assertion passes, it closes only that verified sandbox record and reads back
  its closed state. The marker and workflow remain as evidence: later pushes leave the
  unique marker unchanged, so they do not trigger the timeout. Preserve both together;
  deleting the marker alone would trigger it again. Post the passing results with
  `live.py probe --post`; `merge-watch-miss` also verifies the render merge's push path.
  The offline `live-runner` cases check these judgments, including wrong or absent evidence,
  and do not claim live GitHub behavior. `merge-watch-clean` is separate from this
  cancellation check and needs both bots and about 40 minutes.
- **The private sandbox (#53)** takes the same probes, unchanged: `prepare --sandbox private`
  and the same `--probe` names. They read the repository and default branch from the
  context, and habit's commands name that repository.
- **GitHub's facts they rely on**, from github/docs at `85c3298`, read 2026-10-31:
  `github-token-scope-descriptions.md` lists `contents`, `pull-requests`, `issues`, `checks`,
  `statuses` and `actions` as the permissions behind what the script reads and writes, and
  sets every unlisted permission to `none`. A run's log comes from
  `actions/jobs/<id>/logs`, the gate's read, through `gh api --allow-escape-sequences`.
