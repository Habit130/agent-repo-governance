# Every merge stays with habit, and the merge is the approval

In a governed repository no tier merges without habit in version 1. There is no auto-merge and no workflow merge, and the required approval count is 0. habit's merge is the approval, and a "Restrict updates" ruleset that only habit bypasses keeps every merge with habit.

## Considered options

- **Low-tier auto-merge once checks pass.** Rejected: an honest agent's misclassification would put a medium change on the default branch without habit, and version 1 has no measurement to justify the risk yet. A later version may revisit it.
- **A separate habit approval.** Rejected: it would add a step to every PR, low tier included, and the pinned merge command already binds habit's merge to the reviewed head.

Decided in [How risk tiers gate a change](https://github.com/Habit130/agent-repo-governance/issues/12).
