# The governance gate binds habit's merge and has no bypass

Every merge habit makes in a governed repository is an admin bypass of "Restrict updates". A bypass actor on the Gate ruleset would therefore void the gate. So the Gate ruleset, which requires the governance gate and CI, lists no bypass actor at all, and GitHub enforces it on habit's merge too.

When the gate or CI breaks and blocks its own fix, habit temporarily disables the Gate ruleset, merges the fix and re-enables the ruleset at once.

Decided in [Which rules are enforced deterministically](https://github.com/Habit130/agent-repo-governance/issues/15).
