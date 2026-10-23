# A pure revert takes the low path, sensitive paths included

A PR that exactly undoes one merged squash commit returns to a state that already passed review. In a governed repository such a PR takes the low path even on a sensitive path, so an emergency revert never waits for a Reviewer session.

The exemption holds only when the governance gate recomputes the revert on the PR's merge-base and finds it identical. Reverting a one-way door is an escalation instead.

Decided in [How work flows from idea to merged PR](https://github.com/Habit130/agent-repo-governance/issues/14) and [Which rules are enforced deterministically](https://github.com/Habit130/agent-repo-governance/issues/15).
