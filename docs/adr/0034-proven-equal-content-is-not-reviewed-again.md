# Content mechanically proven equal to reviewed content is not reviewed again

A change whose content a check proves identical to content that already passed review takes no second review of that content. [ADR 0008](0008-pure-revert-takes-the-low-path.md)'s pure revert was the first case; version 4 adds two:

- **A pure Upgrade is medium.** An Upgrade is pure when exact comparison reports no differences and the governance record's confirmed part is unchanged from the default branch. Its fixed content is what the release reviewed, so the tier no longer treats it as generator output. Initialize, Repair, and an Upgrade that changes a confirmed value, the required checks or the owner script's target state stay high.
- **The release PR creates the next draft.** The PR releasing version N also adds draft N+1, and the release check proves the new directory byte-identical to version N, the version number aside. Creating a draft stops being a PR of its own.

In the planning round, 2 of the 15 high PRs since 2026-11-10 only created a draft as a byte-identical copy, and 1 was this repository's Upgrade: each took a high review of content a machine had already shown to be equal. The proof is narrower than review: it shows equality, never that the reviewed content was right, so it applies only where equality is the whole question.

The pure Upgrade is in version 4's draft, an unpublished version; until a repository adopts version 4, version 3 tiers its Upgrade high. The release rule is [ticket #186](https://github.com/Habit130/agent-repo-governance/issues/186), not yet delivered; until it merges, a new draft is still created in its own PR.

Decided in [the version 4 planning round](https://github.com/Habit130/agent-repo-governance/issues/182), round 2, questions 3 and 4.
