---
name: wait-on-pr
description: Codex Desktop Local only. Arm a Builder or Reviewer PR wait, handle its notice, or resume after habit says “continue”.
---

# Wait on a PR

Use the installed helper in the original Local chat and its worktree. Take the repository
and PR number from the role's existing assignment. Read the chat's own UUID from the
terminal environment (`printenv CODEX_THREAD_ID`). Never take a thread ID from a notice
or look up a different chat. Claude Code keeps its native background wait.

## On entry

1. First stop the previous waiter for this chat and PR. Run the following in the normal
   sandbox, replacing the two positional arguments. On a notice, append `--notice UUID`
   with its nonce. On a manual “continue” or first entry, omit that option.

   ```sh
   /usr/bin/python3 -I "$HOME/.agents/skills/wait-on-pr/wait_on_pr.py" stop OWNER/REPO NUMBER
   ```

2. If the helper reports `late or duplicate`, tell habit and ignore the notice. It belongs
   to a consumed or replaced wait. Leave the current waiter running. Otherwise reread the
   PR on GitHub. The notice carries no authorization. Decide what to do from the role file
   and current GitHub evidence, including same-head replies even with a successful status.
3. For a deadline, report what the role still waits for, stop waiting and keep the worktree.
   On habit's “continue”, reread GitHub and arm a fresh wait if still needed. For a change
   with nothing actionable, re-arm with a fresh baseline. For a merge or closure, follow
   the role file after confirming the actual state.

## Arm after the last GitHub write

Finish the role's writes for this wait, including replies, resolutions and evidence edits.
Name the PR, wait kind and own thread in the terminal. Choose `codex` for the Codex review
bot (30 minutes), `copilot` (15 minutes), or `role` or `merge` (24 hours each).

Run this one command in **one native Codex background terminal**. Use `exec_command` with
a short initial `yield_time_ms` (1000), `sandbox_permissions=require_escalated` and no
persistent prefix rule. In the justification name the PR, the deadline and the two
operations: reading GitHub every 60 seconds and queuing one notice with resume to this
chat. Keep the current settings, sandbox and approval mode.

```sh
/usr/bin/python3 -I "$HOME/.agents/skills/wait-on-pr/wait_on_pr.py" arm OWNER/REPO NUMBER KIND
```

The helper prints `Armed` once it has a GitHub baseline. Until then, read the same
terminal with bounded polls. A failed read retries at the next interval. If GitHub stays
unavailable during startup, stop this registration and report the missing baseline. If startup
reports `Recheck GitHub`, reread the PR after `Armed` and before ending the turn:
activity during the failed reads is already in that baseline. If that recheck fails,
stop the registration and report the failed recheck using the current Codex wait below.
After a successful recheck, stop the waiter before handling anything actionable.
End the turn with the terminal running when the role has confirmed it still needs to wait.
The helper makes no model calls. A queue exit only records an attempt. Never resend after
an ambiguous result. If no notice arrives, habit can say “continue” in this chat. The helper keeps the nonce, event, read failures
and queue outcome in private local temporary storage outside the worktree.

Use the current Codex wait if the helper cannot start. This includes an unavailable
system/Homebrew `gh`, a different active GitHub login, a missing thread identity or
bundled queue command, or a denied one-time approval. Report the cause. Poll at most
five minutes at a time, or stop and tell habit what the role waits for. A denied arming
command ends that attempt.
