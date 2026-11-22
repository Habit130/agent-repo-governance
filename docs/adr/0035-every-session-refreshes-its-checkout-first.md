# Every session refreshes its checkout before reading its role

A session's first step, before reading its role file, is to fetch the remote and identify its default branch, then fast-forward the checkout when it is clean and on that branch. A session with no role does it too; a subagent uses its parent's tree and doesn't. A checkout that is dirty, on another branch, or can't fast-forward or reach the remote stays as it is: the session tells habit and reads the instruction files from the remote default branch when it can. When the refresh changed an instruction file, the session reads it again.

No rule refreshed the main checkout before, so sessions read whatever policy it happened to hold. The planning round found a four-day gap across the version 2 Upgrade, and a checkout still on version 1 recorded in [#127](https://github.com/Habit130/agent-repo-governance/issues/127): a session there follows rules the repository no longer has. Only a fast-forward is automatic, so the refresh never discards or merges anyone's work; anything else is left for habit.

This repository added the refresh to its own instructions on 2026-11-17, while version 4 was still a draft. The refresh becomes part of a governed repository's fixed content when it adopts version 4. On 2026-11-19 this repository's Upgrade replaced its temporary instruction with that fixed content. [Repository instruction](https://github.com/Habit130/agent-repo-governance/pull/192) · [Version 4 Upgrade](https://github.com/Habit130/agent-repo-governance/pull/203)

Decided in [the version 4 planning round](https://github.com/Habit130/agent-repo-governance/issues/182).
