# The governance gate checks the PR, not the reviews

A governed repository's one required governance check reads only what the PR shows:

- the `Risk:` line;
- the sensitive-path floors;
- the author;
- pure-revert confirmation.

Whether each tier's minimum reviews ran is checked by whoever writes the Merge summary, not by the gate, for two reasons:

- A required check can't vary by tier.
- Parsing third-party bot output would make every merge depend on those formats.

A review check joins the gate only once measurement shows misses. ADR 0021 sets out how.

Decided in [Which rules are enforced deterministically](https://github.com/Habit130/agent-repo-governance/issues/15).
