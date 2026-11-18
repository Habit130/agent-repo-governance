# Releasing

Start with [Build and verification](../agents/build.md) for the ordered checks and
habit-only commands. This reference describes the current state.

A version is released once its `generator/govern-repository/store/<n>/change-note.md` is on
the default branch (#44 §4). From then on the release check freezes the whole version
directory. Develop subsequent fixes in the
[unpublished draft](testing.md#unpublished-model-development).

## Cut a version

Prepare both changes in the cutting PR.

1. Add the final `change-note.md` to draft version N. `govern.py change-note <path>` reads
   the note's two fields.
2. Copy the resulting version directory to N+1, preserving the tracked files and their Git
   modes. Leave the root `change-note.md` out of the copy and change the top-level
   `version` integer in the copied `manifest.json` to N+1. Preserve every other byte.

The release check compares a newly added draft with its predecessor in the PR head and
reports the first differing path. Its proof of equality stands in for reviewing the copy.

The cutting PR's end-to-end run (#44 §11) is an Initialize of the public sandbox, after CI
and the [core Commands](../agents/build.md#commands) pass on the head. Every result names the head, so a later push
reruns them, the live checks and this run, with a fresh reset. The version cut is the
highest released one in the store: `reset` reads this checkout's, and `end-to-end` the
store in the plugin it builds from the head's commit. Both print that version and its
review bots, from its manifest's `review_bots`, and refuse a version whose manifest names
none.

1. **The reset.** `live.py reset --sandbox public` opens a sandbox PR whose commit holds exactly
   the materialized seed, `tests/fixtures/repositories/sandbox/repo/`, checked against the
   seed's `git write-tree`. It prints habit's two steps, in this order: the pinned merge once the
   PR's checks pass, then disabling the Gate ruleset in the browser, Merge and History staying
   active. The Gate ruleset has no bypass, so the sandbox's still-governed default branch judges
   the reset PR; its `Risk: high` line clears every floor the removed paths carry. Gate is
   disabled afterwards because the Initialize PR can't report `governance-gate` until its gate
   workflow is on the default branch. The reset reads the public sandbox only.
2. **The launch.** `live.py end-to-end --pr <n> --sandbox public` refuses, leaving nothing
   behind, unless this checkout is clean at the PR's head, the sandbox's default branch holds
   the seed's tree, Gate is disabled with Merge and History active, and no directory above its
   new one under the system temporary directory holds an `AGENTS.md`, `CLAUDE.md` or
   `CLAUDE.local.md`, which a session there would load. It clones the sandbox afresh. Beside the
   clone it builds the session-only plugin `cut` from the head's committed generator
   (`git archive`), so an ignored file in this checkout stays out. The seed holds no record, so
   the run is an Initialize at the version cut. It writes `end-to-end.json`: the before state,
   with the rulesets' enforcement, the version and its review bots, and the plugin's identity
   hash, which the run's issue must name. Then it prints habit's line. It runs from any harness
   or a plain terminal.
3. **habit's run.** habit starts Claude Code with that line in a terminal of their own, never
   with `!`. The line sets no `GOVERN_SCENARIO_` setting, so the run reads real GitHub as the
   agent account on the real machine. habit types `/cut:govern-repository`: the bare name
   resolves the installed copy. habit answers the confirmation, which lists the three rulesets
   for the owner script to replace and, from version 3, the review bots to enable in preference
   order. Then habit follows that run's Builder through the high path. Version 3 takes two bot
   slots. From version 4, request the first confirmed bot for one slot and try the next enabled
   bot only when the current one is unavailable. Use the Builder's command for Codex and the
   browser at Lite effort for Copilot when requested. Start the Reviewer with exactly the start
   instruction the Builder gives (#149). At version 3 its model vendor differs from the
   Builder's. From version 4 it differs from every Builder session that pushed to the PR.
   Read the high-risk report, run the pinned merge, say merged in the Builder's terminal and
   run the owner-script command to restore Gate.
4. **The outcomes.** The cutting PR's Builder posts each step's outcome on the cutting PR,
   naming the head. The issue's `generator_identity` equals `end-to-end.json`'s identity; the
   evidence includes habit's confirmation, the record at the version cut with the confirmed
   bot order, and the exact comparison. On the Initialize PR's head, verify self-verification,
   the completed bot reviews filling the version's slots, the Reviewer's Comment review and
   successful `Reviewer` status, and the Merge summary and high-risk report. For a v4
   Initialize, record which bot filled the one slot, any fallback, and which Builder and Reviewer
   session marks establish the vendor check. Record habit's squash merge and Merge watch's push
   run on it. From version 3 the run must report that it read the bots from the record the merge
   adds, say `No miss in this push event.` and have no `UNREADABLE` line. Record the run's
   after-merge report and the rulesets after the owner-script run. The version's live checks
   then run on the same cutting head through `prepare` and `probe`.

The cutting PR follows this repository's adopted version. While it is at v3, that means two
bot slots and a different-vendor Reviewer, including when the sandbox Initialize is at v4.
After the merge habit runs the install (README.md), which brings the released version to the
machine. Each repository adopts it by its own Upgrade. The cut's Merge summary names the
version, its urgency, the install and the remaining verification gaps (#44 §8, Trigger).

## Scenarios

No PR runs a model scenario or a replacement for one, releases included. In
[#138](https://github.com/Habit130/agent-repo-governance/issues/138), habit approved this
standing arrangement, verbatim:

> 同意， 同意推荐。

At a release, the cutting PR's end-to-end Initialize of the public sandbox remains
required, unchanged, as Initialize's behavioral check (the release procedure above). This repository's Upgrade to the newly released version is Upgrade's
behavioral check; a failure there is a miss, repaired in a later version. Repair and
OpenCode have no behavioral check before release. This gap is accepted; a failure in use
is a miss.

`AGENTS.md`, Verification by change, keeps the evidence and Merge summary line: model
scenarios were not run because of their quota cost; final-head model behavior is
unverified. Offline runner tests remain required and use no model.

The runner description below is retained as reference, not an instruction to run it.

`python3 tests/scenarios/runner.py <scenario> --harness claude|opencode [--runs N] [--out DIR]`
runs a scenario in a logged-in harness on habit's Mac, one run at a time. Its docstring gives
the fixture shape. The scenarios are `initialize-planted`, `upgrade` and `repair-files` under
`tests/scenarios/fixtures/`: each Claude Code scenario runs three times, and the OpenCode
smoke scenario is one run of `initialize-planted`. These retired procedures are reference only; the standing prohibition above applies. Each OpenCode submission passes exactly
`--model xai/grok-4.7`, and `opencode models --standalone` must list it first. Each Claude
Code submission passes `--model claude-sonnet-5-5 --effort medium`, habit's choice, and a run
fails unless every main-thread message ran on it and no message ran on Opus. A run's
permissions are its own: `--tools` and `--allowedTools` in Claude Code, `permission` in the
run's `OPENCODE_CONFIG_CONTENT` in OpenCode, never `--auto`. A failed resume records #40's
fallback and stops. `tests/scenarios/headless_probe.py` holds the resume and interface-entry
probes, and the runner reuses its clean environment. CI runs no model.

For version 2, the runner applies the additive scenario data in
`tests/fixtures/generator/scenarios-v2.json` to the unchanged original fixtures. It uses
the actual candidate store and an isolated installed home containing this repository's
real skill copies. Initialize starts without governance, Upgrade starts at version 1,
and Repair damages version 2's real review policy. The recorded answer confirms product
smoke and policy preservation; the judge checks the rendered version and the unchanged
confirmed-record format. No additional signing configuration is used.
